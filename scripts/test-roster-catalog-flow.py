"""Exercise the real per-dog retry controller with fake rendering and scoring."""
import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from portrait_llm_planner import recipe

if sys.platform!='win32':
    spec=importlib.util.spec_from_file_location('roster_runner',Path(__file__).with_name('run-roster-catalog.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@unittest.skipIf(sys.platform=='win32','Linux controller uses flock')
class FlowTests(unittest.TestCase):
    def exercise(self,root,always_fail=False):
        proposal=dict(steps=40,cfg=4,grow=48,feather=12,original_megapixels=1,face_megapixels=1,
            design_megapixels=.6,strategy='fresh-latent',focus=['body'],pose_policy='reference',
            rationale='Fix posture',scene='Garden',clothing='Jacket',require_clothing=True,single_subject=True)
        class Fake:
            def __init__(self,plan):
                self.plan=plan;self.run=plan['version'];self.home=root/'private';self.home.mkdir(exist_ok=True)
                self.jobs=self.home/'jobs';self.jobs.mkdir(exist_ok=True)
                self.state=dict(templates={},rows={},generations=0)
                self.dogs={d:dict(input=d+'.png',label='Dog '+d) for d in 'abcdefg'};self.calls=[]
                (self.home/'input-quality-snapshot.json').write_text(json.dumps({d:dict(score=7,confidence='high') for d in self.dogs}))
            def save(self):(root/'auto-refine-status.json').write_text('{}')
            def budget(self):pass
            def prepare(self,t,state):return dict(reference='costume.png'),{}
            def render(self,t,state,source,base,r,dog,stage):
                self.budget();self.calls.append((dog,r['version']));self.state['generations']+=1
                key=f"{dog}-{r['version']}";row=dict(id=key,dog_id=dog,output='private.png',output_sha256=key,prompt_id=key,graph_sha256=key)
                self.state['rows'][key]=row
                graph={k:dict(class_type='LoadImage',inputs=dict(image='private.png')) for k in ('76','detailimage','81','repair-base','repair-mask')}
                graph.update({'9':dict(class_type='SaveImage',inputs=dict(filename_prefix='private')),
                    '92:105':dict(class_type='RandomNoise',inputs=dict(noise_seed=1)),
                    '92:113':dict(class_type='CLIPTextEncode',inputs=dict(text='private'))})
                (self.jobs/(key+'.json')).write_text(json.dumps(dict(graph=graph)))
                return row
            def score(self,row):
                failed=row['dog_id'] in ('b','c') and (always_fail or sum(d=='b' for d,_ in self.calls)<3)
                return dict(identity=9,fur=9,body=6 if failed else 7,template=9,confidence='high',defects=[],output_sha256=row['output_sha256'])
            def publish(self,row):pass
        plan=dict(version='fixture-costume',templates=[dict(id='costume',scene='Garden',clothing='Jacket',initial_proposal=proposal)])
        fake=Fake(plan)
        class Catalog(module.RosterCatalog):
            def save(self):pass
            def report(self,*args):pass
            def stage_reference(self,ref):return 'costume.png','reference-row'
            def propose(self,ref,source,refiner,t,development,initial=False):
                # Real controller still decides which failing dog to repair and when to retry.
                n=len(development['candidates']);return recipe({**proposal,'steps':40+n},n,[])
        c=Catalog.__new__(Catalog);c.home=root;c.version='fixture';c.recipes=6
        c.state=dict(started_at=time.time(),max_hours=1,items={'costume':dict(status='pending',round=0,errors=0,generations=0)})
        (root/'fixture-costume-plan.json').write_text(json.dumps(plan))
        with patch.object(module,'ROOT',root),patch.object(module.core,'Refiner',return_value=fake):
            c.process(dict(id='costume',name='Costume'))
        return c,fake

    def test_full_sweeps_before_revising_then_locks_at_threshold(self):
        with tempfile.TemporaryDirectory() as d:
            c,fake=self.exercise(Path(d))
            self.assertEqual([dog for dog,_ in fake.calls[:14]],list('abcdefg')*2)
            self.assertEqual(c.state['items']['costume']['status'],'accepted')
            export=json.loads((fake.home/'accepted/costume.json').read_text())
            self.assertGreaterEqual(export['evaluation']['passing_entries'],6)

    def test_six_failures_keep_costume_unaccepted_and_other_dogs_still_render(self):
        with tempfile.TemporaryDirectory() as d:
            c,fake=self.exercise(Path(d),always_fail=True)
            self.assertEqual(sum(d=='b' for d,_ in fake.calls),6)
            self.assertEqual(set(d for d,_ in fake.calls),set('abcdefg'))
            self.assertEqual(c.state['items']['costume']['status'],'retry_pending')
            self.assertFalse((fake.home/'accepted').exists())


if __name__=='__main__':unittest.main()
