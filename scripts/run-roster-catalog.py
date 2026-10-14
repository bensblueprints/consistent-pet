"""Owner-authorized sequential refinement on every submitted dog; no holdout claim."""
import argparse
import copy
import fcntl
import importlib.util
import json
import shutil
import time
from pathlib import Path
from portrait_reviews import ROOT,digest
from portrait_autorefine import DIMENSIONS,signature
from portrait_llm_planner import request as request_plan,recipe as make_recipe,atomic
from portrait_roster import POLICY,THRESHOLDS,AVERAGE_TARGET,round_average,required_passes,set_passes,meets_target,new_candidate,next_dog,passing,record_check,export_locked,recipe_hash,functional_recipe
from portrait_input_quality import eligible,read_scores,RUBRIC as INPUT_RUBRIC


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


catalog_module=module('catalog_base','run-costume-catalog.py')
core=catalog_module.runner


class RosterCatalog(catalog_module.Catalog):
    def save(self):
        super().save()
        path=ROOT/'catalog-public-status.json';public=json.loads(path.read_text())
        public.update(policy=POLICY,roster_total=self.state.get('roster_total',0),
                      checked_current_recipe=self.state.get('checked_current_recipe',0),current_dog=self.state.get('current_dog'),passed_current_recipe=self.state.get('passed_current_recipe',0),
                      required_average=AVERAGE_TARGET,current_recipe_average=self.state.get('current_recipe_average'),
                      note='A complete qualifying dog round must average >=8 across face, fur, body and design. Input >=7. Development checks, not unseen-dog validation.',
                      submission_deadline=self.state['started_at']+self.state['max_hours']*3600)
        atomic(path,public)

    def report(self,ref,item,development=None,accepted=None):
        if development is None and item.get('run'):
            saved=ROOT/'auto-refinement'/item['run']/'state.json'
            if saved.exists():development=json.loads(saved.read_text()).get('templates',{}).get(ref['id'],{}).get('roster_development')
        folder=self.repo/ref['workflow_folder'];path=folder/'status.json';status=json.loads(path.read_text())
        if accepted:
            target=folder/'workflow.json'
            if target.exists() and json.loads(target.read_text())!=accepted:raise ValueError('Existing locked export differs')
            if not target.exists():atomic(target,accepted)
        status.update(status='provisional' if item['status']=='retry_pending' else item['status'],
            last_run_version=item.get('run'),last_updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            customer_identity_transfer_validated=False,known_roster_identity_transfer_validated=bool(accepted),
            evaluation_policy=POLICY,unseen_dog_validation=False,ai_estimate_only=True,
            accepted_workflow='workflow.json' if accepted else None,latest_provisional_workflow=None,
            rounds_started=item['round'],generation_candidates=item.get('generations',0))
        candidates=(development or {}).get('candidates',[]);current=candidates[-1] if candidates else None
        status.update(roster_entries=len((development or {}).get('roster',[])),
                      passing_current_recipe=len(passing(current)) if current else 0,required_average=AVERAGE_TARGET,current_recipe_average=round_average(current) if current else None,
                      candidate_revisions=len(candidates),input_minimum=7,output_thresholds=THRESHOLDS,
                      excluded_input_entries=(development or {}).get('excluded_input_entries',0))
        atomic(path,status)
        lines=[f"# {ref['name']} — development-roster report",'',f"Status: **{status['status']}**. Updated {status['last_updated_utc']}.",'',
            f"{status['passing_current_recipe']} / {status['roster_entries']} qualifying input records pass the current shared recipe. {status['excluded_input_entries']} source photos excluded by the input-quality gate. {len(candidates)} candidate recipes; {item.get('generations',0)} renders.",'',
            'The independent output critic stays fixed. Acceptance: original input >=7; complete round arithmetic mean >=8 across all four scores for every qualifying dog. Individual dimension minima and the 85% pass fraction do not gate this policy.',
            'Each successful dog check is checkpointed privately. A recipe change invalidates earlier passes until those dogs are checked again. One exact recipe must be checked on the full qualifying roster and average >=8 to lock this costume. Incomplete rounds cannot pass.','',
            'All submitted photos are development data under the owner-requested policy. Historical holdout runs remain immutable; this new result is not independent validation on unseen dogs. AI estimates do not establish universal or perfect performance.','',
            '| Candidate | Dogs checked | Dogs passing | Lowest body | Strategy | Pose policy |',
            '| --- | ---: | ---: | ---: | --- | --- |']
        for candidate in candidates[-20:]:
            checks=candidate['checks'];scores=[e['assessment']['body'] for e in checks.values()]
            recipe=candidate['recipe'];lines.append(f"| {recipe['version']} | {len(checks)} | {len(passing(candidate))} | {min(scores) if scores else 'pending'} | {recipe.get('strategy','inpaint')} | {recipe.get('pose_policy','reference')} |")
        lines+=['','Exact images, per-dog checkpoints, native job IDs, critiques and unsuccessful graphs remain private. Accepted exports are parameterized and omit customer identities and media paths.',
                'Difficult references remain provisional for another catalog pass; technical failures require inspection. The submission deadline does not become an acceptance shortcut.']
        temp=folder/'REPORT.tmp';temp.write_text('\n'.join(lines)+'\n',encoding='utf-8');temp.replace(folder/'REPORT.md')

    def progress(self,ref,item,refiner,development):
        item['generations']=refiner.state['generations'];candidate=development['candidates'][-1] if development['candidates'] else None
        self.state['roster_total']=len(development['roster'])
        self.state['passed_current_recipe']=len(passing(candidate)) if candidate else 0
        self.state['checked_current_recipe']=len(candidate['checks']) if candidate else 0
        self.state['current_recipe_average']=round_average(candidate) if candidate else None
        self.save();refiner.save();self.report(ref,item,development)

    def propose(self,ref,source,refiner,t,development,initial=False):
        candidates=development['candidates'];previous=candidates[-1] if candidates else None
        dog=next_dog(development) if previous else development['roster'][0]
        selected=[dog]
        if previous:
            # Show a previously successful dog too, so repairs must preserve it.
            earlier=next((d for c in reversed(candidates) for d in passing(c) if d!=dog),None)
            if earlier:selected.append(earlier)
        images=[dict(file=source['reference'],label='Costume reference')]
        for d in selected:
            images.append(dict(file=refiner.dogs[d]['input'],label='Original development dog '+d))
            evidence=next((c['checks'][d] for c in reversed(candidates) if d in c['checks']),None)
            if evidence:
                row=refiner.state['rows'][evidence['row_id']]
                images.append(dict(file=row['output'],label='Earlier output for '+d))
        history=[dict(recipe=functional_recipe(c['recipe']),checks=[{k:e['assessment'].get(k) for k in (*DIMENSIONS,'dog_id','confidence','reason','defects')} for e in c['checks'].values()]) for c in candidates[-4:]]
        for attempt in range(3):
            self.check_window()
            proposal=request_plan(ROOT,f"{refiner.run}-visit-{development['visit']}-candidate-{len(candidates)+1}-proposal-{attempt+1}",dict(images=images,context=dict(
                reference=ref['name'],scene=t['scene'],development_history=history,
                instruction='All shown dogs are development examples. Correct the failing dog without losing earlier successes. A complete shared-recipe round must average at least 8 across all qualifying dogs and all four score dimensions. Do not copy a specific dog color or anatomy into generic instructions. If steps or mask growth failed repeatedly, change pose policy, conditioning balance or latent strategy. Avoid prior identical recipes.',
                retry='An identical functional recipe is not a new experiment.' if attempt else '')))
            if not proposal['single_subject']:raise ValueError('Reference requires multi-subject handling')
            reviews=[e['assessment'] for e in previous['checks'].values()] if previous else []
            recipe=make_recipe(proposal,len(candidates),reviews,previous['recipe'] if previous else None)
            if not any(c['recipe_sha256']==recipe_hash(recipe) for c in candidates):return recipe
        raise RuntimeError('Planner repeated earlier functional recipes; evidence retained')

    def check_window(self):
        if (self.home/'STOP').exists() or time.time()>=self.state['started_at']+self.state['max_hours']*3600:
            raise core.BudgetReached('Submission window closed; checkpoints retained')

    def process(self,ref):
        self.check_window()
        item=self.state['items'][ref['id']];reference,source_row=self.stage_reference(ref)
        if item['status']!='in_progress':item['round']+=1
        item['run']=item.get('run') or self.version+'-'+ref['id']
        item['status']='in_progress';self.state.update(status='Running',current_reference=ref['name']);self.save()
        plan_path=self.home/(item['run']+'-plan.json')
        if not plan_path.exists():
            dogs,tune=self.tuning_dogs()
            proposal=request_plan(ROOT,item['run']+'-initial',dict(images=[dict(file=reference,label='Costume reference'),dict(file=dogs[tune[0]]['input'],label='First original dog')],
                context=dict(instruction='First experiment: no generated output has been inspected. Describe a pet-neutral costume scene and choose an initial workflow.')))
            if not proposal['single_subject']:raise ValueError('Reference requires multi-subject handling')
            previous_rows=json.loads((ROOT/'dog-revisions.json').read_text())['rows'] if (ROOT/'dog-revisions.json').exists() else []
            offset=max([r.get('generation',0) for r in previous_rows if r.get('reference_id')==ref['id']]+[0])
            plan=dict(version=item['run'],dogs_manifest='selected-dogs-v3.json',stable_seeds=True,seed_namespace='roster-seed-v1',
                max_attempts=12,patience=12,max_generations=5000,max_hours=48,
                evaluation_policy=POLICY,templates=[dict(id=ref['id'],reference_id=ref['id'],source_row=source_row,
                    clothing=proposal['clothing'],scene=proposal['scene'],require_clothing=proposal['require_clothing'],
                    initial_proposal=proposal,generation_offset=offset)])
            atomic(plan_path,plan)
        refiner=core.Refiner(json.loads(plan_path.read_text()));t=refiner.plan['templates'][0]
        original_budget=refiner.budget
        def budget():self.check_window();original_budget()
        refiner.budget=budget
        original_save=refiner.save
        def save():
            original_save()
            p=ROOT/'auto-refine-status.json';s=json.loads(p.read_text());s['target']='Complete-round average >=8/10; input >=7';s['dogs']=getattr(refiner,'qualified_count',len(refiner.dogs));atomic(p,s)
        refiner.save=save
        refiner.state.update(current_template=ref['name'],phase='Preparing costume workflow')
        template=refiner.state['templates'].setdefault(t['id'],{'attempts':[]});source,base=refiner.prepare(t,template)
        pinned=refiner.home/'input-quality-snapshot.json'
        if pinned.exists():quality=json.loads(pinned.read_text())
        else:
            scores=read_scores(ROOT);quality={}
            for dog,data in refiner.dogs.items():
                value=scores.get(data['input'],{})
                if value.get('input_sha256')!=digest(ROOT/'media'/data['input']) or value.get('rubric')!=INPUT_RUBRIC:raise ValueError('Input audit missing or stale')
                quality[dog]=value
            atomic(pinned,quality)
        quality_hash=digest(pinned)
        if refiner.state.get('input_quality_sha256',quality_hash)!=quality_hash:raise ValueError('Pinned input scores changed')
        refiner.state['input_quality_sha256']=quality_hash
        roster=sorted([d for d in refiner.dogs if eligible(quality[d])],key=lambda d:(refiner.dogs[d].get('quality_rank',100),d))
        if len(roster)<7:raise ValueError('Fewer than seven qualifying inputs; cannot validate a shared workflow')
        if t.get('dog_order'):
            if set(t['dog_order'])!=set(refiner.dogs) or len(t['dog_order'])!=len(refiner.dogs):raise ValueError('Invalid dog ordering')
            roster=[d for d in t['dog_order'] if d in roster]
        refiner.qualified_count=len(roster)
        development=template.setdefault('roster_development',dict(policy=POLICY,roster=roster,candidates=[],locked=False,input_quality=quality,excluded_input_entries=len(refiner.dogs)-len(roster)))
        if development['roster']!=roster:raise ValueError('Roster changed; use a new version')
        if development.get('visit')!=item['round']:
            development.update(visit=item['round'],visit_attempts={},focus_dog=None)
        if not development['candidates']:new_candidate(development,make_recipe(t['initial_proposal'],0,[]))
        while True:
            if (self.home/'STOP').exists() or time.time()>=self.state['started_at']+self.state['max_hours']*3600:break
            if shutil.disk_usage(ROOT).free<10*1024**3:raise RuntimeError('Runtime storage needs attention')
            candidate=development['candidates'][-1];dog=next_dog(development)
            if dog is None:
                if not set_passes(development):break
                first=candidate['checks'][roster[0]];graph=json.loads((refiner.jobs/(first['row_id']+'.json')).read_text())['graph']
                artifact=export_locked(development,t,graph)
                accepted=refiner.home/'accepted';accepted.mkdir(exist_ok=True);atomic(accepted/(t['id']+'.json'),artifact)
                development['locked']=True;item.update(status='accepted',errors=0)
                refiner.state.update(status='Roster workflow locked',phase=f"Complete round accepted: {round_average(candidate):.3f}/10 across {len(roster)} dogs");refiner.save()
                self.report(ref,item,development,artifact);self.save();return
            self.state['current_dog']=roster.index(dog)+1
            development['focus_dog']=dog
            if dog in candidate['checks']:
                # Failed check: request an actual new recipe, then recheck prior dogs.
                refiner.state.update(status='Running',phase='Complete round average below 8; LLM revising shared workflow');refiner.save()
                new_candidate(development,self.propose(ref,source,refiner,t,development));self.progress(ref,item,refiner,development);continue
            attempt=development['visit_attempts'].get(dog,0)+1
            refiner.state.update(status='Running',phase=f"Round sweep: {len(candidate['checks'])}/{len(roster)} scored, average {round(round_average(candidate),2) if candidate['checks'] else 'pending'}/10 (target 8). Rendering {refiner.dogs[dog]['label']} ({attempt}/6)");refiner.save()
            row=refiner.render(t,template,source,base,candidate['recipe'],dog,'roster')
            row.update(output_thresholds=THRESHOLDS,input_photo_score=quality[dog]['score'],acceptance_policy=POLICY)
            refiner.state['phase']='Scoring development dog '+str(roster.index(dog)+1);refiner.save()
            assessment={**refiner.score(row),'dog_id':dog};record_check(candidate,dog,assessment,row)
            row['review']='Pass checkpoint saved for this recipe' if meets_target(assessment) else 'Below target; finish the dog round before deciding whether to revise'
            # Idempotent: resume may find a completed native row that has not been checkpointed.
            if row['id'] not in development.setdefault('counted_rows',[]):
                development['visit_attempts'][dog]=attempt;development['counted_rows'].append(row['id'])
            refiner.publish(row)
            if meets_target(assessment):
                development['focus_dog']=None
                locks=refiner.home/'dog-checkpoints';locks.mkdir(exist_ok=True)
                path=locks/(signature(dog)[:12]+'-'+candidate['recipe_sha256'][:12]+'.json')
                if not path.exists():atomic(path,dict(recipe=candidate['recipe'],evidence=candidate['checks'][dog]))
            self.progress(ref,item,refiner,development)
        item.update(status='retry_pending',errors=0);self.progress(ref,item,refiner,development)

    def run(self):
        self.state['status']='Running';self.save()
        while time.time()<self.state['started_at']+self.state['max_hours']*3600:
            if (self.home/'STOP').exists():self.state['status']='Stopped by operator';break
            refs=[r for r in self.index if self.state['items'][r['id']]['status'] not in ('accepted','blocked')]
            if not refs:self.state['status']='All references processed; inspect any blocked items';break
            ref=min(refs,key=lambda r:(self.state['items'][r['id']]['round']-(self.state['items'][r['id']]['status']=='in_progress'),r['id']!=self.state.get('start_reference'),self.index.index(r)));item=self.state['items'][ref['id']]
            try:
                with (ROOT/'auto-refinement.lock').open('a') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);self.process(ref)
            except BlockingIOError:time.sleep(5)
            except core.BudgetReached:
                item['status']='retry_pending';self.state['status']='Submission window finished; checkpoints retained';self.save();break
            except Exception as error:
                item['errors']+=1;item['last_error_type']=type(error).__name__
                item['status']='blocked' if item['errors']>=3 else 'retry_pending'
                self.save();self.report(ref,item)
                print('Roster error',ref['id'],type(error).__name__,str(error)[:160],flush=True);time.sleep(10)
        else:self.state['status']='Submission window finished; checkpoints retained'
        self.save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--version',default='roster-v1')
    p.add_argument('--hours',type=float,default=48);p.add_argument('--attempts-per-dog',type=int,choices=[6],default=6);a=p.parse_args()
    if not 0<a.hours<=48:raise SystemExit('Invalid resource window')
    with (ROOT/'catalog-refinement.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);RosterCatalog(a.repo.resolve(),a.version,a.hours,a.attempts_per_dog).run()
