"""Create one GPU work folder per reference without overwriting existing work."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / 'reference-library'
DEST = ROOT / 'workflows' / 'portraits'


def create_only(path, content):
    if not path.exists():
        path.write_text(content, encoding='utf-8')


def main():
    rows = json.loads((LIBRARY / 'catalog.json').read_text(encoding='utf-8'))
    assert len(rows) == 725 and len({r['id'] for r in rows}) == 725
    baseline = (ROOT / 'workflows/flux-klein-4b-base-api.json').read_text(encoding='utf-8')
    json.loads(baseline)
    index = []
    for row in rows:
        identifier = row['id']
        assert Path(identifier).name == identifier and '/' not in identifier and '\\' not in identifier
        folder = DEST / identifier
        folder.mkdir(parents=True, exist_ok=True)
        record = {
            'id': identifier, 'name': row['name'], 'sex': row['sex'],
            'category': row['category'], 'collection': row['collection'],
            'reference_path': 'reference-library/' + row['file_name'],
            'preview_path': 'reference-library/' + row['preview'],
            'reference_url': 'https://huggingface.co/datasets/bensblueprints/consistent-pet/resolve/main/' + row['file_name'],
            'reference_sha256': row['sha256'],
            'workflow_folder': 'workflows/portraits/' + identifier,
            'qa_flags': row['qa_flags'],
            'description': row['description'],
            'source_generation_prompt': row['prompt'],
        }
        create_only(folder / 'reference.json', json.dumps(record, indent=2, ensure_ascii=False) + '\n')
        create_only(folder / 'baseline.api.json', baseline)
        create_only(folder / 'status.json', json.dumps({
            'reference_id': identifier,
            'status': 'pending_gpu_refinement',
            'target_hardware': 'RTX PRO 6000 Blackwell 96 GB',
            'baseline_sha256': hashlib.sha256(baseline.encode()).hexdigest(),
            'baseline_is_reference_specific': False,
            'customer_identity_transfer_validated': False,
            'requires_design_review': bool(row['qa_flags']),
            'accepted_workflow': None,
            'latest_provisional_workflow': None,
            'last_run_version': None,
            'last_updated_utc': None,
        }, indent=2) + '\n')
        create_only(folder / 'README.md', f'''# {row['name']}

Reference ID: `{identifier}`  
Category: {row['category']} | Costume eligibility: {row['sex']}

![Reference preview](../../../reference-library/{row['preview']})

- [Full-resolution reference](../../../reference-library/{row['file_name']})
- [Direct image download]({record['reference_url']})
- [RTX 6000 handoff](../../../HANDOFF.md)
- `reference.json`: source mapping, SHA256, prompt and review flags. Paths are relative to the repository root.
- `baseline.api.json`: copy of the shared FLUX Klein baseline; placeholders remain unbound. It is NOT a tuned or accepted workflow for this picture.
- `status.json`: current progress; update only from actual run evidence.

Use the RTX 6000 refinement process in the handoff. Save a sanitized, accepted export as `workflow.json` only after all required checks pass. Save an unsuccessful best attempt as `provisional.workflow.json` and explain it in `REPORT.md`; never label it accepted. Keep private photos, masks, actual job graphs, scores and customer outputs in the private runtime, outside Git. Public reports must omit dog identities and private paths.
''')
        index.append({k: record[k] for k in ('id', 'name', 'sex', 'category', 'collection', 'reference_path', 'reference_url', 'reference_sha256', 'workflow_folder')})
    (DEST / 'index.json').write_text(json.dumps(index, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Prepared {len(index)} reference workflow folders; existing files preserved. No GPU jobs submitted.')


if __name__ == '__main__':
    main()
