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
