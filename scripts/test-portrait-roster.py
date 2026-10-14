import copy
import unittest
from portrait_roster import new_candidate,next_dog,record_check,passing,export_locked
from portrait_llm_planner import recipe
from portrait_autorefine import DIMENSIONS


class RosterTests(unittest.TestCase):
    def recipe(self,n=0):
        return recipe(dict(steps=40+n,cfg=4,grow=48,feather=12,original_megapixels=1,face_megapixels=1,
            design_megapixels=.6,strategy='fresh-latent',focus=['body'],pose_policy='natural-sitting',
            rationale='Fix posture',scene='A garden',clothing='Jacket',require_clothing=True,single_subject=True),n,[])

    def check(self,candidate,dog,value=9):
        ai=dict(dog_id=dog,**dict.fromkeys(DIMENSIONS,value),confidence='high',defects=[],output_sha256='output-'+dog)
        row=dict(id='private-row-'+dog,output_sha256='output-'+dog,prompt_id='private-job-'+dog,graph_sha256='graph-'+dog)
        record_check(candidate,dog,ai,row)

    def fixture(self):
        state=dict(roster=list('abcdefg'),candidates=[],locked=False,input_quality={d:dict(score=7,confidence='high') for d in 'abcdefg'})
        candidate=new_candidate(state,self.recipe())
        graph={k:dict(class_type='LoadImage',inputs=dict(image='private-customer.png')) for k in ('76','detailimage','81','repair-base','repair-mask')}
        graph.update({'9':dict(class_type='SaveImage',inputs=dict(filename_prefix='private-path')),
            '92:105':dict(class_type='RandomNoise',inputs=dict(noise_seed=123)),
            '92:113':dict(class_type='CLIPTextEncode',inputs=dict(text='private-dog-description'))})
        return state,candidate,graph

    def test_full_roster_sweep_before_retry(self):
        state,c,_=self.fixture()
        for d in state['roster']:
            self.assertEqual(next_dog(state),d)
            self.check(c,d,7)
        self.assertEqual(next_dog(state),'a')
        state['visit_attempts']={d:6 for d in state['roster']}
        self.assertIsNone(next_dog(state))

    def test_changed_recipe_rechecks_every_dog(self):
        state,c,_=self.fixture()
        for d in state['roster']:self.check(c,d)
        self.assertIsNone(next_dog(state))
        new_candidate(state,self.recipe(1))
        self.assertEqual(next_dog(state),'a')

    def test_85_percent_uses_full_roster_and_requires_complete_sweep(self):
        state,c,graph=self.fixture()
        state['roster']=[str(n) for n in range(17)]
        state['input_quality']={d:dict(score=7,confidence='high') for d in state['roster']}
        for d in state['roster'][:14]:self.check(c,d)
        for d in state['roster'][15:]:self.check(c,d,7)
        with self.assertRaises(ValueError):export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)
        self.check(c,'14')
        artifact=export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)
        self.assertEqual(artifact['evaluation']['passing_entries'],15)
        self.assertEqual(artifact['evaluation']['required_passing_entries'],15)
        self.assertEqual(artifact['evaluation']['checked_entries'],17)
        c2=new_candidate(state,self.recipe(1));self.check(c2,'16')
        with self.assertRaises(ValueError):export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)

    def test_fourteen_of_seventeen_fails(self):
        state,c,graph=self.fixture();state['roster']=[str(n) for n in range(17)]
        state['input_quality']={d:dict(score=7,confidence='high') for d in state['roster']}
        for n,d in enumerate(state['roster']):self.check(c,d,9 if n<14 else 7)
        with self.assertRaises(ValueError):export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)

    def test_export_is_private_free_and_honest_about_development_data(self):
        state,c,graph=self.fixture()
        for d in state['roster']:self.check(c,d)
        artifact=export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)
        self.assertNotIn('private-',str(artifact));self.assertEqual(artifact['evaluation']['passing_entries'],7)
        self.assertFalse(artifact['evaluation']['unseen_dog_validation']);self.assertEqual(artifact['status'],'locked_on_qualified_roster')

    def test_body_seven_passes_but_face_fur_design_still_require_nine(self):
        from portrait_roster import meets_target
        a=dict(identity=9,fur=9,body=7,template=9,confidence='high',defects=[])
        self.assertTrue(meets_target(a))
        for key,value in [('identity',8),('fur',8),('body',6),('template',8)]:self.assertFalse(meets_target({**a,key:value}))

    def test_low_quality_input_cannot_lock(self):
        state,c,graph=self.fixture()
        for d in state['roster']:self.check(c,d)
        state['input_quality']['a']['score']=6
        with self.assertRaises(ValueError):export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)

    def test_changed_recipe_or_duplicate_job_evidence_cannot_lock(self):
        for mode in ('recipe','job'):
            state,c,graph=self.fixture()
            for d in state['roster']:self.check(c,d)
            if mode=='recipe':c['recipe']['steps']+=1
            else:c['checks']['b']['prompt_id']=c['checks']['a']['prompt_id']
            with self.assertRaises(ValueError):export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)

    def test_duplicate_recipe_or_mismatched_score_is_rejected(self):
        state,c,_=self.fixture()
        with self.assertRaises(ValueError):new_candidate(state,self.recipe())
        with self.assertRaises(ValueError):record_check(c,'a',dict(dog_id='b'),{})
        with self.assertRaises(ValueError):record_check(c,'a',dict(dog_id='a',output_sha256='wrong'),dict(output_sha256='right'))


if __name__=='__main__':unittest.main()
