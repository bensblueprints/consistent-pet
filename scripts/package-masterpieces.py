"""Package owner-approved dog paintings; never mark untuned recipes accepted."""
import argparse,hashlib,json,re,shutil,unicodedata
from pathlib import Path
from PIL import Image

GROUPS={
 'Renaissance':[1,11,12,13,15,19,20,21,22,25,32,57,65,66,67,68,69,70,71,72,90,91,92,97,98,99],
 'Mannerism':[14,23,24,26,27,60,61,73,74],
 'Baroque':[2,3,7,8,18,28,29,30,31,48,58,59,62,100],
 'Rococo':[10],
 'Neoclassicism':[33,34,35,36,37,38,39,63],
 'Romanticism':[64],
 'Realism':[5,6,17,40,43,49,50,51,52,53,54,75,76,77,94],
 'Impressionism':[41,42,78,79,80],
 'Post-Impressionism':[9,16,47],
 'Art Nouveau':[4,55,56,87],
 'Early Modernism':[44,45],
 'Cubism':[46],
 'Expressionism':[81,83,84,85],
 'Vorticism':[82],
 'Pop Art':[86],
 'Surrealism':[88,89],
 'Symbolism':[93],
 'Pre-Raphaelite':[95,96]
}
# Classify each artwork, not the artist's entire career.
for i,g in {65:'Baroque',66:'Baroque',90:'Neoclassicism',91:'Neoclassicism',92:'Neoclassicism',17:'Early Modernism'}.items():
 for ids in GROUPS.values():
  if i in ids:ids.remove(i)
 GROUPS[g].append(i)
GROUP_SCENES={3,7,13,22,27,40,50,51,59,64,77,85,86,89,91}
INSTRUCTION=('Preserve the original painting\'s composition, clothing, accessories, pose, background, palette, lighting, brushwork and surface texture. '
 'Transfer the uploaded pet\'s recognizable face, muzzle, ear shape, coat markings and fur pattern into the painted figure. '
 'Render the pet using the painting\'s own visual language, never a photographic face pasted onto a painting. '
 'Do not inherit the reference dog\'s breed, identity or markings. Keep the body clothed, without human breasts. '
 'Preserve original aspect ratio and important scene elements; no automatic portrait crop. '
 'Review both identity preservation and fidelity to the original artwork before accepting the reusable recipe.')
def slug(v):return re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',v).encode('ascii','ignore').decode().lower()).strip('-')
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);a=p.parse_args()
 refs={x['index']:x for x in json.loads((a.source/'references.json').read_text(encoding='utf-8'))}
 jobs=[x for x in json.loads((a.source/'jobs.json').read_text()) if x.get('status')=='completed']
 assert len(jobs)==75 and len({x['index'] for x in jobs})==75
 baseline=json.loads((a.repo/'workflows/portraits/heaven-001-jesus-and-golden-retriever/baseline.api.json').read_text())
 rows=[]
 for job in sorted(jobs,key=lambda x:x['index']):
  i=job['index'];r=refs[i];movement=next(k for k,v in GROUPS.items() if i in v);category=slug(movement);rid=f'masterpieces-{i:03d}-'+slug(r['title']);folder=a.repo/'workflows/portraits'/rid
  if folder.exists():raise RuntimeError(f'Existing workflow must not be overwritten: {rid}')
  source=a.source/'outputs'/f'{i:03d}.png';refpath=Path('reference-library/references/unisex')/category/(rid+'.png');previewpath=Path('reference-library/previews/unisex')/category/(rid+'.webp')
  (a.repo/refpath).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,a.repo/refpath)
  (a.repo/previewpath).parent.mkdir(parents=True,exist_ok=True)
  with Image.open(source) as im:
   width,height=im.size;im.thumbnail((560,640));im.save(a.repo/previewpath,'WEBP',quality=83)
  flags=['preserve-original-painting-style','preserve-source-aspect-ratio','identity-transfer-not-validated']
  if i in GROUP_SCENES:flags+=['multiple-figures-require-explicit-identity-mapping']
  row=dict(id=rid,name=r['title']+' — Dog Portrait',sex='unisex',category=category,art_movement=movement,collection='masterpieces75',reference_path=refpath.as_posix(),preview_path=previewpath.as_posix(),reference_url=job['result_url'],reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),workflow_folder='workflows/portraits/'+rid,description=f"Dog interpretation of {r['title']} by {r['artist']}. {INSTRUCTION}",original_artwork={'title':r['title'],'artist':r['artist'],'source_page':r['page_url']},width=width,height=height,qa_flags=flags,customer_identity_transfer_validated=False,production_enabled=False,refinement_instructions=INSTRUCTION)
  graph=json.loads(json.dumps(baseline));scale=min(1040/max(width,height),1);w=max(256,round(width*scale/32)*32);h=max(256,round(height*scale/32)*32)
  for node in graph.values():
   inputs=node.get('inputs',{})
   if isinstance(inputs.get('width'),int) and isinstance(inputs.get('height'),int):inputs['width']=w;inputs['height']=h
  write(folder/'reference.json',row);write(folder/'baseline.api.json',graph)
  write(folder/'status.json',{'reference_id':rid,'status':'not_started','accepted_workflow':None,'customer_identity_transfer_validated':False,'production_enabled':False,'queue_registration':'pending_gpu_connection','last_run_version':None})
  (folder/'README.md').write_text(f"# {row['name']}\n\nArt movement: {movement}.\n\n{INSTRUCTION}\n\nStarting graph only; not validated or production-enabled. Append behind existing queue.\n\n![Reference](../../../{previewpath.as_posix()})\n",encoding='utf-8')
  rows.append(row)
 write(a.repo/'workflows/portraits/append-masterpieces75.json',rows)
 write(a.source/'movement-catalog.json',rows)
 print('Packaged',len(rows),'workflow folders and references; all remain not_started.')
if __name__=='__main__':main()
