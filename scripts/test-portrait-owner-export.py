import importlib.util,unittest
from pathlib import Path
from portrait_owner_export import export_owner_approved
spec=importlib.util.spec_from_file_location('fixtures',Path(__file__).with_name('test-portrait-roster.py'));f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
class OwnerExportTests(unittest.TestCase):
    def test_owner_approval_preserves_nonpassing_scores_without_private_bindings(self):
        state,c,graph=f.RosterTests().fixture()
        approval=dict(acceptance_basis='explicit_owner_override',approved_at=1,recipe=c['recipe'],roster=state['roster'],ai_checked=7,ai_passed=4)
        result=export_owner_approved(approval,dict(id='costume',scene='Garden',clothing='Jacket'),graph)
        self.assertFalse(result['ai_acceptance_claim']);self.assertEqual(result['evaluation']['passing_entries'],4)
        self.assertEqual(result['status'],'owner_approved');self.assertNotIn('private-',str(result))
    def test_unrecorded_approval_is_rejected(self):
        with self.assertRaises(ValueError):export_owner_approved({}, {}, {})
if __name__=='__main__':unittest.main()
