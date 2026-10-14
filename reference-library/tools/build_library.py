"""Package approved template masters only. Never scan customer storage or upload journals."""
from pathlib import Path
import argparse, collections, concurrent.futures, hashlib, html, json, re, shutil
from PIL import Image

ORIGINAL = {
 'renaissance-king':('male','Royalty'), 'victorian-duchess':('female','Royalty'),
 'steampunk-explorer':('unisex','Steampunk and Time Travel'), 'galactic-emperor':('male','Science Fiction'),
 'space-commander':('unisex','Science Fiction'), 'pirate-captain':('unisex','Pirates and Naval'),
 'medieval-knight':('unisex','Knights and Warriors'), 'forest-wizard':('unisex','Fantasy and Magic'),
 'samurai-warrior':('unisex','Knights and Warriors'), 'ancient-pharaoh':('unisex','Royalty'),
 'viking-explorer':('unisex','Knights and Warriors'), 'wild-west-sheriff':('unisex','Western'),
 'royal-navy-admiral':('unisex','Pirates and Naval'), 'jazz-club-legend':('unisex','Music and Performance'),
 'secret-agent':('unisex','Detectives and Secret Agents'), 'mad-scientist':('unisex','Science and Inventors'),
 'cyberpunk-hacker':('unisex','Science Fiction'), 'dragon-guardian':('unisex','Fantasy and Magic'),
 'underwater-monarch':('unisex','Fantasy and Magic'), 'celestial-guardian':('unisex','Fantasy and Magic'),
 'time-traveler':('unisex','Steampunk and Time Travel'), 'grandmaster-detective':('unisex','Detectives and Secret Agents'),
 'arctic-expedition-leader':('unisex','Exploration'), 'enchanted-garden-queen':('female','Royalty'),
 'rainbow-bridge-guardian':('unisex','Memorial and Remembrance'),
}
COLLECTIONS = [('2026-10-13','surreal'),('2026-10-13-vintage','vintage'),('2026-10-13-mobsters-and-superheroes','cinematic'),('2026-10-14-costumes-300','costumes300')]
def slug(value): return re.sub(r'[^a-z0-9]+','-',value.lower()).strip('-')
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path): return hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
def safe_file(root,name):
 p=(root/name).resolve();assert p.is_relative_to(root.resolve()) and p.is_file(),name;return p

def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,required=True);p.add_argument('--originals',type=Path,required=True);p.add_argument('--original-manifest',type=Path,required=True);p.add_argument('--output',type=Path,default=Path('.'));a=p.parse_args();out=a.output.resolve()
 jobs=[]
 for folder,collection in COLLECTIONS:
  root=a.sources/folder;manifest=read(root/'manifest.json');completed=read(root/'completed-manifest.json')
  requests={x['index']:x['params'] for x in manifest.get('requests',[])}
  for r in completed:
   sex={'boy':'male','girl':'female'}.get(r['gender'],r['gender']);basis='original collection metadata'
   if collection=='vintage':
    sex='female' if r['index'] in [22,25,27] else 'male' if r['index'] in [21,84] else 'unisex'
    basis='costume/title eligibility; provisional alternating source boy/girl labels normalized'
   group=r.get('pack') if collection=='cinematic' else collection
   category=r['category'];idx=f'{group}-{r["index"]:03d}-{r["slug"]}'
   master=safe_file(root,r.get('artwork_file',r['file']));expected=r.get('artwork_sha256',r['sha256'])
   prompt=r.get('effective_prompt') or r.get('prompt') or requests.get(r['index'],{}).get('prompt','')
   flags=[]
   if collection=='surreal' and sex=='female':flags.append('anatomy-review-required')
   if collection=='vintage' and r['index'] in [19,30,80,94]:flags.append('multiple-subjects-or-age-variants')
   if collection=='original25' and r['slug']=='dragon-guardian':flags.append('secondary-creature')
   rec={'id':idx,'name':r['name'],'sex':sex,'category':category,'collection':group,'source_sex':r['gender'],'classification_basis':basis,
    'description':r.get('scene',''),'prompt':re.sub(r'https?://\S+','[source reference URL omitted]',prompt),
    'source_provider':'Higgsfield','source_model':'gpt_image_2_5','source_variant':'flare','reference_used':r.get('reference_used',True),
    'qa_flags':flags,'customer_identity_transfer_validated':False,'caption':r.get('caption','')}
   variant=safe_file(root,r['file']) if r.get('artwork_file') else None
   jobs.append((rec,master,expected,variant,r['sha256'] if variant else None))
 for r in read(a.original_manifest):
  sex,category=ORIGINAL[r['slug']];rec={'id':'original25-'+r['slug'],'name':r['name'],'sex':sex,'category':category,'collection':'original25',
   'source_sex':'unspecified','classification_basis':'costume/title eligibility','description':r['name'],
   'prompt':r['params']['prompt'],'source_provider':'Higgsfield','source_model':r['params']['model'],'source_variant':r['params'].get('variant','flare'),
   'reference_used':False,'qa_flags':['secondary-creature'] if r['slug']=='dragon-guardian' else [],'customer_identity_transfer_validated':False,'caption':''}
  jobs.append((rec,safe_file(a.originals,r['file']),r['sha256'],None,None))
 def package(job):
  rec,src,expected,variant,variant_hash=job;actual=digest(src);assert actual==expected,rec['id']
  rel=Path(rec['sex'])/slug(rec['category'])/(rec['id']+'.png');target=out/'references'/rel;target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists() or digest(target)!=actual:shutil.copyfile(src,target)
  with Image.open(src) as image:
   image.load();width,height=image.size;assert width>=1024 and height>=1024
   preview=out/'previews'/rel.with_suffix('.webp');preview.parent.mkdir(parents=True,exist_ok=True)
   if not preview.exists():
    image=image.convert('RGB');image.thumbnail((360,450));image.save(preview,'WEBP',quality=82,method=4)
  rec.update(file_name=target.relative_to(out).as_posix(),preview=preview.relative_to(out).as_posix(),sha256=actual,width=width,height=height,bytes=src.stat().st_size,
    print_variant='',print_variant_sha256='')
  if variant:
   assert digest(variant)==variant_hash
   dest=out/'print-variants'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists() or digest(dest)!=variant_hash:shutil.copyfile(variant,dest)
   with Image.open(dest) as image:image.verify()
   rec.update(print_variant=dest.relative_to(out).as_posix(),print_variant_sha256=variant_hash)
  return rec
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:records=list(ex.map(package,jobs))
 records.sort(key=lambda r:(r['sex'],r['category'],r['collection'],r['id']))
 assert len(records)==725 and len({r['id'] for r in records})==725 and len({r['sha256'] for r in records})==725
 (out/'metadata.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf8')
 (out/'catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 summary={'concepts':len(records),'distinct_master_hashes':len({r['sha256'] for r in records}),'print_variants':sum(bool(r['print_variant']) for r in records),
 'sex_counts':dict(collections.Counter(r['sex'] for r in records)),'collection_counts':dict(collections.Counter(r['collection'] for r in records)),
 'category_counts':dict(sorted(collections.Counter(r['category'] for r in records).items())),
 'master_bytes':sum(r['bytes'] for r in records),'all_image_bytes':sum(p.stat().st_size for folder in ['references','previews','print-variants'] for p in (out/folder).rglob('*') if p.is_file())}
 (out/'inventory.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
