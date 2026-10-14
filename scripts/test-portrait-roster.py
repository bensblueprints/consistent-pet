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
        state=dict(roster=list('abcdefg'),candidates=[],locked=False)
        candidate=new_candidate(state,self.recipe())
        graph={k:dict(class_type='LoadImage',inputs=dict(image='private-customer.png')) for k in ('76','detailimage','81','repair-base','repair-mask')}
        graph.update({'9':dict(class_type='SaveImage',inputs=dict(filename_prefix='private-path')),
            '92:105':dict(class_type='RandomNoise',inputs=dict(noise_seed=123)),
            '92:113':dict(class_type='CLIPTextEncode',inputs=dict(text='private-dog-description'))})
        return state,candidate,graph

    def test_next_dog_waits_for_current_dog_to_pass(self):
        state,c,_=self.fixture();self.assertEqual(next_dog(state),'a')
        self.check(c,'a',8);self.assertEqual(next_dog(state),'a')
        self.assertEqual(passing(c),set())

    def test_later_change_rechecks_previously_passing_dogs(self):
        state,c,_=self.fixture();self.check(c,'a');self.assertEqual(next_dog(state),'b')
        self.check(c,'b',7);new_candidate(state,self.recipe(1))
        self.assertEqual(next_dog(state),'a');self.assertEqual(len(state['candidates'][0]['checks']),2)

    def test_failing_dog_gets_six_attempts_then_other_dogs_get_a_turn(self):
        state,c,graph=self.fixture();state.update(focus_dog='b',visit_attempts={})
        for n in range(6):
            self.assertEqual(next_dog(state),'b')
            self.check(c,'b',7);state['visit_attempts']['b']=n+1
            if n<5:c=new_candidate(state,self.recipe(n+1))
        self.assertEqual(next_dog(state),'a')
        for dog in 'acdefg':self.check(c,dog)
        self.assertIsNone(next_dog(state))
        with self.assertRaises(ValueError):export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)
        state.update(visit_attempts={},focus_dog=None)
        self.assertEqual(next_dog(state),'b')

    def test_passing_dog_stops_early_but_changed_recipe_requires_recheck(self):
        state,c,_=self.fixture();state.update(focus_dog='a',visit_attempts={'a':1})
        self.check(c,'a');self.assertEqual(next_dog(state),'b')
        c=new_candidate(state,self.recipe(1));self.assertEqual(next_dog(state),'a')

    def test_all_passes_must_belong_to_one_recipe(self):
        state,c,graph=self.fixture()
        for d in 'abcdef':self.check(c,d)
        self.check(c,'g',7)
        with self.assertRaises(ValueError):export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)
        c2=new_candidate(state,self.recipe(1));self.check(c2,'g')
        with self.assertRaises(ValueError):export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)

    def test_export_is_private_free_and_honest_about_development_data(self):
        state,c,graph=self.fixture()
        for d in state['roster']:self.check(c,d)
        artifact=export_locked(state,dict(id='jacket',scene='Garden',clothing='Jacket'),graph)
        self.assertNotIn('private-',str(artifact));self.assertEqual(artifact['evaluation']['passing_entries'],7)
        self.assertFalse(artifact['evaluation']['unseen_dog_validation']);self.assertEqual(artifact['status'],'locked_on_development_roster')

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
