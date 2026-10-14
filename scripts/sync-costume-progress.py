"""Pull only sanitized per-costume reports from an operator's GPU checkout.

Optional --publish commits only those report files and pushes the existing main
branch. SSH identity/host are private command-line configuration, never stored in Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import time

COLLECT='''import json,sys
from pathlib import Path
repo=Path(sys.argv[1]);files={}
for ref in json.loads((repo/'workflows/portraits/index.json').read_text()):
    folder=repo/ref['workflow_folder']
    if not (folder/'REPORT.md').exists():continue
    status=json.loads((folder/'status.json').read_text())
    for name in ('status.json','REPORT.md')+ (('workflow.json',) if status.get('customer_identity_transfer_validated') else ()):
        files[ref['workflow_folder']+'/'+name]=(folder/name).read_text()
print(json.dumps(files))
'''


def run(args):
    repo=args.repo.resolve()
    def git(*values):return subprocess.check_output(['git',*values],cwd=repo,text=True).strip()
    if git('branch','--show-current')!='main':raise ValueError('Progress publisher requires main')
    if 'bensblueprints/consistent-pet' not in git('remote','get-url','origin'):raise ValueError('Unexpected publishing destination')
    index=json.loads((repo/'workflows/portraits/index.json').read_text())
    allowed={ref['workflow_folder']+'/'+name for ref in index for name in ('status.json','REPORT.md','workflow.json')}
    ssh=['ssh','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=20','-i',str(args.identity),'-p',str(args.port),args.host,
         '/venv/main/bin/python - '+shlex.quote(args.remote_repo)]
    reply=subprocess.run(ssh,input=COLLECT,text=True,capture_output=True,timeout=120,check=True)
    files=json.loads(reply.stdout)
    changed=[]
    for relative,text in files.items():
        if relative not in allowed or not isinstance(text,str):raise ValueError('Unexpected report path or type')
        if any(secret in text for secret in ('trycloudflare.com','root@','inputs-v3-','/workspace/fpg-validation')):
            raise ValueError('Private runtime evidence in public report')
        path=repo/relative
        if path.exists() and path.read_text(encoding='utf-8')==text:continue
        if git('status','--porcelain','--',relative):raise ValueError('Local report has uncommitted changes; inspect before syncing')
        if path.name=='workflow.json':
            data=json.loads(text)
            if data.get('status')!='AI target met across dogs' or data.get('format')!='consistent-pet-api-recipe-v1':raise ValueError('Unaccepted workflow export')
            unsigned={k:v for k,v in data.items() if k!='sha256'}
            from portrait_autorefine import signature
            if data['sha256']!=signature(unsigned):raise ValueError('Export checksum differs')
            if path.exists():raise ValueError('Never replace an existing accepted workflow')
            for node in data['graph'].values():
                if node['class_type'] in ('LoadImage','LoadImageMask'):
                    image=node['inputs']['image']
                    if not (image.startswith('__') and image.endswith('__')):raise ValueError('Export contains a bound image')
        changed.append((relative,text))
    for relative,text in changed:(repo/relative).write_text(text,encoding='utf-8',newline='\n')
    if changed and args.publish:
        paths=[name for name,_ in changed]
        git('add','--',*paths)
        git('commit','--only','-m','Record per-costume GPU refinement progress','--',*paths)
        git('push','origin','HEAD:main')
    print(json.dumps(dict(changed_files=len(changed),published=bool(changed and args.publish))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--identity',type=Path,required=True)
    p.add_argument('--host',required=True);p.add_argument('--port',type=int,default=22);p.add_argument('--remote-repo',default='/workspace/consistent-pet')
    p.add_argument('--publish',action='store_true');p.add_argument('--watch-hours',type=float,default=0);a=p.parse_args()
    if not 0<=a.watch_hours<=48:raise SystemExit('Watch window must be 0..48 hours')
    deadline=time.time()+a.watch_hours*3600
    while True:
        run(a)
        if time.time()>=deadline:break
        time.sleep(min(300,max(0,deadline-time.time())))
