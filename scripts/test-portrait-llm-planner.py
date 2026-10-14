import copy
import unittest
from portrait_llm_planner import validate,recipe,BOUNDS
from portrait_autorefine import apply_recipe,DIMENSIONS


class PlannerTests(unittest.TestCase):
    def proposal(self):
        return dict(steps=40,cfg=4.1,grow=48,feather=12,original_megapixels=1.2,face_megapixels=1.0,
            design_megapixels=.6,strategy='fresh-latent',focus=['body','fur'],rationale='Remove the retained old torso silhouette.',
            clothing='Dinner jacket',scene='Seat the dog by the marina, tailoring the jacket to its own body.',require_clothing=True,single_subject=True)

    def test_llm_selects_real_graph_changes_without_executing_code(self):
        proposal=self.proposal();proposal['shell']='steal private files'
        result=recipe(proposal,1,[])
        self.assertEqual(result['cfg'],4.1);self.assertNotIn('shell',result)
        graph={k:{'inputs':{}} for k in ('92:115','92:114','92:110','detailscale','92:85','92:103')}
        apply_recipe(graph,result)
        self.assertEqual(graph['92:103']['inputs']['latent_image'],['92:109',0])
        self.assertEqual(graph['92:115']['inputs']['steps'],40)
        self.assertNotIn(proposal['rationale'],result['instruction'])

    def test_out_of_bounds_and_invalid_control_values_fail_closed(self):
        for key,(_,high) in BOUNDS.items():
            with self.assertRaises(ValueError):validate({**self.proposal(),key:high+1})
        for patch in ({'steps':True},{'grow':40.5},{'strategy':'execute-python'},{'focus':['change-reviewer']},{'single_subject':'yes'}):
            with self.assertRaises(ValueError):validate({**self.proposal(),**patch})

    def test_dog_specific_critique_is_not_baked_into_generic_prompt(self):
        assessment=dict(dog_id='private-dog',**dict.fromkeys(DIMENSIONS,7),defects=[dict(area='fur',severity='major',evidence='Wrong white patch',correction='Restore this dog patch')])
        result=recipe(self.proposal(),0,[assessment])
        self.assertIn('private-dog',str(result['diagnosis']))
        self.assertNotIn('private-dog',result['instruction']);self.assertNotIn('white patch',result['instruction'])

    def test_long_display_explanation_does_not_discard_valid_graph_changes(self):
        proposal=self.proposal();proposal['rationale']='Long explanation. '*80
        self.assertEqual(len(validate(proposal)['rationale']),500)
        with self.assertRaises(ValueError):validate({**proposal,'scene':'x'*701})


if __name__=='__main__':unittest.main()
