import copy
import importlib.util
import json
import unittest
from pathlib import Path
from portrait_llm_planner import validate
from portrait_autorefine import signature

spec = importlib.util.spec_from_file_location('recovery', Path(__file__).with_name('recover-planner-bound.py'))
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def sample(self):
        proposal = dict(steps=48, cfg=4.5, grow=60, feather=20, original_megapixels=1.2,
                        face_megapixels=1.5, design_megapixels=.2, strategy='fresh-latent',
                        rationale='Reduce template conditioning.', clothing='Beret and vest',
                        scene='Seated beside a vintage car.', require_clothing=True,
                        single_subject=True, focus=['identity', 'fur', 'body'])
        request = {'payload': {'images': []}}
        request['fingerprint'] = signature(request['payload'])
        response = dict(fingerprint=request['fingerprint'], error='Invalid planner design_megapixels', raw=json.dumps(proposal))
        return request, response

    def test_bounded_repair_preserves_evidence_and_inputs(self):
        request, response = self.sample()
        original = copy.deepcopy(response)
        result = recovery.repaired_result(request, response, .25, validate, signature)
        self.assertEqual(response, original)
        self.assertEqual(result['raw'], original['raw'])
        self.assertEqual(result['proposal']['design_megapixels'], .25)
        self.assertEqual(result['operator_recovery']['before'], .2)
        self.assertNotIn('error', result)

    def test_cannot_bypass_full_validator(self):
        request, response = self.sample()
        for value in (.2, 99, float('nan')):
            with self.assertRaises(ValueError):
                recovery.repaired_result(request, response, value, validate, signature)
        raw = json.loads(response['raw']); raw['strategy'] = 'run-shell'; response['raw'] = json.dumps(raw)
        with self.assertRaises(ValueError):
            recovery.repaired_result(request, response, .25, validate, signature)

    def test_rejects_unrelated_errors_or_changed_request(self):
        request, response = self.sample()
        with self.assertRaises(ValueError):
            recovery.repaired_result(request, {**response, 'error': 'CUDA failure'}, .25, validate, signature)
        request['payload']['changed'] = True
        with self.assertRaises(ValueError):
            recovery.repaired_result(request, response, .25, validate, signature)


if __name__ == '__main__':
    unittest.main()
