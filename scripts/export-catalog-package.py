"""Export the stopped catalog run into reproducible per-image packages.

Inputs are the files pulled from the RTX 6000 into .artifacts/export-tmp:
catalog-references.json, the roster-screening-v6 queue and every accepted
workflow. Outputs are committed under workflows/:

  accepted/<id>.json          sanitized accepted recipes (ComfyUI graph + recipe)
  higgsfield/<id>.json        one regeneration package per image
  higgsfield/index.json       package manifest
  backlog/unfinished-jobs.json  pending, retry and blocked work for a later run
  backlog/jobs/<id>.json      base ComfyUI graph for each backlog item
  catalog-export.json         merged catalog metadata for the storefront

No customer photographs, dog identifiers or runtime secrets are written.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / '.artifacts' / 'export-tmp'
SITE = Path('C:/Users/DELL/pawtography-ai')
KEY = 'bensblueprints/consistent-pet'
HF_BASE = f'https://huggingface.co/datasets/{KEY}/resolve/main'

NEW_GROUPS = {
    'masterpieces75': 'Fine Art Masterpieces',
    'heaven24': 'Heaven & Angels',
}
CATEGORY_LABELS = {
    'jesus-with-dogs': 'Jesus & Dogs',
}
GROUP_ORDER = [
    'Royals & Storybooks', 'Heroes & Space', 'Movie Stars & Mischief',
    'Adventure & Travel', 'Sports & Speed', 'Everyday Characters',
    'Cozy & Coastal', 'Celebrations & Keepsakes', 'Vintage & Cover Stars',
    'Music & Studio', 'Fine Art Masterpieces', 'Heaven & Angels',
]


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def slug(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def clean_name(value: str) -> str:
    return ' '.join(value.replace('\u2014', '-').split())


def category_label(value: str) -> str:
    return CATEGORY_LABELS.get(value, value.replace('-', ' ').title())


def preview_prompt(meta: dict, accepted: dict) -> str:
    return (
        'Create one premium full-bleed pet portrait template, vertical 4:5, '
        'cinematic fine-art realism and detailed natural texture, beautifully '
        'art-directed for a framed print. Use the reference dog\'s natural face and '
        'markings. Exactly ONE dog in the scene. Dog face large, clearly visible, '
        'front or three-quarter view, eyes sharp; entire ears inside the image with '
        'comfortable 12% top breathing room. A real dog wearing dog-tailored costume, '
        'natural canine shoulders, chest, body and paws. NO human body, NO human hands, '
        'NO human characters, NO lettering, NO watermark, NO frame mockup. '
        f'Category: {meta["category"]}. Scene: {accepted.get("scene", meta.get("description", ""))}. '
        f'Costume: {accepted.get("clothing", "")}. Natural dog anatomy under the outfit.'
    )


def customer_prompt(meta: dict) -> str:
    return (
        'Create a polished, portrait-oriented pet portrait featuring the exact same dog '
        'from reference image 1, named {dog_name}. Image 1 is the identity source of truth: '
        'preserve this dog\'s recognizable face, muzzle, eyes, natural ears, coat colors, '
        'markings, fur length, and age. Image 2 is the selected artwork design reference. '
        'Recreate its costume, props, color palette, artistic medium, lighting, and scene '
        'as closely as practical, adapting everything to a real dog\'s anatomy and '
        f'proportions. Style: {meta["name"]}. Design notes: {meta.get("description", "")}. '
        'Show one complete dog with a natural canine head and body, no humans, '
        'no second animal, no text, no watermark.'
    )


def main() -> None:
    refs = load(TMP / 'catalog-references.json')['rows']
    queue = load(TMP / 'catalog-refinement' / 'roster-screening-v6' / 'queue.json')['items']
    index = load(ROOT / 'workflows' / 'portraits' / 'index.json')
    library = load(ROOT / 'reference-library' / 'catalog.json')
    site = load(SITE / 'public' / 'catalog.json')
    ready = load(SITE / 'public' / 'ready-workflows.json')

    by_lib = {row['id']: row for row in library}
    by_site = {row['id']: row for row in site}
    by_ready = {row['id']: row for row in ready}
    by_ref = {row['id'].removeprefix('catalog-reference-'): row for row in refs}
    by_index = {row['id']: row for row in index}

    accepted_files = {}
    for path in TMP.glob('auto-refinement/*/accepted/*.json'):
        accepted_files[path.stem] = load(path)

    accepted_ids = sorted(k for k, v in queue.items() if v['status'] == 'accepted')
    accepted_ids = [i for i in accepted_ids if i in accepted_files or i in by_ready]

    out_accepted = ROOT / 'workflows' / 'accepted'
    out_hf = ROOT / 'workflows' / 'higgsfield'
    out_backlog = ROOT / 'workflows' / 'backlog'
    out_jobs = out_backlog / 'jobs'
    for path in (out_accepted, out_hf, out_backlog, out_jobs):
        path.mkdir(parents=True, exist_ok=True)

    catalog_rows = []
    hf_index = []
    skipped = []

    for image_id in accepted_ids:
        record = accepted_files.get(image_id)
        base = by_site.get(image_id) or {}
        ref = by_ref.get(image_id, {})
        idx = by_index.get(image_id, {})
        lib = by_lib.get(image_id, {})

        pack = ref.get('pack') or lib.get('collection') or base.get('collection') or ''
        name = base.get('name') or clean_name(ref.get('template') or lib.get('name') or image_id)
        sex = base.get('sex') or lib.get('sex') or 'unisex'
        category = base.get('category') or category_label(ref.get('category') or 'Uncategorised')
        group = base.get('group') or NEW_GROUPS.get(pack, 'Uncategorised')
        description = lib.get('description') or base.get('description') or ' '.join((record or {}).get('scene', '').split())[:240]

        raw_category = ref.get('category') or lib.get('category') or category
        cat_slug = slug(raw_category)
        reference_url = idx.get('reference_url')
        if not reference_url and pack in NEW_GROUPS:
            reference_url = f'{HF_BASE}/references/{sex}/{cat_slug}/{image_id}.png'
        reference_url = reference_url or None
        preview = base.get('preview') or f'previews/{sex}/{cat_slug}/{image_id}.webp'

        sha = (record or {}).get('sha256') or by_ready.get(image_id, {}).get('sha256')
        average = ((record or {}).get('evaluation') or {}).get('average_score') \
            or by_ready.get(image_id, {}).get('average')

        if record:
            sanitized = {
                'format': record.get('format'),
                'template_id': record.get('template_id', image_id),
                'status': record.get('status'),
                'scene': record.get('scene', ''),
                'clothing': record.get('clothing', ''),
                'recipe': record.get('recipe', {}),
                'graph': record.get('graph', {}),
                'evaluation': record.get('evaluation', {}),
                'thresholds': record.get('thresholds'),
                'binding': record.get('binding'),
                'sha256': sha,
            }
            (out_accepted / f'{image_id}.json').write_text(
                json.dumps(sanitized, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        else:
            skipped.append(image_id)

        source = {
            'provider': lib.get('source_provider'),
            'model': lib.get('source_model'),
            'variant': lib.get('source_variant'),
            'prompt': lib.get('prompt'),
            'reference_used': lib.get('reference_used'),
            'source_known': bool(lib.get('prompt')),
        }
        package = {
            'format': 'pawtography-higgsfield-recipe-v1',
            'id': image_id,
            'name': name,
            'category': category,
            'group': group,
            'collection': pack,
            'sex': sex,
            'description': description,
            'average_score': average,
            'workflow_sha256': sha,
            'reference_url': reference_url,
            'preview_url': f'https://pawtography.ai/{preview}',
            'higgsfield': {
                'source_art': {
                    'provider': source['provider'],
                    'model': source['model'],
                    'variant': source['variant'],
                    'prompt': source['prompt'],
                    'source_known': source['source_known'],
                },
                'customer_generation': {
                    'provider': 'Higgsfield',
                    'model': 'alibaba/qwen-image-3/edit',
                    'image_slots': ['identity: customer dog photo', 'design: reference_url'],
                    'prompt': customer_prompt({'name': name, 'description': description}),
                    'resolution': '1k',
                    'aspect_ratio': '3:4',
                    'prompt_extend': True,
                    'enable_thinking': True,
                    'prompt_extend_mode': 'direct',
                },
                'template_regeneration': {
                    'prompt': preview_prompt({'name': name, 'category': category,
                                              'description': description}, record or {}),
                    'image_slots': ['design: reference_url'],
                    'resolution': '1k',
                    'aspect_ratio': '3:4',
                },
            },
            'local_refinement': {
                'format': (record or {}).get('format', 'legacy-approved'),
                'workflow_file': f'workflows/accepted/{image_id}.json' if record else None,
                'recipe': (record or {}).get('recipe'),
                'evaluation': (record or {}).get('evaluation'),
                'note': None if record else 'Owner-approved before the v2 export format; checksum kept, graph not re-exported.',
            },
        }
        (out_hf / f'{image_id}.json').write_text(
            json.dumps(package, indent=1, sort_keys=True) + '\n', encoding='utf-8')

        catalog_rows.append({
            'id': image_id, 'name': name, 'sex': sex, 'category': category,
            'description': description, 'preview': preview, 'group': group,
            'collection': pack, 'average': average, 'sha256': sha,
            'reference_url': reference_url,
        })
        hf_index.append({
            'id': image_id, 'name': name, 'group': group, 'category': category,
            'collection': pack, 'average': average, 'sha256': sha,
            'recipe': f'workflows/higgsfield/{image_id}.json',
            'workflow': f'workflows/accepted/{image_id}.json' if record else None,
        })

    catalog_rows.sort(key=lambda row: (GROUP_ORDER.index(row['group'])
                                       if row['group'] in GROUP_ORDER else 99,
                                       row['category'], row['name']))
    hf_index.sort(key=lambda row: row['id'])

    (out_hf / 'index.json').write_text(json.dumps({
        'format': 'pawtography-higgsfield-index-v1',
        'count': len(hf_index),
        'groups': GROUP_ORDER,
        'images': hf_index,
    }, indent=1) + '\n', encoding='utf-8')
    (ROOT / 'workflows' / 'catalog-export.json').write_text(
        json.dumps({'count': len(catalog_rows), 'images': catalog_rows}, indent=1) + '\n',
        encoding='utf-8')

    backlog = []
    for image_id, item in sorted(queue.items()):
        if item['status'] == 'accepted':
            continue
        ref = by_ref.get(image_id, {})
        idx = by_index.get(image_id, {})
        base = by_site.get(image_id, {})
        pack = ref.get('pack') or ''
        category = base.get('category') or category_label(ref.get('category') or '')
        sex = base.get('sex') or 'unisex'
        cat_slug = slug(ref.get('category') or category)
        job = TMP / 'catalog-jobs' / f'catalog-reference-{image_id}.json'
        packaged = None
        if job.exists():
            packaged = f'workflows/backlog/jobs/{image_id}.json'
            shutil.copyfile(job, out_jobs / f'{image_id}.json')
        backlog.append({
            'id': image_id,
            'name': base.get('name') or clean_name(ref.get('template') or image_id),
            'category': category,
            'collection': pack,
            'status': item['status'],
            'last_error_type': item.get('last_error_type'),
            'round': item.get('round'),
            'generations': item.get('generations'),
            'errors': item.get('errors'),
            'run': item.get('run'),
            'reference_url': idx.get('reference_url')
            or f'{HF_BASE}/references/{sex}/{cat_slug}/{image_id}.png',
            'base_job': packaged,
            'resume': 'Re-run roster-screening-v6 for this id on the GPU host; the base graph is in base_job.',
        })

    counts = {}
    for item in backlog:
        counts[item['status']] = counts.get(item['status'], 0) + 1
    (out_backlog / 'unfinished-jobs.json').write_text(json.dumps({
        'format': 'pawtography-catalog-backlog-v1',
        'source_run': 'roster-screening-v6',
        'stopped_at': '2026-10-19T10:39:00Z',
        'counts': counts,
        'accepted_at_stop': len(accepted_ids),
        'jobs': backlog,
        'how_to_resume': [
            'Start fpg-catalog-resume on the RTX 6000 host.',
            'The runner reads catalog-refinement/roster-screening-v6/queue.json.',
            'Pending and retry_pending items continue automatically.',
            'Blocked items need a policy or input fix: UnsupportedMultiSubject and ValueError '
            'entries failed repeatedly; PriorityAttemptCap items hit the priority cap.',
        ],
    }, indent=1) + '\n', encoding='utf-8')

    print(json.dumps({
        'accepted_packages': len(hf_index),
        'accepted_with_graph': len(hf_index) - len(skipped),
        'legacy_only': skipped,
        'backlog': counts,
        'new_catalog_rows': len([r for r in catalog_rows if r['id'] not in by_site]),
    }, indent=1))


if __name__ == '__main__':
    main()
