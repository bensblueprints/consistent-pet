import json,tempfile,unittest
from pathlib import Path
from portrait_approval_timing import snapshot,_cache
class TimingTests(unittest.TestCase):
 def test_retry_interval_and_version_isolation(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);repo=r/'repo';v='five';h=r/'catalog-refinement'/v;h.mkdir(parents=True)
   (r/'catalog-public-status.json').write_text(json.dumps(dict(version=v,total=10,counts={'accepted':3})))
   (h/'queue.json').write_text(json.dumps({'items':{'a':{'status':'accepted','run':'five-a'},'b':{'status':'accepted','run':'five-b'},'old':{'status':'accepted','run':'old-policy'}}}))
   for key,stamp in [('a','2026-01-01T00:00:00Z'),('b','2026-01-01T00:10:00Z')]:
    p=repo/'workflows/portraits'/key;p.mkdir(parents=True);(p/'status.json').write_text(json.dumps({'last_updated_utc':stamp}))
   _cache.clear();s=snapshot(r,repo,1767226260)
   self.assertEqual(s['mean_seconds'],600);self.assertEqual(s['approvals'],2);self.assertEqual(s['remaining_seconds'],4140)
   _cache.clear();s=snapshot(r,repo,1767227400)
   self.assertEqual(s['remaining_seconds'],7200)
   self.assertEqual(len(json.loads((r/'approval-timing.json').read_text())['events']),2)
 def test_missing_state_is_nonfatal(self):
  _cache.clear()
  with tempfile.TemporaryDirectory() as d:self.assertIn('error',snapshot(Path(d)))
if __name__=='__main__':unittest.main()
