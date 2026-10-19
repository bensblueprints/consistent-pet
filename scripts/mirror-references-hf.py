"""Upload reference images and previews that are missing from the mirrored datasets.

Reference images are the templates the GPU renders against, so they must travel with
the workflow rows. They are LFS objects, which git-archive would emit as pointers, so
this mirrors them from the working tree instead.
"""
from pathlib import Path
import time

BATCH = 10
RETRIES = 4


def targets():
    home = Path.home()
    return [
        ('bensblueprints/consistent-pet', home / '.cache/huggingface/token'),
        ('benjithedeveloper/consistent-pet', home / '.cache/huggingface/token-secondary'),
    ]


def wanted(repo):
    library = Path(repo) / 'reference-library'
    files = list((library / 'references').rglob('*.png')) + list((library / 'previews').rglob('*.webp'))
    return sorted((str(path.relative_to(library)).replace('\\', '/'), path) for path in files)


def upload(repo_id, token_path, todo, library):
    from huggingface_hub import CommitOperationAdd, HfApi

    api = HfApi(token=token_path.read_text().strip())
    remote = set(api.list_repo_files(repo_id, repo_type='dataset'))
    pending = [(rel, path) for rel, path in todo if rel not in remote]
    done = 0
    for start in range(0, len(pending), BATCH):
        chunk = pending[start:start + BATCH]
        operations = [CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(path)) for rel, path in chunk]
        for attempt in range(1, RETRIES + 1):
            try:
                api.create_commit(repo_id=repo_id, repo_type='dataset', operations=operations,
                                  commit_message=f'Mirror reference images {done + 1}-{done + len(chunk)}')
                done += len(chunk)
                break
            except Exception:
                if attempt == RETRIES:
                    raise
                time.sleep(5 * attempt)
    return done


def sync(repo):
    library = Path(repo) / 'reference-library'
    todo = wanted(repo)
    result = {}
    for repo_id, token_path in targets():
        if not token_path.exists():
            continue
        result[repo_id] = upload(repo_id, token_path, todo, library)
    return result
