import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('initializer',HERE/'init-portrait-lab.py')
initializer=importlib.util.module_from_spec(spec);spec.loader.exec_module(initializer)


class SetupTests(unittest.TestCase):
    def fixture(self,folder):
        dogs=[]
        for i in range(7):
            Image.new('RGB',(16,16),(i*30,10,20)).save(folder/f'dog-{i}.png')
            dogs.append(dict(id=f'dog-{i}',label=f'Fixture dog {i}',original=f'dog-{i}.png',face=f'dog-{i}.png'))
        Image.new('RGB',(16,16),'green').save(folder/'reference.png')
        model=folder/'judge';model.mkdir()
        manifest=dict(dogs=dogs,judge=dict(path=str(model),model='test-only',revision='test-only'),
            templates=[dict(id='jacket',title='Jacket',reference='reference.png',clothing='jacket',scene='Garden')])
        path=folder/'manifest.json';path.write_text(json.dumps(manifest));return path

    def test_new_runtime_can_be_initialized_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);manifest=self.fixture(folder);runtime=folder/'runtime'
            result=initializer.initialize(manifest,runtime,HERE.parent/'workflows/flux-klein-4b-base-api.json')
            self.assertEqual(result['generations_submitted'],0)
            self.assertEqual(len(json.loads((runtime/'selected-dogs.json').read_text())['dogs']),7)
            from portrait_autorefine import validate_plan
            validate_plan(json.loads((runtime/'plan.json').read_text()))
            with self.assertRaisesRegex(ValueError,'already exists'):
                initializer.initialize(manifest,runtime,HERE.parent/'workflows/flux-klein-4b-base-api.json')

    def test_bad_fixture_leaves_no_partial_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);manifest=self.fixture(folder);runtime=folder/'runtime'
            (folder/'dog-3.png').unlink()
            with self.assertRaises(FileNotFoundError):
                initializer.initialize(manifest,runtime,HERE.parent/'workflows/flux-klein-4b-base-api.json')
            self.assertFalse(runtime.exists())


if __name__=='__main__':unittest.main()
