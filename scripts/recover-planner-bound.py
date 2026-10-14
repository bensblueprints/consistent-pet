"""Explicit operator recovery for an out-of-range design-conditioning proposal.

Does not change the critic, code fingerprints, native jobs or saved assessments.
Stop only the catalog refiner before running; the vision judge may stay running.
"""
import argparse
import copy
import json
import math
import shutil
import sys
import time
from pathlib import Path


def repaired_result(request, response, value, validate, signature):
    if response.get('error') != 'Invalid planner design_megapixels':
        raise ValueError('This tool only repairs a rejected design_megapixels bound')
    fingerprint = signature(request['payload'])
    if request['fingerprint'] != fingerprint or response['fingerprint'] != fingerprint:
        raise ValueError('Request/response fingerprints differ')
    if not math.isfinite(value):
        raise ValueError('Replacement must be finite')
    raw = response['raw']
    proposal = json.loads(raw[raw.find('{'):raw.rfind('}') + 1])
    previous = proposal['design_megapixels']
    proposal['design_megapixels'] = value
    proposal = validate(proposal)  # Use the original frozen runner's full validator.
    result = copy.deepcopy(response)
    result.pop('error')
    result['proposal'] = proposal
    result['operator_recovery'] = {'parameter': 'design_megapixels', 'before': previous,
                                   'after': value, 'recovered_at': time.time(),
                                   'note': 'Explicit bounded parameter repair; quality checks unchanged.'}
    return result


def main():
    import fcntl  # Runtime recovery is Linux-only; validation helpers are portable.
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--runner', type=Path, required=True)
    p.add_argument('--queue-version', required=True)
    p.add_argument('--reference-id', required=True)
    p.add_argument('--request-id', required=True)
    p.add_argument('--design-megapixels', type=float, required=True)
    a = p.parse_args()
    for name in (a.queue_version, a.reference_id, a.request_id):
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):
            raise ValueError('Unsafe identifier')
    sys.path.insert(0, str(a.runner))
    from portrait_llm_planner import validate, atomic
    from portrait_autorefine import signature
    with (a.root / 'catalog-refinement.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        queue = a.root / 'catalog-refinement' / a.queue_version / 'queue.json'
        state = json.loads(queue.read_text())
        item = state['items'][a.reference_id]
        if item['status'] != 'blocked' or not a.request_id.startswith(item['run'] + '-'):
            raise ValueError('Target is not the blocked run matching this request')
        request_path = a.root / 'planner-requests' / (a.request_id + '.json')
        result_path = request_path.with_name(a.request_id + '.result.json')
        request = json.loads(request_path.read_text())
        response = json.loads(result_path.read_text())
        result = repaired_result(request, response, a.design_megapixels, validate, signature)
        backup = a.root / 'planner-recovery' / str(time.time_ns())
        backup.mkdir(parents=True)
        for file in (queue, request_path, result_path):
            shutil.copy2(file, backup / file.name)
        item.setdefault('recoveries', []).append({**result['operator_recovery'], 'previous_errors': item['errors']})
        item.update(status='in_progress', errors=0)
        state['updated_at'] = time.time()
        atomic(result_path, result)
        atomic(queue, state)
        print('Repaired bounded proposal and requeued the same run; backups retained; no new GPU job submitted.')


if __name__ == '__main__':
    main()
