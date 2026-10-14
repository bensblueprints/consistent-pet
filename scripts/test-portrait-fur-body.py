"""A good face cannot hide retained template fur or a broken body."""
import json
import unittest
from portrait_fur_body_rubric import validate


def candidate(**changes):
    base=dict(identity=9,fur=9,body=9,template=9,confidence='high',
              face_notes='Visible face matches.',fur_notes='Visible markings match.',
              body_notes='Proportions are coherent.',preparation_notes='No visible missing parts.',
              reason='Likeness and body are consistent.',defects=[])
    return json.dumps({**base,**changes})


class RubricTests(unittest.TestCase):
    def test_wrong_body_or_fur_cannot_be_hidden_by_face(self):
        for area in ('fur','body'):
            with self.subTest(area=area):
                result=validate(candidate(**{area:2}))
                self.assertLessEqual(result['score'],3)
                self.assertTrue(result['needs_revision'])

    def test_major_visible_defect_caps_inconsistent_high_scores(self):
        defects=[dict(area='fur',severity='major',evidence='Golden paws on the white dog.',correction='Replace all visible paw fur using the source coat.')]
        result=validate(candidate(defects=defects))
        self.assertLessEqual(result['score'],5);self.assertEqual(result['verdict'],'Needs revision')

    def test_preparation_problem_is_separate_from_output_anatomy(self):
        defects=[dict(area='preparation',severity='major',evidence='Cutout loses a source-visible foot.',correction='Repair foreground mask and retain the whole visible limb.')]
        result=validate(candidate(defects=defects))
        self.assertEqual(result['body'],9);self.assertEqual(result['score'],9)
        self.assertTrue(result['needs_revision'])

    def test_good_output_still_requires_human_review(self):
        result=validate(candidate())
        self.assertEqual(result['score'],9);self.assertFalse(result['needs_revision'])
        self.assertEqual(result['verdict'],'Human review required')
        self.assertEqual(validate(candidate(template=1))['score'],3.5)

    def test_invalid_scores_and_unsupported_defects_are_rejected(self):
        for changes in ({'fur':True},{'body':11},{'fur_notes':''},{'defects':'none'},
                        {'defects':[dict(area='body',severity='major',evidence='bad',correction='')]},
                        {'defects':[dict(area='unknown',severity='major',evidence='bad',correction='Fix proportions.')]},
                        {'confidence':'certain'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate(candidate(**changes))


if __name__=='__main__':unittest.main()
