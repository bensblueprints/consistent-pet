"""Exercise durable feedback, stale-output protection and JSON write boundaries."""
import importlib.util
import io
import json
import tempfile
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path

import portrait_reviews as reviews
spec=importlib.util.spec_from_file_location('scorer',Path(__file__).with_name('score-portrait-outputs.py'))
scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
export_spec=importlib.util.spec_from_file_location('exporter',Path(__file__).with_name('export-portrait-training-feedback.py'))
exporter=importlib.util.module_from_spec(export_spec);export_spec.loader.exec_module(exporter)
report_spec=importlib.util.spec_from_file_location('reporter',Path(__file__).with_name('report-portrait-judge-agreement.py'))
reporter=importlib.util.module_from_spec(report_spec);report_spec.loader.exec_module(reporter)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.old=reviews.ROOT
        reviews.ROOT=Path(self.temp.name);(reviews.ROOT/'media').mkdir()
        self.image=reviews.ROOT/'media'/'example.png';self.image.write_bytes(b'output one')
        self.row=dict(id='test-dog-style-v1',status='Complete',output='example.png')
        self.payload=dict(row_id=self.row['id'],output_sha256=reviews.output_hash(self.row),score=4,
                          notes='Muzzle is too long.',submission_id=str(uuid.uuid4()))

    def tearDown(self):
        reviews.ROOT=self.old;self.temp.cleanup()

    def test_history_and_retry_are_durable(self):
        reviews.save_human(self.payload,[self.row]);reviews.save_human(self.payload,[self.row])
        next_review={**self.payload,'submission_id':str(uuid.uuid4()),'score':6,'notes':'Reconsidered after comparing ears.'}
        reviews.save_human(next_review,[self.row])
        fresh=reviews.attach([dict(self.row)])[0]
        self.assertEqual([x['score'] for x in fresh['human_reviews']],[4,6])
        self.assertEqual(fresh['human_review']['notes'],next_review['notes'])
        with self.assertRaises(ValueError):reviews.save_human({**self.payload,'score':9},[self.row])

    def test_invalid_reviews_do_not_write(self):
        for value in [0,11,5.5,'5',True,None]:
            with self.subTest(score=value),self.assertRaises(ValueError):
                reviews.save_human({**self.payload,'score':value},[self.row])
        for changes in [{'row_id':'unknown'},{'notes':'x'*2001},{'notes':{}},{'output_sha256':'stale'},{'submission_id':'bad'}]:
            with self.subTest(changes=list(changes)),self.assertRaises(ValueError):
                reviews.save_human({**self.payload,**changes},[self.row])
        with self.assertRaises(ValueError):reviews.save_human(self.payload,[{**self.row,'status':'Rendering'}])
        self.assertEqual(reviews.attach([dict(self.row)])[0]['human_reviews'],[])

    def test_changed_output_does_not_inherit_old_scores(self):
        reviews.save_human(self.payload,[self.row]);self.image.write_bytes(b'new output version')
        fresh=reviews.attach([dict(self.row)])[0]
        self.assertIsNone(fresh['human_review'])
        with self.assertRaises(ValueError):reviews.save_human(self.payload,[self.row])

    def test_ai_never_overwrites_human(self):
        reviews.save_human(self.payload,[self.row])
        assessment=dict(output_sha256=self.payload['output_sha256'],rubric='test-v1',score=8.2,model='test')
        reviews.save_ai(self.row,assessment)
        reviews.save_ai(self.row,{**assessment,'rubric':'test-v2','score':3})
        fresh=reviews.attach([dict(self.row)])[0]
        self.assertEqual(fresh['human_review']['score'],4);self.assertEqual(fresh['ai_review']['score'],3)
        self.assertEqual(fresh['ai_previous'][0]['score'],8.2)

    def test_http_boundaries(self):
        class Handler:
            def __init__(self,payload,content='application/json',site='same-origin'):
                data=json.dumps(payload).encode();self.headers={'Content-Type':content,'Content-Length':str(len(data)),'Sec-Fetch-Site':site};self.rfile=io.BytesIO(data);self.wfile=io.BytesIO()
            def send_response(self,status):self.status=status
            def send_header(self,*args):pass
            def end_headers(self):pass
        for content,site,expected in [('text/plain','same-origin',400),('application/json','cross-site',400),('application/json','same-origin',200)]:
            h=Handler(self.payload,content,site);reviews.handle_post(h,[self.row]);self.assertEqual(h.status,expected)

    def test_ai_scoring_rejects_bad_data_and_caps_wrong_results(self):
        base=dict(identity=1,template=10,anatomy=10,reason='Wrong individual dog.',flags=['wrong dog'],confidence='high')
        self.assertEqual(scorer.validate(json.dumps(base))['score'],2)
        self.assertEqual(scorer.validate(json.dumps({**base,'identity':10,'template':1}))['score'],3.5)
        for changes in [{'identity':11},{'identity':True},{'reason':''},{'flags':'none'},{'confidence':'certain'}]:
            with self.subTest(changes=list(changes)),self.assertRaises(ValueError):scorer.validate(json.dumps({**base,**changes}))

    def test_training_export_has_no_identity_leakage_or_ai_only_labels(self):
        old_root=exporter.ROOT;exporter.ROOT=reviews.ROOT
        try:
            dogs=[dict(id=f'dog-{i}',source_sha256=f'identity-{i}',crop='example.png') for i in range(10)]
            (reviews.ROOT/'selected-dogs.json').write_text(json.dumps({'dogs':dogs}))
            rows=[]
            for dog in dogs:
                for version in ('v1','v2'):
                    row={**self.row,'id':dog['id']+'-'+version,'dog_id':dog['id'],'input':'example.png','reference':'example.png'}
                    rows.append(row)
                    reviews.save_human({**self.payload,'row_id':row['id'],'submission_id':str(uuid.uuid4())},[row])
            rows.append({**self.row,'id':'unreviewed-ai-only','dog_id':'dog-0','input':'example.png','reference':'example.png'})
            (reviews.ROOT/'dog-batch.json').write_text(json.dumps({'rows':rows}))
            revision={**rows[0],'id':'dog-0-shadow-v3'}
            reviews.save_human({**self.payload,'row_id':revision['id'],'submission_id':str(uuid.uuid4())},[revision])
            (reviews.ROOT/'dog-revisions.json').write_text(json.dumps({'rows':[revision]}))
            full={**rows[0],'id':'dog-0-full-library-new-style'}
            reviews.save_human({**self.payload,'row_id':full['id'],'submission_id':str(uuid.uuid4())},[full])
            (reviews.ROOT/'dog-library-batch.json').write_text(json.dumps({'rows':[full]}))
            destination=reviews.ROOT/'dataset'
            with redirect_stdout(io.StringIO()):exporter.export(destination)
            seen={};count=0
            for split in ('train','validation','test'):
                for line in (destination/(split+'.jsonl')).read_text().splitlines():
                    item=json.loads(line);count+=1
                    self.assertNotEqual(item['id'],'unreviewed-ai-only')
                    self.assertEqual(seen.setdefault(item['identity_group'],split),split)
            self.assertEqual(count,22)
            readiness=json.loads((destination/'readiness.json').read_text())
            self.assertFalse(readiness['pilot_data_ready']);self.assertFalse(readiness['training_complete'])
        finally:exporter.ROOT=old_root

    def test_agreement_uses_matching_output_hash_and_independent_human_label(self):
        base=dict(id='example',dog_id='dog-0',image_hashes={'output':'current'},human_score=4,human_notes='Muzzle changed.')
        records=[{**base,'ai_estimate':{'score':8,'output_sha256':'current','rubric':'v1'}},
                 {**base,'id':'stale','ai_estimate':{'score':4,'output_sha256':'old','rubric':'v1'}},
                 {**base,'id':'pending','ai_estimate':None}]
        summary=reporter.summarize(records)
        self.assertEqual(summary['count'],1)
        self.assertEqual(summary['mean_absolute_error'],4)
        self.assertEqual(summary['mean_signed_error'],4)
        self.assertEqual(summary['within_one_point'],0)

    def test_revised_rubric_agreement_stays_separate(self):
        base=dict(id='example',dog_id='dog-0',image_hashes={'output':'current'},human_score=4,human_notes='Wrong body.')
        records=[{**base,'ai_estimate':{'score':8,'output_sha256':'current','rubric':'v2'}},
                 {**base,'id':'revised','ai_estimate':{'score':4,'output_sha256':'current','rubric':'v3'}}]
        for split,rows in [('train',records),('validation',[]),('test',[])]:
            (reviews.ROOT/(split+'.jsonl')).write_text('\n'.join(json.dumps(r) for r in rows))
        with redirect_stdout(io.StringIO()):result=reporter.report(reviews.ROOT)
        self.assertTrue(result['mixed_rubrics'])
        self.assertEqual(result['by_rubric']['v2']['mean_absolute_error'],4)
        self.assertEqual(result['by_rubric']['v3']['mean_absolute_error'],0)
        self.assertIn('mixes scoring methods',result['note'])


if __name__=='__main__':unittest.main()
