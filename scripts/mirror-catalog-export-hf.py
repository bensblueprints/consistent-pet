"""Upload the stopped catalog run's reference art and recipes to Hugging Face.

Reference PNGs are the templates the GPU renders against. They are too large for
the GitHub LFS budget, so the dataset is their canonical home; the recipe files
point at the resulting URLs.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from huggingface_hub import CommitOperationAdd, HfApi

ROOT = Path(__file__).resolve().parent.parent
REPO = 'bensblueprints/consistent-pet'
TOKEN = (Path.home() / '.cache' / 'huggingface' / 'token').read_text().strip()
TMP = ROOT / '.artifacts' / 'export-tmp'


def batches(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def commit(api: HfApi, operations, message: str) -> None:
    for attempt in range(1, 4):
        try:
            api.create_commit(REPO, repo_type='dataset', operations=operations,
                              commit_message=message)
            return
        except Exception:  # noqa: BLE001 - retry transient upload failures
            if attempt == 3:
                raise
            time.sleep(5 * attempt)


def main() -> None:
    api = HfApi(token=TOKEN)
    remote = set(api.list_repo_files(REPO, repo_type='dataset'))

    export = json.loads((ROOT / 'workflows' / 'catalog-export.json').read_text(encoding='utf-8'))

    pending = []
    for row in export['images']:
        if not row.get('reference_url', '').startswith('https://huggingface.co/'):
            continue
        remote_path = row['reference_url'].split('/resolve/main/', 1)[1]
        local = TMP / 'media' / f'catalog-{row["id"]}-reference.png'
        if remote_path in remote or not local.exists():
            continue
        pending.append((remote_path, local))

    print(f'reference uploads pending: {len(pending)}', flush=True)
    done = 0
    for chunk in batches(pending, 4):
        operations = [CommitOperationAdd(path_in_repo=remote_path, path_or_fileobj=str(local))
                      for remote_path, local in chunk]
        commit(api, operations, f'Add catalog reference art {done + 1}-{done + len(chunk)}')
        done += len(chunk)
        print(f'uploaded references {done}/{len(pending)}', flush=True)

    files = []
    for folder in ('workflows/accepted', 'workflows/higgsfield', 'workflows/backlog'):
        files.extend(sorted((ROOT / folder).rglob('*.json')))
    files.append(ROOT / 'workflows' / 'catalog-export.json')
    pending = [(str(path.relative_to(ROOT)).replace('\\', '/'), path)
               for path in files if str(path.relative_to(ROOT)).replace('\\', '/') not in remote]
    print(f'workflow uploads pending: {len(pending)}', flush=True)
    done = 0
    for chunk in batches(pending, 40):
        operations = [CommitOperationAdd(path_in_repo=remote_path, path_or_fileobj=str(local))
                      for remote_path, local in chunk]
        commit(api, operations, f'Publish accepted catalog recipes {done + 1}-{done + len(chunk)}')
        done += len(chunk)
        print(f'uploaded workflows {done}/{len(pending)}', flush=True)

    print(json.dumps({'reference_files': done, 'workflow_files': len(files)}))


if __name__ == '__main__':
    main()
