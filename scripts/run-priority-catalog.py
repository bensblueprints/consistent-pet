"""Overlay approved priority references without changing a frozen runner/index.

Run with the same version, limits, repo and frozen runner as the paused worker.
The original catalog fingerprint and all native job checkpoints are preserved.
"""
import argparse
import fcntl
import importlib.util
import json
import sys
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--runner', type=Path, required=True)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--priority-index', type=Path, required=True)
    p.add_argument('--append-index', type=Path, action='append', default=[], help='Additional references after the existing catalog, preserving existing queue entries')
    p.add_argument('--version', required=True)
    p.add_argument('--hours', type=float, default=48)
    p.add_argument('--deadline', type=float, help='Explicit owner-authorized UTC epoch deadline for a resumed run')
    p.add_argument('--attempts-per-dog', type=int, default=6, choices=[6])
    a = p.parse_args()
    sys.path.insert(0, str(a.runner))
    spec = importlib.util.spec_from_file_location('priority_roster_base', a.runner / 'run-roster-catalog.py')
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    priority = json.loads(a.priority_index.read_text())
    appended = [row for path in a.append_index for row in json.loads(path.read_text())]
    ids = [r['id'] for r in priority]
    supplemental_ids = ids + [r['id'] for r in appended]
    if not ids or len(supplemental_ids) != len(set(supplemental_ids)):
        raise ValueError('Supplemental references must have unique IDs')
    for r in priority + appended:
        if base.digest(a.repo / r['reference_path']) != r['reference_sha256']:
            raise ValueError('Priority reference hash differs')
        if not (a.repo / r['workflow_folder'] / 'status.json').is_file():
            raise ValueError('Missing per-reference workflow folder')

    class PriorityCatalog(base.RosterCatalog):
        def __init__(self):
            super().__init__(a.repo, a.version, a.hours, a.attempts_per_dog)
            if a.deadline is not None:
                if a.deadline > time.time() + 48 * 3600 + 60:
                    raise ValueError('Resume deadline exceeds 48 hours')
                self.state['max_hours'] = (a.deadline - self.state['started_at']) / 3600
                self.state['authorized_resume_deadline'] = a.deadline
            overlap = set(supplemental_ids) & set(self.by_id)
            if overlap:
                raise ValueError('Priority IDs overlap original catalog')
            self.index = priority + self.index + appended
            self.by_id = {r['id']: r for r in self.index}
            for r in priority + appended:
                self.state['items'].setdefault(r['id'], dict(status='pending', round=0, generations=0, errors=0))
            self.state['priority_references'] = ids
            self.state['appended_references'] = [r['id'] for r in appended]
            self.save()

        def save(self):
            super().save()
            path = base.ROOT / 'catalog-public-status.json'
            public = json.loads(path.read_text())
            public['total'] = len(self.state['items'])
            public['priority_remaining'] = sum(self.state['items'].get(i, {}).get('status') not in ('accepted', 'blocked') for i in ids)
            base.atomic(path, public)

    with (base.ROOT / 'catalog-refinement.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        catalog = PriorityCatalog()
        # Resume the prior active portrait before selecting the new front batch.
        # A durable marker prevents this from repeatedly preempting priority work.
        marker = catalog.home / 'priority-resume-original.json'
        if not marker.exists():
            active = [r for r in catalog.index if r['id'] not in ids and catalog.state['items'][r['id']]['status'] == 'in_progress']
            base.atomic(marker, {'ids': [r['id'] for r in active], 'complete': False})
        resume = json.loads(marker.read_text())
        if not resume['complete']:
            for identifier in resume['ids']:
                if catalog.state['items'][identifier]['status'] not in ('accepted', 'blocked'):
                    with (base.ROOT / 'auto-refinement.lock').open('a') as render_lock:
                        fcntl.flock(render_lock, fcntl.LOCK_EX)
                        catalog.process(catalog.by_id[identifier])
            base.atomic(marker, {**resume, 'complete': True})
        catalog.run()


if __name__ == '__main__':
    main()
