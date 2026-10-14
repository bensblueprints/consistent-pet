"""Token-link investor view and reviews of the approved ten-dog demonstration.

Expose this dedicated service through HTTPS, never the private board or ComfyUI.
Only the selected demo batch, dog references, generated art and aggregate GPU stats
are served. Review writes are allowed; private job graphs and GPU controls are excluded.
"""
import json,os,secrets,urllib.parse
from portrait_reviews import ROOT,attach,handle_post
from portrait_judge_runtime import snapshot as judge_snapshot
from portrait_input_registry import public_catalog,MEDIA_FIELDS
from portrait_input_quality import public_scores
from pathlib import Path
from portrait_approval_timing import snapshot as approval_snapshot
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
R=ROOT;R.mkdir(parents=True,exist_ok=True);M=R/'media';TOKEN_FILE=R/'investor-share-token'
if not TOKEN_FILE.exists():TOKEN_FILE.write_text(secrets.token_urlsafe(24));TOKEN_FILE.chmod(0o600)
PREFIX='/view/'+TOKEN_FILE.read_text().strip()+'/'
def read(name,default):
 try:return json.loads((R/name).read_text())
 except (OSError,ValueError):return default
FIELDS=('id','index','pack','category','template','mode','input','reference','label','status','review','output','thumbnail','seconds','started','finished_at','preview','progress_max','progress_value','progress_seq','workflow_id','dog_id','prepared','preparation','baseline_output','baseline_label','repair_version','repair_mask','repair_design','auto_refine_version','auto_stage','auto_attempt','auto_target','auto_changes','auto_corrections','auto_rationale','input_quality','input_quality_notes','reference_id','generation','planner','strategy')
def public_state():
 prior=read('dog-batch.json',{'rows':[]});full=read('dog-library-batch.json',{'rows':[]})
 batch=full if full['rows'] else prior
 rows=read('dog-revisions.json',{'rows':[]})['rows']+full['rows']+prior['rows']
 result=[]
 for item in rows:
  row={k:item[k] for k in (*FIELDS,'output_thresholds','input_photo_score','acceptance_policy') if k in item}
  if row['status']=='Rendering':
   progress=read('progress/'+row['id']+'.json',{})
   row.update({k:v for k,v in progress.items() if k in FIELDS})
  result.append(row)
 safe_batch={k:batch[k] for k in ('status','counts','median_seconds') if k in batch}
 safe_batch['rows']=[{'id':r['id'],'status':r['status']} for r in batch['rows']]
 result=attach(result)
 auto=read('auto-refine-status.json',{})
 auto={k:auto[k] for k in ('run','status','generations','current_template','phase','target','max_generations','templates','finished','passed','updated_at','dogs') if k in auto}
 return {'rows':result,'batch':safe_batch,'gpu':read('gpu-status.json',{}),'judge':judge_snapshot(result,R),'auto_refine':auto,'input_catalog':public_catalog(read('input-catalog.json',{})),'catalog_progress':read('catalog-public-status.json',{}),'approval_timing':approval_snapshot(R),'input_photo_scores':public_scores(R)}
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  if urllib.parse.urlparse(self.path).path!=PREFIX+'review':self.send_error(404);return
  handle_post(self,public_state()['rows'])
 def do_GET(self):
  path=urllib.parse.urlparse(self.path).path
  if not path.startswith(PREFIX):self.send_error(404);return
  suffix=path[len(PREFIX):];state=public_state()
  if suffix=='':
   page=Path(__file__).with_name('portrait-pack-lab.html').read_text(encoding='utf-8')
   page=page.replace('__STATE_URL__',PREFIX+'state').replace("'/media/'",repr(PREFIX+'media/'))
   review=Path(__file__).with_name('portrait-review-ui.js').read_text(encoding='utf-8').replace('__REVIEW_URL__',PREFIX+'review')
   page=page.replace('</html>','<script>'+review+'</script></html>')
   page=page.replace('Private connection to your 96 GB GPU.','Live demonstration on an RTX PRO 6000 Blackwell 96 GB GPU.').replace('Private GPU','GPU')
   a=page.index('<footer>');b=page.index('</footer>',a)+len('</footer>')
   page=page[:a]+'<footer>Live research demonstration · Preview-resolution artwork · Identity, anatomy and print quality remain under evaluation.</footer>'+page[b:]
   data=page.encode();kind='text/html; charset=utf-8'
  elif suffix=='state':data=json.dumps(state).encode();kind='application/json'
  elif suffix.startswith('media/'):
   name=urllib.parse.unquote(suffix[6:]);allowed={r.get(k) for r in state['rows'] for k in ('input','prepared','reference','output','thumbnail','preview','baseline_output','repair_mask','repair_design')}
   allowed.update(d.get(k) for d in state['input_catalog']['dogs'] for k in MEDIA_FIELDS)
   if Path(name).name!=name or name not in allowed or not (M/name).is_file():self.send_error(404);return
   data=(M/name).read_bytes();kind='image/png' if name.endswith('.png') else 'image/jpeg'
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
  self.send_header('Cache-Control','private, max-age=3600' if suffix.startswith('media/') and '-preview.' not in suffix else 'no-store')
  self.send_header('X-Robots-Tag','noindex, nofollow, noarchive');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'; frame-ancestors 'none'");self.end_headers();self.wfile.write(data)
 def log_message(self,*args):pass
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',int(os.environ.get('REVIEW_PORT','18300'))),Handler).serve_forever()
