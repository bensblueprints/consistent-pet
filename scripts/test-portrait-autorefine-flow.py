"""Linux orchestration checks with an explicit generator/reviewer double, no GPU."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys

if sys.platform!='win32':
    spec=importlib.util.spec_from_file_location('refiner',Path(__file__).with_name('run-portrait-autorefine.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def score(value):return dict(identity=value,fur=value,body=value,template=value,confidence='high',defects=[])


@unittest.skipIf(sys.platform=='win32','Production runner uses Linux flock; run on GPU host')
class FlowTests(unittest.TestCase):
    def make_runner(self,path,validation_score=9,always_low=False):
        class Fake(module.Refiner):
            def save(self):pass
            def prepare(self,t,state):
                state['asset_hashes']={};return dict(dog_id='a',template='Test costume'),{}
            def evaluate(self,t,state,source,base,recipe,dogs,stage):
                self.calls.append((stage,recipe['version'],list(dogs),module.signature(recipe)))
                for dog in dogs:
                    key=f"{self.run}-{t['id']}-r{recipe['version']}-{stage}-{dog}"
                    graph={k:{'inputs':{'image':'fixture.png'}} for k in ('76','detailimage','81','repair-base','repair-mask')}
                    graph.update({'9':{'inputs':{'filename_prefix':'fixture'}},'92:105':{'inputs':{'noise_seed':123}},'92:113':{'inputs':{'text':'Dog-specific description'}}})
                    (self.jobs/(key+'.json')).write_text(json.dumps({'graph':graph}))
                    self.state['rows'][key]={'source_hashes':{}}
                value=8 if always_low or (stage=='tune' and recipe['version']==1) else validation_score if stage=='validation' else 9
                return [score(value) for _ in dogs]
        r=Fake.__new__(Fake);r.home=Path(path);r.jobs=r.home/'jobs';r.jobs.mkdir();r.run='fixture'
        r.plan={'max_attempts':3,'patience':2};r.calls=[];r.state={'templates':{},'rows':{}}
        r.splits={'train':['a','b','c'],'validation':['d','e'],'test':['f','g']}
        r.dogs={k:{'input':k+'.png','crop':k+'-face.png'} for k in 'abcdefg'}
        return r

    def test_pass_requires_frozen_validation_and_final_dogs(self):
        with tempfile.TemporaryDirectory() as path:
            r=self.make_runner(path);t={'id':'costume','scene':'Garden','clothing':'Suit'};r.template(t)
            self.assertEqual([c[0] for c in r.calls],['tune','tune','validation','test'])
            self.assertEqual(r.calls[1][3],r.calls[2][3]);self.assertEqual(r.calls[2][3],r.calls[3][3])
            self.assertEqual(r.state['templates']['costume']['status'],'AI target met across dogs')
            prior=len(r.calls);r.template(t);self.assertEqual(len(r.calls),prior)
            frozen=json.loads((Path(path)/'costume-frozen.json').read_text())
            self.assertEqual(frozen['recipe']['version'],2)
            self.assertTrue((Path(path)/'accepted/costume.json').exists())

    def test_failed_validation_never_rerolls_or_uses_final_test_dogs(self):
        with tempfile.TemporaryDirectory() as path:
            r=self.make_runner(path,validation_score=8);r.template({'id':'costume','scene':'Garden','clothing':'Suit'})
            self.assertNotIn('test',[c[0] for c in r.calls])
            result=r.state['templates']['costume'];self.assertEqual(result['status'],'Best saved; target not met')
            self.assertEqual(len(result['validation']),3)
            self.assertFalse((Path(path)/'accepted/costume.json').exists())

    def test_expanded_validation_includes_remaining_dogs_with_frozen_recipe(self):
        with tempfile.TemporaryDirectory() as path:
            r=self.make_runner(path);r.plan['validate_all_dogs']=True
            for k in ('h','i','j'):r.dogs[k]={'input':k+'.png','crop':k+'-face.png'}
            r.splits['train'].extend(['h','i','j'])
            r.template({'id':'costume','scene':'Garden','clothing':'Suit'})
            check=next(c for c in r.calls if c[0]=='validation')
            self.assertEqual(set(check[2]),set('cdehij'))
            self.assertEqual(check[3],r.calls[-1][3])

    def test_stagnation_keeps_earliest_best_and_still_checks_other_dogs(self):
        with tempfile.TemporaryDirectory() as path:
            r=self.make_runner(path,always_low=True);r.template({'id':'costume','scene':'Garden','clothing':'Suit'})
            result=r.state['templates']['costume'];self.assertEqual(len(result['attempts']),3)
            self.assertEqual(result['best_recipe']['version'],1)
            self.assertEqual(r.calls[-1][0],'validation');self.assertNotIn('test',[c[0] for c in r.calls])

    def test_bootstrap_cannot_leak_a_holdout_review_into_tuning(self):
        with tempfile.TemporaryDirectory() as path:
            r=self.make_runner(path)
            with self.assertRaisesRegex(ValueError,'non-tuning dog'):
                r.template(dict(id='costume',scene='Garden',clothing='Suit',initial_feedback=[dict(dog_id='f',**score(9))]))
            self.assertEqual(r.calls,[])


if __name__=='__main__':unittest.main()
