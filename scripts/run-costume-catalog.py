"""Persistent per-costume LLM refinement queue; private jobs, sanitized reports.

Training failures are revisited in later rounds. Failed frozen holdout checks are
retained for inspection, never fed to the planner or silently rerolled.
"""
import argparse
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
import statistics
import time
from pathlib import Path
import requests
from portrait_reviews import ROOT,digest
from portrait_autorefine import DIMENSIONS,signature
from portrait_llm_planner import request as request_plan,atomic


def load_module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


runner=load_module('catalog_refiner','run-portrait-autorefine.py')
exporter=load_module('catalog_exporter','export-accepted-workflow.py')


def training_history(state):
    result=[]
    for a in state.get('attempts',[])[-4:]:
        result.append({'recipe':{k:v for k,v in a['recipe'].items() if k not in ('diagnosis','instruction')},
            'assessments':[{k:s[k] for k in (*DIMENSIONS,'dog_id','reason','defects','confidence') if k in s} for s in a['assessments']]})
    return result


class Catalog:
    def __init__(self,repo,version,hours,recipes):
        self.repo=repo;self.version=version;self.recipes=recipes
        self.index=json.loads((repo/'workflows/portraits/index.json').read_text())
        if len(self.index)!=725 or len({r['id'] for r in self.index})!=725:raise ValueError('Expected the verified 725-reference catalog')
        self.home=ROOT/'catalog-refinement'/version;self.home.mkdir(parents=True,exist_ok=True)
        self.path=self.home/'queue.json'
        fingerprint=signature({'index':self.index,'dogs':digest(ROOT/'selected-dogs-v3.json'),'recipes':recipes,'hours':hours,
            'code':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
        if self.path.exists():
            self.state=json.loads(self.path.read_text())
            if self.state['fingerprint']!=fingerprint:raise ValueError('Catalog inputs/code changed; use a new queue version')
        else:self.state=dict(version=version,fingerprint=fingerprint,started_at=time.time(),max_hours=hours,status='Ready',items={
            r['id']:dict(status='pending',round=0,generations=0,errors=0) for r in self.index})
        self.by_id={r['id']:r for r in self.index};self.save()

    def save(self):
        self.state['updated_at']=time.time();atomic(self.path,self.state)
        values=list(self.state['items'].values())
        counts={s:sum(v['status']==s for v in values) for s in ('pending','in_progress','retry_pending','accepted','blocked')}
        atomic(ROOT/'catalog-public-status.json',dict(version=self.version,status=self.state['status'],total=725,counts=counts,
            current_reference=self.state.get('current_reference'),updated_at=self.state['updated_at'],
            note='AI-driven workflow experiments, not weight training. Retries and failed checks are retained.'))

    def stage_reference(self,ref):
        name='catalog-'+ref['id']+'-reference.png';path=ROOT/'media'/name
        if not path.exists():
            reply=requests.get(ref['reference_url'],timeout=180);reply.raise_for_status()
            if hashlib.sha256(reply.content).hexdigest()!=ref['reference_sha256']:raise ValueError('Reference download hash differs')
            temporary=path.with_suffix('.download');temporary.write_bytes(reply.content);temporary.replace(path)
        if digest(path)!=ref['reference_sha256']:raise ValueError('Staged reference changed')
        row_id='catalog-reference-'+ref['id'];rows_path=ROOT/'catalog-references.json'
        rows=json.loads(rows_path.read_text())['rows'] if rows_path.exists() else []
        if not any(r['id']==row_id for r in rows):
            _,tune=self.tuning_dogs()
            rows.append(dict(id=row_id,dog_id=tune[0],reference=name,template=ref['name'],pack=ref['collection'],category=ref['category'],status='Reference ready'))
            atomic(rows_path,{'rows':rows})
        jobs=ROOT/'catalog-jobs';jobs.mkdir(exist_ok=True)
        graph_path=jobs/(row_id+'.json')
        if not graph_path.exists():
            graph=json.loads((self.repo/'workflows/flux-klein-4b-base-api.json').read_text())
            graph['92:87']['inputs']['text']='';atomic(graph_path,graph)
        return name,row_id

    def tuning_dogs(self):
        dogs={d['id']:d for d in json.loads((ROOT/'selected-dogs-v3.json').read_text())['dogs']}
        train=runner.dog_splits(list(dogs.values()))['train']
        return dogs,runner.choose_tuning_dogs(dogs,train,train[0])

    def report(self,ref,item,state=None,accepted=None):
        folder=self.repo/ref['workflow_folder'];status_path=folder/'status.json';status=json.loads(status_path.read_text())
        if status.get('customer_identity_transfer_validated') and not accepted:return
        status.update(status='provisional' if item['status']=='retry_pending' else item['status'],
            customer_identity_transfer_validated=bool(accepted),last_run_version=item.get('run'),
            last_updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            accepted_workflow='workflow.json' if accepted else None,latest_provisional_workflow=None,
            ai_estimate_only=True,rounds_started=item['round'],generation_candidates=item['generations'])
        if accepted:
            target=folder/'workflow.json'
            if target.exists() and json.loads(target.read_text())!=accepted:raise ValueError('Existing accepted workflow differs')
            if not target.exists():atomic(target,accepted)
        atomic(status_path,status)
        lines=[f"# {ref['name']} — refinement report",'',f"Status: **{status['status']}**. Updated {status['last_updated_utc']}.",'',
            f"Queue `{self.version}`; run `{item.get('run','not-started')}`; {item['round']} rounds started; {item['generations']} generated candidates.",'',
            'The resident Qwen3-VL-32B proposes bounded graph changes from reference images, original tuning pets, previous outputs and training-only critiques. The independent scoring prompt and weights remain fixed.',
            'Graph strategies: whole-subject inpainting or fresh subject latent with protected-background compositing. FLUX.2 Klein base 4B and SAM3.1 remain the generation/segmentation stack.','']
        if state:
            attempts=state.get('attempts',[])
            lines.extend(['| Generation in this round | Lowest face | Lowest fur | Lowest body | Lowest design | Strategy |','| --- | ---: | ---: | ---: | ---: | --- |'])
            for a in attempts:
                mins=[min(s[k] for s in a['assessments']) for k in DIMENSIONS]
                lines.append('| '+str(a['recipe']['version'])+' | '+' | '.join(map(str,mins))+' | '+a['recipe'].get('strategy','inpaint')+' |')
            lines+=['',f"Frozen validation assessments: {len(state.get('validation',[]))}. Final-test assessments: {len(state.get('test',[]))}.",'']
        lines+=['Acceptance requires every face/fur/body/design score >=9, high confidence, no major defects, and successful frozen cross-dog checks. AI scores are estimates, not proof of perfect identity or print quality.',
                'Exact customer images, masks, graph attempts, critiques and provisional recipes remain in the private runtime. No provisional graph has been published as an accepted workflow.',
                'Training failures return to the queue. Failed held-out checks are not supplied as tuning feedback. Technical failures retain their native job IDs for safe resume.']
        (folder/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    def process(self,ref):
        item=self.state['items'][ref['id']];reference,source_row=self.stage_reference(ref)
        if not item.get('run') or item['status']=='retry_pending':
            item['round']+=1;item['run']=f"{self.version}-{ref['id']}-round-{item['round']}"
            item['offset']=item.get('offset',0)+item.get('last_recipes',0)
        item['status']='in_progress';self.state['current_reference']=ref['name'];self.save();self.report(ref,item)
        run=item['run'];plan_path=self.home/(run+'-plan.json')
        if not plan_path.exists():
            dogs,tune=self.tuning_dogs()
            images=[{'file':reference,'label':'Target costume artwork'}]
            images.extend({'file':dogs[d]['input'],'label':'Original tuning dog '+d} for d in tune)
            proposal=request_plan(ROOT,run+'-initial',{'images':images,
                'context':{'reference':ref['name'],'earlier_training_experiments':item.get('training_history',[]),
                    'instruction':'Visually inspect this costume, including any unnatural body shape. Describe a pet-neutral, anatomically coherent adaptation; never copy the old animal identity.'}})
            if not proposal['single_subject']:
                item.update(status='blocked',block_reason='Reference needs a multi-subject workflow');self.save();self.report(ref,item);return
            plan=dict(version=run,dogs_manifest='selected-dogs-v3.json',use_llm_planner=True,validate_provisional=False,
                validate_all_dogs=True,max_attempts=self.recipes,patience=self.recipes,max_generations=100,max_hours=6,
                templates=[dict(id=ref['id'],reference_id=ref['id'],source_row=source_row,clothing=proposal['clothing'],
                    scene=proposal['scene'],require_clothing=proposal['require_clothing'],initial_proposal=proposal,
                    training_history=item.get('training_history',[]),generation_offset=item['offset'])])
            atomic(plan_path,plan)
        refiner=runner.Refiner(json.loads(plan_path.read_text()));refiner.execute_plan()
        state=refiner.state['templates'].get(ref['id'],{})
        if refiner.state['status']=='Needs attention' or not state.get('finished'):raise RuntimeError('Reference run needs inspection or more time')
        # Account by durable run ID so a crash during report publication cannot double counts.
        item.setdefault('run_generations',{})[run]=refiner.state['generations']
        item['generations']=sum(item['run_generations'].values());item['last_recipes']=len(state.get('attempts',[]))
        item['training_history']=training_history(state)
        accepted=None
        if state['status']=='AI target met across dogs':
            accepted=exporter.sanitized(json.loads((refiner.home/'accepted'/(ref['id']+'.json')).read_text()))
            item['status']='accepted'
        elif state.get('validation') or state.get('test'):
            item['status']='blocked';item['block_reason']='Frozen cross-dog checks did not pass; no holdout-guided retry'
        else:item['status']='retry_pending'
        item['errors']=0;self.report(ref,item,state,accepted);self.save()

    def run(self):
        self.state['status']='Running';self.save()
        while time.time()-self.state['started_at']<self.state['max_hours']*3600:
            if (self.home/'STOP').exists():self.state['status']='Stopped by operator';break
            candidates=[(ref,self.state['items'][ref['id']]) for ref in self.index if self.state['items'][ref['id']]['status'] not in ('accepted','blocked')]
            if not candidates:self.state['status']='Queue exhausted; inspect blocked references';break
            # Up to three training rounds per costume, then let the next costume run.
            ref,item=min(candidates,key=lambda pair:((max(0,pair[1]['round']-1) if pair[1]['status']=='in_progress' else pair[1]['round'])//3,
                self.index.index(pair[0])))
            try:
                with (ROOT/'auto-refinement.lock').open('a') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);self.process(ref)
            except BlockingIOError:
                self.state['status']='Waiting for existing refinement worker';self.save();time.sleep(10)
            except Exception as error:
                item['errors']+=1;item['last_error_type']=type(error).__name__
                if item['errors']>=3:item['status']='blocked'
                self.save();self.report(ref,item)
                print('Catalog error',ref['id'],type(error).__name__,str(error)[:180],flush=True)
                time.sleep(10)
        else:self.state['status']='Time window reached; queue retained for resume'
        self.save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);p.add_argument('--version',default='catalog-llm-v3')
    p.add_argument('--hours',type=float,default=48);p.add_argument('--recipes',type=int,default=4);a=p.parse_args()
    if not 1<=a.recipes<=12 or not 0<a.hours<=48:raise SystemExit('Invalid resource window')
    with (ROOT/'catalog-refinement.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);Catalog(a.repo.resolve(),a.version,a.hours,a.recipes).run()
