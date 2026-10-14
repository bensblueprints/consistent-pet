import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('sync',Path(__file__).with_name('sync-costume-progress.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ProgressTests(unittest.TestCase):
    def test_roster_export_requires_all_entries_and_publishes_only_parameterized_graph(self):
        from portrait_autorefine import signature
        for passing in (6,7):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);folder=root/'workflows/portraits/costume';folder.mkdir(parents=True)
                (folder.parent/'index.json').write_text(json.dumps([dict(workflow_folder='workflows/portraits/costume')]))
                args=SimpleNamespace(repo=root,identity=Path('operator-key'),host='operator-host',port=22,remote_repo='/repo',publish=False)
                def git(command,**kwargs):
                    return 'main' if command[1]=='branch' else 'https://github.com/bensblueprints/consistent-pet.git' if command[1]=='remote' else ''
                data=dict(status='locked_on_development_roster',format='consistent-pet-roster-recipe-v1',
                    evaluation=dict(roster_entries=7,passing_entries=passing,same_recipe_for_all=True,unseen_dog_validation=False),
                    graph={'1':dict(class_type='LoadImage',inputs=dict(image='__DOG_ORIGINAL__'))})
                data['sha256']=signature(data)
                files={'workflows/portraits/costume/workflow.json':json.dumps(data)}
                with patch.object(module.subprocess,'check_output',side_effect=git),patch.object(module.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(files))):
                    if passing==7:module.run(args);self.assertTrue((folder/'workflow.json').exists())
                    else:
                        with self.assertRaises(ValueError):module.run(args)
                        self.assertFalse((folder/'workflow.json').exists())

    def test_85_percent_export_requires_fifteen_of_seventeen_and_complete_round(self):
        from portrait_autorefine import signature
        for version,passing,checked in [(v,p,c) for v in (3,4) for p,c in [(14,17),(15,17),(15,16)]]:
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);folder=root/'workflows/portraits/costume';folder.mkdir(parents=True)
                (folder.parent/'index.json').write_text(json.dumps([dict(workflow_folder='workflows/portraits/costume')]))
                args=SimpleNamespace(repo=root,identity=Path('operator-key'),host='operator-host',port=22,remote_repo='/repo',publish=False)
                def git(command,**kwargs):
                    return 'main' if command[1]=='branch' else 'https://github.com/bensblueprints/consistent-pet.git' if command[1]=='remote' else ''
                data=dict(status='locked_on_qualified_roster',format=f'consistent-pet-roster-recipe-v{version}',thresholds=dict(identity=8 if version==4 else 9,fur=8 if version==4 else 9,body=7,template=8 if version==4 else 9),
                    evaluation=dict(roster_entries=17,passing_entries=passing,checked_entries=checked,required_pass_percent=85,required_passing_entries=15,input_minimum=7,same_recipe_for_all=True,unseen_dog_validation=False),
                    graph={'1':dict(class_type='LoadImage',inputs=dict(image='__DOG_ORIGINAL__'))})
                data['sha256']=signature(data)
                files={'workflows/portraits/costume/workflow.json':json.dumps(data)}
                with patch.object(module.subprocess,'check_output',side_effect=git),patch.object(module.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(files))):
                    if passing==15 and checked==17:module.run(args);self.assertTrue((folder/'workflow.json').exists())
                    else:
                        with self.assertRaises(ValueError):module.run(args)

    def test_publisher_rejects_unexpected_paths_private_evidence_and_bound_workflows(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'workflows/portraits/costume';folder.mkdir(parents=True)
            (folder.parent/'index.json').write_text(json.dumps([dict(workflow_folder='workflows/portraits/costume')]))
            args=SimpleNamespace(repo=root,identity=Path('operator-key'),host='operator-host',port=22,remote_repo='/repo',publish=False)
            def git(command,**kwargs):
                return 'main' if command[1]=='branch' else 'https://github.com/bensblueprints/consistent-pet.git' if command[1]=='remote' else ''
            for files in ({'../secret':'bad'}, {'workflows/portraits/costume/REPORT.md':'inputs-v3-private.png'},
                          {'workflows/portraits/costume/workflow.json':'{"status":"provisional"}'}):
                with patch.object(module.subprocess,'check_output',side_effect=git),patch.object(module.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(files))):
                    with self.assertRaises(ValueError):module.run(args)
                self.assertEqual(list(folder.iterdir()),[])


if __name__=='__main__':unittest.main()
