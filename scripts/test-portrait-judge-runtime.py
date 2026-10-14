import json,tempfile,unittest
from pathlib import Path
from portrait_judge_runtime import pending_rows,snapshot,PROFILE
from portrait_fur_body_rubric import RUBRIC


class RuntimeTests(unittest.TestCase):
    def test_first_scores_precede_old_audits_and_failures_are_bounded(self):
        rows=[dict(id='old',output='old.png',ai_review={'rubric':'old'},repair_version='repair'),
              dict(id='new',output='new.png',finished_at=10),dict(id='failed',output='f.png'),
              dict(id='done',output='done.png',ai_review={'rubric':RUBRIC}),dict(id='unfinished')]
        self.assertEqual([r['id'] for r in pending_rows(rows,{'failed':3},['old'])],['new','old'])

    def test_oldest_unscored_first_and_repair_priority_within_queue(self):
        rows=[dict(id='newest',output='x',finished_at=30),dict(id='older',output='y',finished_at=10),
              dict(id='repair',output='z',finished_at=40,repair_version='repair'),
              dict(id='auto',output='a',finished_at=50,auto_refine_version='auto')]
        self.assertEqual([r['id'] for r in pending_rows(rows,{})],['repair','auto','older','newest'])

    def test_live_metrics_hide_unknown_rows_and_stale_activity(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'judge-live.json';p.write_text(json.dumps(dict(status='Scoring',row_id='secret',heartbeat_at=100,started_at=90,secret='private')))
            rows=[dict(id='a',output='a',ai_status='Scoring')]
            result=snapshot(rows,root,now=105)
            self.assertIsNone(result['active_row_id']);self.assertNotIn('secret',result)
            self.assertEqual(rows[0]['ai_status'],'Queued')
            p.write_text(json.dumps(dict(status='Scoring',row_id='a',heartbeat_at=100,started_at=90)))
            self.assertEqual(snapshot(rows,root,now=105)['active_row_id'],'a')
            self.assertIsNone(snapshot(rows,root,now=120)['active_row_id'])
            self.assertEqual(snapshot(rows,root,now=120)['status'],'Offline or reconnecting')

    def test_counts_and_timings_do_not_mix_old_inference_profiles(self):
        with tempfile.TemporaryDirectory() as root:
            rows=[dict(id='none',output='x'),dict(id='old',output='y',ai_review={'rubric':'old'}),
                  dict(id='v3',output='z',ai_review={'rubric':RUBRIC,'seconds':90}),
                  dict(id='fast',output='f',seconds=36,finished_at=10,ai_review={'rubric':RUBRIC,'seconds':18,'total_seconds':19,'created_at':10,'inference_profile':PROFILE})]
            result=snapshot(rows,root,now=20)
            self.assertEqual((result['unscored'],result['reaudit_pending'],result['scored']),(1,1,3))
            self.assertEqual(result['recent_score_seconds'],19);self.assertEqual(result['recent_render_seconds'],36)
            self.assertEqual(result['timing_samples'],1)


if __name__=='__main__':unittest.main()
