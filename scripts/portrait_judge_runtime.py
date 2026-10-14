"""Queue policy and safe live telemetry for the local vision reviewer."""
import json
import statistics
import threading
import time
from pathlib import Path

from portrait_fur_body_rubric import RUBRIC

PROFILE='compact-v1'


def pending_rows(rows,failures,priority=()):
    pending=[r for r in rows if r.get('output') and (r.get('ai_review') or {}).get('rubric')!=RUBRIC and failures.get(r['id'],0)<3]
    ranks={name:i for i,name in enumerate(priority)}
    def order(r):
        # Never leave a fresh result blank while re-auditing an existing score.
        return (0 if not r.get('ai_review') else 1,
                0 if r.get('repair_version') or r.get('auto_refine_version') else 1 if r['id'] in ranks else 2,
                ranks.get(r['id'],0),r.get('finished_at') or r.get('index',0),r['id'])
    return sorted(pending,key=order)


class LiveJudge:
    def __init__(self,root):
        self.path=Path(root)/'judge-live.json';self.lock=threading.Lock();self.stop=threading.Event()
        self.data={'status':'Loading','started_at':time.time(),'profile':PROFILE}
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()

    def update(self,**values):
        with self.lock:self.data.update(values)

    def _run(self):
        while not self.stop.is_set():
            with self.lock:data={**self.data,'heartbeat_at':time.time()}
            temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(data));temp.replace(self.path)
            self.stop.wait(1)

    def close(self):
        self.stop.set();self.thread.join(timeout=3)


def snapshot(rows,root,now=None):
    """Only publish allowlisted state; stale heartbeats cannot claim active scoring."""
    now=time.time() if now is None else now
    try:live=json.loads((Path(root)/'judge-live.json').read_text())
    except (OSError,ValueError):live={}
    fresh=0<=now-live.get('heartbeat_at',0)<15
    active=next((r for r in rows if r['id']==live.get('row_id') and r.get('output')),None) if fresh else None
    done=[r for r in rows if r.get('output')]
    unscored=[r for r in done if not r.get('ai_review')]
    current=[r for r in done if (r.get('ai_review') or {}).get('rubric')==RUBRIC]
    recent=sorted((r['ai_review'] for r in current if r['ai_review'].get('inference_profile')==PROFILE),key=lambda a:a['created_at'])[-20:]
    score_times=[a.get('total_seconds',a['seconds']) for a in recent]
    renders=sorted((r for r in done if r.get('seconds') and r.get('finished_at')),key=lambda r:r['finished_at'])[-20:]
    render_times=[r['seconds'] for r in renders]
    status=live.get('status','Unavailable') if fresh else 'Offline or reconnecting'
    if status=='Scoring' and not active:status='Updating'
    for row in rows:
        if active and row['id']==active['id'] and status=='Scoring':row['ai_status']='Scoring'
        elif row.get('ai_status')=='Scoring':row['ai_status']='Queued'
    return dict(status=status,profile=live.get('profile'),active_row_id=active['id'] if active else None,
                active_label=(active.get('template','')+' · '+active.get('label','')) if active else None,
                elapsed_seconds=round(max(0,now-live.get('started_at',now))) if fresh else None,
                heartbeat_age=round(max(0,now-live.get('heartbeat_at',0))) if live else None,
                unscored=len(unscored),reaudit_pending=len(done)-len(unscored)-len(current),
                scored=len(done)-len(unscored),whole_pet_scored=len(current),completed_images=len(done),
                recent_score_seconds=round(statistics.median(score_times),1) if score_times else None,
                recent_render_seconds=round(statistics.median(render_times),1) if render_times else None,
                timing_samples=len(score_times),last_completed_at=max((r['ai_review'].get('created_at',0) for r in done if r.get('ai_review')),default=None))
