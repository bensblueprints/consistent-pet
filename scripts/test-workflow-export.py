import copy
import importlib.util
from pathlib import Path
import unittest
from portrait_autorefine import DIMENSIONS,next_recipe,freeze_recipe,signature

spec=importlib.util.spec_from_file_location('exporter',Path(__file__).with_name('export-accepted-workflow.py'))
exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)


class ExportTests(unittest.TestCase):
    def fixture(self):
        graph={k:{'class_type':'LoadImage','inputs':{'image':'private-customer.png'}} for k in ('76','detailimage','81','repair-base','repair-mask')}
        graph.update({'9':{'class_type':'SaveImage','inputs':{'filename_prefix':'private'}},
                      '92:105':{'class_type':'RandomNoise','inputs':{'noise_seed':1}},
                      '92:113':{'class_type':'CLIPTextEncode','inputs':{'text':'Private description'}}})
        frozen=freeze_recipe(next_recipe(0),dict(id='jacket',scene='Garden',clothing='Jacket'),graph,{'private-asset.png':'sha'},['a','b'],['c','d','e'],['f','g'])
        def scores(ids):return [dict(dog_id=i,**dict.fromkeys(DIMENSIONS,9),confidence='high',defects=[]) for i in ids]
        return dict(status='AI target met across dogs',workflow=frozen,tuning=scores('ab'),scores={'validation':scores('cde'),'test':scores('fg')})

    def test_export_removes_private_assets_and_preserves_parameterized_graph(self):
        original=self.fixture();result=exporter.sanitized(original)
        self.assertNotIn('private-',str(result));self.assertNotIn('tune_dogs',result)
        self.assertEqual(result['graph']['76']['inputs']['image'],'__DOG_ORIGINAL__')
        self.assertEqual(original['workflow']['asset_hashes'],{'private-asset.png':'sha'})
        original['workflow']['recipe']['strategy']='fresh-latent'
        original['workflow']['recipe_sha256']=signature({k:v for k,v in original['workflow'].items() if k!='recipe_sha256'})
        self.assertEqual(exporter.sanitized(original)['recipe']['strategy'],'fresh-latent')

    def test_export_rejects_provisional_and_failed_or_leaked_assessments(self):
        for change in ('provisional','low','overlap','checksum'):
            item=self.fixture()
            if change=='provisional':item['status']='Best saved; target not met'
            elif change=='low':item['scores']['test'][0]['body']=8
            elif change=='overlap':item['scores']['test'][0]['dog_id']='a'
            else:item['workflow']['scene']='Changed'
            with self.assertRaises(ValueError):exporter.sanitized(item)

    def test_expanded_cohort_requires_every_frozen_validation_assessment(self):
        item=self.fixture();frozen=item['workflow']
        for i in range(25):
            dog='additional-'+str(i);frozen['validation_dogs'].append(dog)
            item['scores']['validation'].append(dict(dog_id=dog,**dict.fromkeys(DIMENSIONS,9),confidence='high',defects=[]))
        frozen['recipe_sha256']=signature({k:v for k,v in frozen.items() if k!='recipe_sha256'})
        self.assertEqual(exporter.sanitized(item)['evaluation']['validation_dogs'],28)
        item['scores']['validation'][-1]['fur']=8
        with self.assertRaises(ValueError):exporter.sanitized(item)


if __name__=='__main__':unittest.main()
