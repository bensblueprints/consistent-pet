"""Submit the accepted catalog recipes to Higgsfield.

Default is a dry run: it validates every package and prints the exact request
that would be sent. Nothing is submitted and no money is spent without
--submit-and-pay. Each image costs one Higgsfield generation; check the current
price before submitting a batch.

    python scripts/push-higgsfield-recipes.py
    python scripts/push-higgsfield-recipes.py --package costumes300-093-winter-carnival-queen
    HF_KEY=... python scripts/push-higgsfield-recipes.py --submit-and-pay --limit 1

The API key is read from HF_KEY or HIGGSFIELD_API_KEY. Never commit it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / 'workflows' / 'higgsfield' / 'index.json'
API = os.getenv('HF_API_BASE_URL', 'https://api.higgsfield.ai').rstrip('/')
MODEL = 'alibaba/qwen-image-3/edit'


def key() -> str:
    return os.getenv('HIGGSFIELD_API_KEY') or os.getenv('HF_KEY') or ''


def payload(package: dict) -> dict:
    generation = package['higgsfield']['template_regeneration']
    if not package.get('reference_url'):
        raise ValueError('missing reference_url')
    return {
        'prompt': generation['prompt'],
        'image_urls': [package['reference_url']],
        'resolution': generation.get('resolution', '1k'),
        'aspect_ratio': generation.get('aspect_ratio', '3:4'),
        'prompt_extend': generation.get('prompt_extend', True),
        'enable_thinking': generation.get('enable_thinking', True),
        'prompt_extend_mode': generation.get('prompt_extend_mode', 'direct'),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', action='append', default=[])
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--submit-and-pay', action='store_true')
    args = parser.parse_args()

    index = json.loads(INDEX.read_text(encoding='utf-8'))
    wanted = set(args.package)
    packages = [row for row in index['images']
                if not wanted or row['id'] in wanted]
    if args.limit:
        packages = packages[:args.limit]
    if wanted - {row['id'] for row in packages}:
        print('unknown package ids:', sorted(wanted - {row['id'] for row in packages}),
              file=sys.stderr)
        raise SystemExit(2)

    checked, problems = 0, []
    for row in packages:
        path = ROOT / row['recipe']
        try:
            body = payload(json.loads(path.read_text(encoding='utf-8')))
        except Exception as error:  # noqa: BLE001 - report every bad package
            problems.append((row['id'], str(error)))
            continue
        checked += 1
        if args.submit_and_pay:
            if not key():
                raise SystemExit('HF_KEY is required for --submit-and-pay')
            response = requests.post(f'{API}/{MODEL}', timeout=90,
                                     headers={'Authorization': 'Key ' + key(),
                                              'Content-Type': 'application/json'},
                                     json=body)
            if response.status_code >= 300:
                print(f'{row["id"]}: HTTP {response.status_code} {response.text[:200]}',
                      file=sys.stderr)
                raise SystemExit(1)
            result = response.json()
            print(json.dumps({'id': row['id'], 'request_id': result.get('request_id'),
                              'status_url': result.get('status_url')}))
        elif checked <= 3:
            print(json.dumps({'id': row['id'], 'reference_url': body['image_urls'][0],
                              'prompt_chars': len(body['prompt'])}, indent=1))

    print(json.dumps({
        'packages': len(packages),
        'validated': checked,
        'problems': problems,
        'submitted': checked if args.submit_and_pay else 0,
        'estimated_cost_usd': round(checked * 0.04, 2),
        'mode': 'submit' if args.submit_and_pay else 'dry-run',
    }, indent=1))


if __name__ == '__main__':
    main()
