import unittest
from portrait_input_quality import validate,eligible

class InputTests(unittest.TestCase):
    def test_missing_body_is_not_hidden_by_clear_face(self):
        q=validate(dict(face=9,fur=9,body=5,confidence='high',reason='Face clear; body cropped.',suggestion='Send a body photo.'))
        self.assertEqual(q['score'],5);self.assertFalse(eligible(q))
    def test_seven_qualifies_and_six_or_uncertain_does_not(self):
        for score,confidence,expected in [(7,'high',True),(7,'medium',True),(6,'high',False),(9,'low',False)]:
            q=validate(dict(face=score,fur=score,body=score,confidence=confidence,reason='Visible evidence.',suggestion='Keep the original.'))
            self.assertEqual(eligible(q),expected)
    def test_invalid_scores_never_become_eligible(self):
        with self.assertRaises(ValueError):validate(dict(face=11,fur=9,body=9))
        self.assertFalse(eligible({}));self.assertFalse(eligible(dict(score=9,confidence='high',error='Unreadable')))

if __name__=='__main__':unittest.main()
