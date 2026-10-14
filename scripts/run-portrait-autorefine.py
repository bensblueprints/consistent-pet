"""Local generate -> score -> revise -> freeze -> cross-dog validation.

Only --run submits work. Saves every attempt separately in the existing studio.
No paid API, reviewer weight changes, or edits to the original batch. Resume uses
saved native job UUIDs; ambiguous submissions stop rather than replaying.
"""
import argparse
import copy
import fcntl
import json
import os
import time
import uuid
from pathlib import Path

import numpy as np
import requests
from PIL import Image,ImageFilter
from portrait_reviews import ROOT,digest,attach
from portrait_body_repair import segmentation_graph,make_masks,neutral_reference,repair_graph
from portrait_benchmark_progress import ComfyProgress
from portrait_autorefine import TARGET,signature,dog_splits,meets_target,result_rank,next_recipe,seed_for,validate_plan,freeze_recipe,tuning_finished,dog_instruction,apply_recipe,choose_tuning_dogs
from portrait_fur_body_rubric import RUBRIC
from portrait_llm_planner import request as request_plan,recipe as llm_recipe

M=ROOT/'media';I=Path(os.environ.get('COMFY_INPUT_DIR','/workspace/ComfyUI/input'));API=os.environ.get('COMFY_API','http://127.0.0.1:18188').rstrip('/')


def atomic(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));temp.replace(path)


class BudgetReached(Exception):pass


