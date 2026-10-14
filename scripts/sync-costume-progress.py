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
    for name in ('status.json','REPORT.md')+ (('workflow.json',) if status.get('customer_identity_transfer_validated') or status.get('known_roster_identity_transfer_validated') or (status.get('owner_approved') and status.get('accepted_workflow')=='workflow.json') else ()):
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
            historical=data.get('status')=='AI target met across dogs' and data.get('format')=='consistent-pet-api-recipe-v1'
            roster=data.get('status')=='locked_on_development_roster' and data.get('format')=='consistent-pet-roster-recipe-v1'
            qualified=data.get('status')=='locked_on_qualified_roster' and data.get('format')=='consistent-pet-roster-recipe-v2'
            majority=data.get('status')=='locked_on_qualified_roster' and data.get('format')=='consistent-pet-roster-recipe-v3'
            eights=data.get('status')=='locked_on_qualified_roster' and data.get('format')=='consistent-pet-roster-recipe-v4'
            if eights and (data.get('thresholds')!=dict(identity=8,fur=8,body=7,template=8) or data.get('evaluation',{}).get('input_minimum')!=7):raise ValueError('Wrong eight-point thresholds')
            if (qualified or majority) and (data.get('thresholds')!=dict(identity=9,fur=9,body=7,template=9) or data.get('evaluation',{}).get('input_minimum')!=7):raise ValueError('Wrong quality thresholds')
            owner=data.get('format')=='consistent-pet-owner-approved-recipe-v1' and data.get('status')=='owner_approved' and data.get('acceptance_basis')=='explicit_owner_override' and data.get('ai_acceptance_claim') is False
            if not (historical or roster or qualified or majority or eights or owner):raise ValueError('Unaccepted workflow export')
            if roster or qualified or majority or eights:
                e=data.get('evaluation',{})
                if not (e.get('roster_entries',0)>=7 and (e.get('roster_entries')==e.get('passing_entries') if not (majority or eights) else (type(e.get('roster_entries')) is int and type(e.get('passing_entries')) is int and e.get('required_pass_percent')==85 and e.get('required_passing_entries')==(85*e['roster_entries']+99)//100 and e['required_passing_entries']<=e['passing_entries']<=e.get('checked_entries',0)==e['roster_entries'])) and e.get('same_recipe_for_all') is True and e.get('unseen_dog_validation') is False):raise ValueError('Incomplete roster export')
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
    if getattr(args,'hf_dataset',None):
        if not args.publish:raise ValueError('HF mirroring requires published source')
        import importlib.util
        spec=importlib.util.spec_from_file_location('hf_mirror',Path(__file__).with_name('mirror-workflows-hf.py'));mirror=importlib.util.module_from_spec(spec);spec.loader.exec_module(mirror)
        revision=mirror.mirror(repo,args.hf_dataset)
        print(json.dumps(dict(hugging_face_revision=revision)),flush=True)
    print(json.dumps(dict(changed_files=len(changed),published=bool(changed and args.publish))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--identity',type=Path,required=True)
    p.add_argument('--host',required=True);p.add_argument('--port',type=int,default=22);p.add_argument('--remote-repo',default='/workspace/consistent-pet')
    p.add_argument('--hf-dataset');p.add_argument('--publish',action='store_true');p.add_argument('--watch-hours',type=float,default=0);a=p.parse_args()
    if not 0<=a.watch_hours<=48:raise SystemExit('Watch window must be 0..48 hours')
    deadline=time.time()+a.watch_hours*3600
    while True:
        try:run(a)
        except Exception as error:
            if not a.watch_hours:raise
            print(json.dumps(dict(sync_error=type(error).__name__,message=str(error)[:200])),flush=True)
        if time.time()>=deadline:break
        time.sleep(min(300,max(0,deadline-time.time())))
