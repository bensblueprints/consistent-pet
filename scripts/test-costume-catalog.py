"""Durability and training-only evidence checks; no live GPU or network."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

if sys.platform!='win32':
    spec=importlib.util.spec_from_file_location('catalog',Path(__file__).with_name('run-costume-catalog.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@unittest.skipIf(sys.platform=='win32','Linux worker uses flock')
class CatalogTests(unittest.TestCase):
    def fixture(self,root):
        repo=root/'repo';folder=repo/'workflows/portraits';folder.mkdir(parents=True)
        index=[dict(id='costume-'+str(n),name='Costume '+str(n),workflow_folder='workflows/portraits/costume-'+str(n)) for n in range(725)]
        (folder/'index.json').write_text(json.dumps(index))
        (root/'selected-dogs-v3.json').write_text('{"dogs":[]}')
        return repo,index

    def test_queue_resumes_and_changed_cohort_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);repo,index=self.fixture(root)
            with patch.object(module,'ROOT',root):
                first=module.Catalog(repo,'test',1,4);first.state['items']['costume-0'].update(round=2,status='retry_pending');first.save()
                resumed=module.Catalog(repo,'test',1,4)
                self.assertEqual(resumed.state['items']['costume-0']['round'],2)
                (root/'selected-dogs-v3.json').write_text('{"dogs":["different"]}')
                with self.assertRaisesRegex(ValueError,'changed'):module.Catalog(repo,'test',1,4)

    def test_public_report_omits_customer_evidence_and_never_claims_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);repo,index=self.fixture(root);folder=repo/index[0]['workflow_folder'];folder.mkdir()
            (folder/'status.json').write_text('{}')
            with patch.object(module,'ROOT',root):
                catalog=module.Catalog(repo,'test',1,4);item=catalog.state['items']['costume-0'];item.update(status='retry_pending',round=1)
                private=dict(attempts=[dict(recipe=dict(version=1),assessments=[dict(identity=8,fur=7,body=6,template=9,dog_id='PRIVATE_CUSTOMER',reason='PRIVATE_NOTES')])])
                catalog.report(index[0],item,private)
                report=(folder/'REPORT.md').read_text();status=json.loads((folder/'status.json').read_text())
                self.assertNotIn('PRIVATE_',report);self.assertFalse(status['customer_identity_transfer_validated'])
                self.assertEqual(status['status'],'provisional');self.assertFalse((folder/'workflow.json').exists())

    def test_planner_history_contains_no_validation_or_test_feedback(self):
        state=dict(attempts=[dict(recipe=dict(version=1,diagnosis='DOG_DETAILS'),assessments=[dict(identity=7,fur=7,body=7,template=7,reason='training')])],
                   validation=[dict(reason='HOLDOUT_SECRET')],test=[dict(reason='FINAL_SECRET')])
        history=str(module.training_history(state))
        self.assertIn('training',history)
        for secret in ('HOLDOUT_SECRET','FINAL_SECRET','DOG_DETAILS'):self.assertNotIn(secret,history)


if __name__=='__main__':unittest.main()