class Refiner:
    def __init__(self,plan):
        self.plan=validate_plan(plan);self.run=plan['version'];self.home=ROOT/'auto-refinement'/self.run
        self.home.mkdir(parents=True,exist_ok=True);self.jobs=self.home/'jobs';self.jobs.mkdir(exist_ok=True)
        self.state_path=self.home/'state.json'
        self.dogs={d['id']:d for d in json.loads((ROOT/plan.get('dogs_manifest','selected-dogs.json')).read_text())['dogs']}
        self.splits=dog_splits(list(self.dogs.values()))
        sources=[r for f in ('dog-library-batch.json','dog-batch.json','catalog-references.json') if (ROOT/f).exists() for r in json.loads((ROOT/f).read_text())['rows']]
        self.sources={r['id']:r for r in sources}
        self.fingerprint=signature({'plan':plan,'dogs':{d['id']:{**{k:d[k] for k in ('source_sha256','input','crop')},'input_sha256':digest(M/d['input']),'crop_sha256':digest(M/d['crop'])} for d in self.dogs.values()},
            'cohort':self.dogs,'judge_model':digest(ROOT/'judge32-model.json'),
            'code':{name:digest(Path(__file__).with_name(name)) for name in ('run-portrait-autorefine.py','portrait_autorefine.py','portrait_body_repair.py','score-portrait-outputs.py','portrait_fur_body_rubric.py','portrait_input_registry.py','portrait_llm_planner.py')}})
        if self.state_path.exists():
            self.state=json.loads(self.state_path.read_text())
            if self.state['fingerprint']!=self.fingerprint:raise ValueError('Changed recipe/code/inputs: use a new run version')
        else:self.state=dict(run=self.run,fingerprint=self.fingerprint,status='Ready',started_at=time.time(),generations=0,templates={},rows={})
        self.save()

    def save(self):
        self.state['updated_at']=time.time();atomic(self.state_path,self.state)
        summary={k:self.state.get(k) for k in ('run','status','generations','current_template','phase','updated_at')}
        summary.update(target=f'At least {TARGET}/10 in face, fur, body and design',max_generations=self.plan['max_generations'],
                       dogs=len(self.dogs),templates=len(self.plan['templates']),finished=sum(bool(t.get('finished')) for t in self.state['templates'].values()),
                       passed=sum(t.get('status')=='AI target met across dogs' for t in self.state['templates'].values()))
        atomic(ROOT/'auto-refine-status.json',summary)

    def budget(self):
        if self.state['generations']>=self.plan['max_generations'] or time.time()-self.state['started_at']>=self.plan['max_hours']*3600:
            raise BudgetReached('Configured generation/time limit reached; resume in a new evaluation version')
        if (self.home/'STOP').exists():raise BudgetReached('Stopped by operator marker')

    def publish(self,row):
        # Merge one row under the shared lock; never overwrite concurrent revisions.
        with (ROOT/'dog-revisions.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=json.loads((ROOT/'dog-revisions.json').read_text()) if (ROOT/'dog-revisions.json').exists() else {'rows':[]}
            state['rows']=[r for r in state['rows'] if r['id']!=row['id']]+[row]
            state['updated_at']=time.time();atomic(ROOT/'dog-revisions.json',state)
        self.state['rows'][row['id']]=row;self.save()

    def upload(self,name):
        if Path(name).name!=name:raise ValueError('Media basename required')
        target=I/name
        if target.exists() and digest(target)!=digest(M/name):raise ValueError('Input file conflict')
        if not target.exists():target.write_bytes((M/name).read_bytes())

    def execute(self,key,graph,row=None):
        record_path=self.jobs/(key+'.json')
        fresh=not record_path.exists()
        if fresh:
            self.budget()
            record=dict(prompt_id=str(uuid.uuid5(uuid.NAMESPACE_URL,self.run+'/'+key)),graph=graph,graph_sha256=signature(graph),started_at=time.time())
            atomic(record_path,record)
        else:
            record=json.loads(record_path.read_text())
            if signature(graph)!=record['graph_sha256']:raise ValueError('Saved graph differs')
            if record.get('history'):
                if record['history']['status']['status_str']!='success':raise RuntimeError('Saved native job failed')
                return record['history']
        if row:
            row.update(status='Rendering',prompt_id=record['prompt_id'],started=record['started_at']);self.publish(row)
        monitor=ComfyProgress(API,row['id'] if row else key,ROOT);monitor.start()
        try:
            if fresh:
                if row:
                    # Persist render reservation before sending: crashes can only overcount, never overspend.
                    self.state['generations']+=1;self.save()
                try:
                    reply=requests.post(API+'/prompt',json={'prompt':graph,'prompt_id':record['prompt_id'],'client_id':key},timeout=45)
                    reply.raise_for_status()
                    if reply.json()['prompt_id']!=record['prompt_id']:raise ValueError('Native job ID changed')
                except requests.RequestException:pass # Reconcile the saved ID below.
            missing=0;deadline=time.time()+2400
            while time.time()<deadline:
                reply=requests.get(API+'/history/'+record['prompt_id'],timeout=30);reply.raise_for_status()
                history=reply.json().get(record['prompt_id'])
                if history:
                    record['history']=history;atomic(record_path,record)
                    if history['status']['status_str']!='success':raise RuntimeError('Native job failed; inspect private history')
                    return history
                q=requests.get(API+'/queue',timeout=30);q.raise_for_status();q=q.json()
                queued={j[1] for k in ('queue_running','queue_pending') for j in q[k]}
                missing=0 if record['prompt_id'] in queued else missing+1
                if missing>=3:raise RuntimeError('Ambiguous native job; stopped without duplicate submission')
                time.sleep(1)
            raise TimeoutError('Native job still pending; safely resume the saved ID')
        finally:monitor.close()

    def fetch(self,history,node,path):
        reply=requests.get(API+'/view',params=history['outputs'][node]['images'][0],timeout=90);reply.raise_for_status()
        temp=path.with_suffix('.tmp');temp.write_bytes(reply.content);temp.replace(path)

    def prepare(self,t,state):
        source=self.sources[t['source_row']]
        graph_path=ROOT/('catalog-jobs' if source['id'].startswith('catalog-reference-') else 'dog-library-jobs' if source['id'].startswith('dogs10-full-library') else 'dog-jobs')/(source['id']+'.json')
        if not graph_path.exists():raise ValueError('Template needs a saved native baseline graph')
        graph=json.loads(graph_path.read_text());w=graph['92:115']['inputs']['width'];h=graph['92:115']['inputs']['height']
        source_hashes={'reference':digest(M/source['reference']),'graph':digest(graph_path)}
        if state.get('source_hashes') and source_hashes!=state['source_hashes']:raise ValueError('Template source changed')
        state['source_hashes']=source_hashes
        prefix=self.run+'-'+t['id'];layout=prefix+'-layout.png'
        if not (M/layout).exists():Image.open(M/source['reference']).convert('RGB').resize((w,h),Image.Resampling.LANCZOS).save(M/layout)
        self.upload(layout)
        if not state.get('assets'):
            g=segmentation_graph(layout,layout,t['clothing'],'fpg-private-validation/'+prefix+'-segment')
            history=self.execute(prefix+'-segment',g)
            paths=[]
            for k in ('subject','animal','clothes','subject-clothes'):
                p=self.jobs/(prefix+'-'+k+'.png');self.fetch(history,k+'-save',p);paths.append(p)
            mask,erase,metrics=make_masks(*(Image.open(p) for p in paths[:3]),(w,h),subject_clothes=Image.open(paths[3]),require_clothing=t.get('require_clothing',True))
            design=prefix+'-design.png';maskname=prefix+'-mask.png'
            mask.save(M/maskname);neutral_reference(Image.open(M/layout),erase).save(M/design)
            state.update(assets=dict(layout=layout,mask=maskname,design=design),mask_metrics=metrics,
                         asset_hashes={name:digest(M/name) for name in (layout,maskname,design)})
            self.save()
        for name,sha in state['asset_hashes'].items():
            if digest(M/name)!=sha:raise ValueError('Prepared template asset changed')
            self.upload(name)
        return source,graph

    def render(self,t,state,source,base,recipe,dog_id,stage):
        key=f"{self.run}-{t['id']}-r{recipe['version']}-{stage}-{dog_id}"
        row=self.state['rows'].get(key)
        if row and row.get('output'):
            if digest(M/row['output'])!=row['output_sha256']:raise ValueError('Completed output changed')
            for name,sha in row['source_hashes'].items():
                if digest(M/name)!=sha:raise ValueError('Completed attempt source changed')
            return row
        dog=self.dogs[dog_id];assets=state['assets']
        for name in (dog['input'],dog['crop']):self.upload(name)
        mask_name=f"{self.run}-{t['id']}-mask-g{recipe['grow']}-f{recipe['feather']}.png"
        if not (M/mask_name).exists():
            prefix=self.run+'-'+t['id']
            paths=[self.jobs/(prefix+'-'+k+'.png') for k in ('subject','animal','clothes','subject-clothes')]
            mask,_,_=make_masks(*(Image.open(p) for p in paths[:3]),Image.open(M/assets['layout']).size,
                grow=recipe['grow'],feather=recipe['feather'],subject_clothes=Image.open(paths[3]),require_clothing=t.get('require_clothing',True))
            mask.save(M/mask_name)
        self.upload(mask_name)
        if not row:
            row={k:source[k] for k in ('pack','category','template','reference')}
            row.update(id=key,dog_id=dog_id,label=dog['label'],input=dog['input'],prepared=dog['input'],
                       identity_crop=dog['crop'],input_quality=dog.get('quality_tier'),input_quality_notes=dog.get('quality_notes'),
                       preparation='Intact original dog; no cutout loss',status='Queued',
                       mode=f'Automatic refinement · {stage} · recipe {recipe["version"]}',
                       auto_refine_version=self.run,auto_stage=stage,auto_attempt=recipe['version'],auto_target=TARGET,
                       reference_id=t.get('reference_id',t['id']),generation=t.get('generation_offset',0)+recipe['version'],
                       planner=recipe.get('planner','heuristic-v2'),strategy=recipe.get('strategy','inpaint'),
                       auto_changes=recipe.get('changes',[]),auto_rationale=recipe.get('rationale',''),
                       auto_corrections=[d['correction'] for d in recipe.get('diagnosis',[]) if stage=='tune' and d['dog_id']==dog_id],
                       workflow_id=t['id']+'-auto-r'+str(recipe['version']),workflow_sha256=signature(recipe),
                       repair_mask=mask_name,repair_design=assets['design'],baseline_output=source.get('output'),
                       baseline_label='Original baseline example (may use a different dog)',
                       review='Waiting for generation and independent AI assessment',index=len(self.state['rows']),
                       source_hashes={name:digest(M/name) for name in (dog['input'],dog['crop'],assets['design'],assets['layout'],mask_name)})
            self.publish(row)
        for name,sha in row['source_hashes'].items():
            if digest(M/name)!=sha:raise ValueError('Attempt input changed')
        graph=repair_graph(base,original=dog['input'],face=dog['crop'],design=assets['design'],baseline=assets['layout'],mask=mask_name,
                           prefix='fpg-private-validation/'+key,identity='Original dog description: '+dog['label']+'. '+dog_instruction(recipe,dog_id,stage),
                           scene=t['scene'],seed=seed_for(self.plan.get('seed_namespace',self.run),t['id'],0 if self.plan.get('stable_seeds') else recipe['version'],dog_id))
        apply_recipe(graph,recipe)
        history=self.execute(key,graph,row);output=key+'.png';self.fetch(history,'9',M/output)
        im=Image.open(M/output).convert('RGB');prior=Image.open(M/assets['layout']).convert('RGB')
        if im.size!=prior.size:raise ValueError('Output dimensions differ')
        outside=np.asarray(Image.open(M/mask_name).convert('L'))==0
        if not outside.any():raise ValueError('Mask leaves no protected background')
        if np.abs(np.asarray(im,dtype='int16')-np.asarray(prior,dtype='int16'))[outside].max()>1:raise ValueError('Protected background changed')
        thumb=im.copy();thumb.thumbnail((720,900));thumb.save(M/(key+'-thumb.jpg'),quality=88)
        row.update(output=output,output_sha256=digest(M/output),thumbnail=key+'-thumb.jpg',status='Complete',finished_at=time.time(),seconds=round(time.time()-row['started'],1),
                   graph_sha256=signature(graph),review=f'Awaiting independent AI score; target at least {TARGET} in every dimension')
        self.publish(row);return row

    def score(self,row):
        deadline=time.time()+1800
        while time.time()<deadline:
            latest=attach([copy.deepcopy(row)])[0];ai=latest.get('ai_review')
            if ai and ai.get('rubric')==RUBRIC:
                return ai
            if latest.get('ai_status')=='Needs attention':raise RuntimeError('Reviewer failed this attempt')
            time.sleep(2)
        raise TimeoutError('Reviewer timeout; output retained for resume')

    def evaluate(self,t,state,source,base,recipe,dogs,stage):
        results=[]
        for dog in dogs:
            row=self.render(t,state,source,base,recipe,dog,stage)
            self.state.update(phase='Scoring '+stage,current_template=source['template']);self.save()
            ai={**self.score(row),'dog_id':dog};results.append(ai)
            row['review']='AI target met on this image' if meets_target(ai) else f"AI feedback: face {ai['identity']}, fur {ai['fur']}, body {ai['body']}, design {ai['template']}"
            self.publish(row)
        return results

    def template(self,t):
        state=self.state['templates'].setdefault(t['id'],{'attempts':[]})
        if state.get('finished'):return
        self.state.update(current_template=t['id'],phase='Preparing whole-animal mask');self.save()
        source,base=self.prepare(t,state)
        train=self.splits['train'];preferred=source['dog_id']
        tune=choose_tuning_dogs(self.dogs,train,preferred)
        tune_groups={self.dogs[d].get('identity_group',self.dogs[d].get('source_sha256',d)) for d in tune}
        remaining=[d for d in train if d not in tune and self.dogs[d].get('identity_group',self.dogs[d].get('source_sha256',d)) not in tune_groups]
        validation=self.splits['validation']+(remaining if self.plan.get('validate_all_dogs') else remaining[:1]);test=self.splits['test']
        state.update(tune_dogs=tune,validation_dogs=validation,test_dogs=test);self.save()
        if any(a.get('dog_id') not in tune for a in t.get('initial_feedback',[])):
            raise ValueError('Bootstrap feedback includes a non-tuning dog')
        while not tuning_finished(state['attempts'],self.plan['max_attempts'],self.plan['patience']):
            index=len(state['attempts'])
            previous=state['attempts'][-1]['assessments'] if state['attempts'] else t.get('initial_feedback',[])
            parent=state['attempts'][-1]['recipe'] if state['attempts'] else t.get('initial_recipe')
            if self.plan.get('use_llm_planner'):
                self.state['phase']='Local LLM designing generation '+str(index+1);self.save()
                if index==0 and t.get('initial_proposal'):proposal=t['initial_proposal']
                else:
                    images=[{'file':source['reference'],'label':'Costume and scene reference'}]
                    for dog in tune:
                        images.append({'file':self.dogs[dog]['input'],'label':'Original tuning dog '+dog})
                        prior_key=f"{self.run}-{t['id']}-r{index}-tune-{dog}"
                        prior_row=self.state['rows'].get(prior_key)
                        if prior_row and prior_row.get('output'):images.append({'file':prior_row['output'],'label':'Prior result for '+dog})
                    history=[{'recipe':{k:v for k,v in a['recipe'].items() if k not in ('diagnosis','instruction')},'assessments':a['assessments']} for a in state['attempts'][-4:]]
                    proposal=request_plan(ROOT,f"{self.run}-{t['id']}-planner-{index+1}",{'images':images,'context':{
                        'reference':source['template'],'clothing':t['clothing'],'scene':t['scene'],'training_history':history,
                        'earlier_training_experiments':t.get('training_history',[]),'rule':'Only training feedback is supplied; held-out reviews must never guide edits.'}})
                recipe=llm_recipe(proposal,index,previous,parent)
            else:recipe=next_recipe(index,previous,parent)
            assessments=self.evaluate(t,state,source,base,recipe,tune,'tune')
            state['attempts'].append(dict(recipe=recipe,assessments=assessments,rank=result_rank(assessments)))
            self.save()
        best=max(state['attempts'],key=lambda a:(all(meets_target(s) for s in a['assessments']),*a['rank']));recipe=best['recipe']
        first_id=f"{self.run}-{t['id']}-r{recipe['version']}-tune-{tune[0]}"
        graph=json.loads((self.jobs/(first_id+'.json')).read_text())['graph']
        assets={**state['asset_hashes'],**self.state['rows'][first_id]['source_hashes']}
        # Export only template assets; exclude the tuning dog's image/crop.
        assets={k:v for k,v in assets.items() if k not in (self.dogs[tune[0]]['input'],self.dogs[tune[0]]['crop'])}
        frozen=freeze_recipe(recipe,t,graph,assets,tune,validation,test)
        freeze_path=self.home/(t['id']+'-frozen.json')
        if freeze_path.exists() and json.loads(freeze_path.read_text())!=frozen:raise ValueError('Frozen recipe changed')
        if not freeze_path.exists():atomic(freeze_path,frozen)
        state.update(best_recipe=recipe,frozen_sha256=digest(freeze_path),status='Frozen; checking other dogs');self.save()
        if self.plan.get('validate_provisional') is False and not all(meets_target(a) for a in best['assessments']):
            state.update(finished=True,status='Best saved; target not met',test_status='Untouched: training target not met')
            atomic(self.home/(t['id']+'-report.json'),{**state,'ai_estimate_only':True,'production_enabled':False});self.save();return
        # Even a provisional best gets cross-dog diagnostics, never a false pass.
        checks=self.evaluate(t,state,source,base,recipe,validation,'validation')
        state['validation']=checks
        passed=all(meets_target(a) for a in best['assessments']+checks)
        if passed:
            state['test']=self.evaluate(t,state,source,base,recipe,test,'test')
            passed=all(meets_target(a) for a in state['test'])
        state.update(finished=True,status='AI target met across dogs' if passed else 'Best saved; target not met',
                     test_status='Evaluated once after validation passed' if 'test' in state else 'Untouched: earlier stages did not pass')
        if digest(freeze_path)!=state['frozen_sha256']:raise ValueError('Frozen recipe changed during validation')
        atomic(self.home/(t['id']+'-report.json'),{**state,'ai_estimate_only':True,'production_enabled':False})
        if passed:
            # Only a frozen recipe that passed every dog enters this registry.
            accepted=self.home/'accepted';accepted.mkdir(exist_ok=True)
            atomic(accepted/(t['id']+'.json'),dict(workflow=frozen,status=state['status'],
                scores={k:state[k] for k in ('validation','test')},tuning=best['assessments'],production_enabled=False))
        self.save()

    def execute_plan(self):
        self.state['status']='Running';self.save()
        try:
            for t in self.plan['templates']:self.template(t)
            self.state.update(status='Evaluation finished',phase='Saved workflows and cross-dog reports')
        except BudgetReached as error:
            self.state.update(status='Budget reached',phase=str(error))
        except Exception:
            self.state.update(status='Needs attention',phase='Check private log; all completed attempts retained');raise
        finally:self.save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--run',action='store_true');args=parser.parse_args()
    with (ROOT/'auto-refinement.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        refiner=Refiner(json.loads(args.plan.read_text()))
        if args.run:refiner.execute_plan()
        else:print(json.dumps({'run':refiner.run,'templates':len(refiner.plan['templates']),'splits':refiner.splits,'status':'Initialized; no generation submitted'}))
