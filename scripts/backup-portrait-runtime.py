"""Incremental private recovery archives; never upload these archives publicly."""
import argparse,json,subprocess,time,hashlib,shlex
from pathlib import Path

REMOTE=r'''
import sys,time,tarfile,sqlite3,hashlib,json,os
from pathlib import Path
since=float(sys.argv[1]); stamp=time.time(); root=Path('/workspace/fpg-validation')
archive=Path('/workspace/fpg-private-recovery.tar.gz'); dbcopy=Path('/workspace/fpg-private-recovery-reviews.sqlite3')
with sqlite3.connect(root/'reviews.sqlite3') as source,sqlite3.connect(dbcopy) as target:source.backup(target)
allowed={'.json','.png','.jpg','.jpeg','.webp','.sqlite3','.py','.js','.html','.md'}
with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
 for folder in [root,*Path('/workspace').glob('fpg-*-runner-v*'),Path('/workspace/fpg-benchmark')]:
  for path in folder.rglob('*'):
   if not path.is_file() or path.is_symlink() or path.suffix.lower() not in allowed:continue
   if any(word in path.name.lower() for word in ('token','secret','credential')):continue
   if path.name=='reviews.sqlite3' or '__pycache__' in path.parts:continue
   if folder==root and path.stat().st_mtime<since-2:continue
   tar.add(path,arcname=str(path.relative_to('/workspace')),recursive=False)
 tar.add(dbcopy,arcname='fpg-validation/reviews.sqlite3')
 # Keep only the relevant service configuration; no tunnel credentials.
 for name in ('fpg-autorefine.conf','fpg-vision-judge.conf'):
  p=Path('/etc/supervisor/conf.d')/name
  if p.exists():tar.add(p,arcname='service-config/'+name)
with archive.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
print(json.dumps(dict(remote_time=stamp,sha256=sha,bytes=archive.stat().st_size)))
'''

def run(a):
    root=a.destination.resolve();root.mkdir(parents=True,exist_ok=True)
    state=root/'checkpoint.json';prior=json.loads(state.read_text()) if state.exists() else {}
    ssh=['ssh','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=20','-i',str(a.identity),'-p',str(a.port),a.host]
    reply=subprocess.run(ssh+['/venv/main/bin/python - '+str(prior.get('remote_time',0))],input=REMOTE,text=True,capture_output=True,check=True,timeout=600)
    result=json.loads(reply.stdout);name=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime(result['remote_time']))+'.tar.gz';target=root/(name+'.partial')
    with target.open('wb') as stream:
        subprocess.run(ssh+['cat /workspace/fpg-private-recovery.tar.gz'],stdout=stream,check=True,timeout=1800)
    with target.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    if sha!=result['sha256']:raise ValueError('Recovery archive checksum mismatch')
    target.rename(root/name);result['archive']=name
    manifest=root/(name+'.json');manifest.write_text(json.dumps(result,indent=2))
    temp=state.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2));temp.replace(state)
    print(json.dumps(dict(backup=name,bytes=result['bytes'],verified=True)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);p.add_argument('--identity',type=Path,required=True)
    p.add_argument('--host',required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--watch-hours',type=float,default=0);a=p.parse_args()
    deadline=time.time()+a.watch_hours*3600
    while True:
        try:run(a)
        except Exception as error:
            if not a.watch_hours:raise
            print(json.dumps(dict(backup_error=type(error).__name__)),flush=True)
        if time.time()>=deadline:break
        time.sleep(min(300,max(0,deadline-time.time())))
