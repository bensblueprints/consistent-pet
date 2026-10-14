from pathlib import Path
import collections,hashlib,json
from PIL import Image
root=Path(__file__).resolve().parent.parent
rows=[json.loads(line) for line in (root/'metadata.jsonl').read_text(encoding='utf8').splitlines()]
assert len(rows)==725 and len({r['id'] for r in rows})==725 and len({r['sha256'] for r in rows})==725
assert rows==json.loads((root/'catalog.json').read_text(encoding='utf8'))
for r in rows:
 assert r['sex'] in ['male','female','unisex'] and r['file_name'].split('/')[1]==r['sex']
 for field,hashfield in [('file_name','sha256'),('print_variant','print_variant_sha256')]:
  if not r[field]:continue
  p=(root/r[field]).resolve();assert p.is_relative_to(root) and p.is_file()
  with p.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==r[hashfield],r['id']
  with Image.open(p) as image:image.verify()
 with Image.open(root/r['preview']) as image:assert image.width<=360 and image.height<=450;image.verify()
 assert 'user_' not in json.dumps(r) and 'templates/' not in json.dumps(r)
print(json.dumps({'validated_concepts':len(rows),'sex':dict(collections.Counter(r['sex'] for r in rows)),'categories':len({r['category'] for r in rows}),'poster_variants':sum(bool(r['print_variant']) for r in rows)}))
