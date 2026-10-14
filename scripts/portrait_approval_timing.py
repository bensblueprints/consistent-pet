"""Approval cadence from saved accepted reports; no changes to generation policy."""
import json,time,threading
from datetime import datetime
from pathlib import Path
_lock=threading.Lock()
_cache={}
def _snapshot(root,repo=Path('/workspace/consistent-pet'),now=None):
 now=time.time() if now is None else now
 with _lock:
  if now-_cache.get('at',0)<10:return _cache['value']
  progress=json.loads((root/'catalog-public-status.json').read_text())
  version=progress['version']
  queue=json.loads((root/'catalog-refinement'/version/'queue.json').read_text())
  events=[]
  for key,item in queue['items'].items():
   if item['status']!='accepted' or not item.get('run','').startswith(version+'-'):continue
   p=repo/'workflows/portraits'/key/'status.json'
   try:
    report=json.loads(p.read_text())
    stamp=datetime.fromisoformat(report['last_updated_utc'].replace('Z','+00:00')).timestamp()
    events.append(dict(reference=key,approved_at=stamp,generations=item.get('generations',0)))
   except (OSError,ValueError,KeyError):continue
  events.sort(key=lambda e:e['approved_at'])
  for previous,event in zip(events,events[1:]):event['seconds_since_previous_approval']=event['approved_at']-previous['approved_at']
  intervals=[e['seconds_since_previous_approval'] for e in events[1:] if e['seconds_since_previous_approval']>0][-10:]
  remaining=progress['total']-progress['counts'].get('accepted',0)
  elapsed=max(0,now-events[-1]['approved_at']) if events else None
  mean=sum(intervals)/len(intervals) if intervals else None
  # Account for a long current retry cycle instead of leaving a frozen optimistic ETA.
  effective=max(mean,elapsed) if mean is not None else None
  seconds=max(0,remaining*effective-elapsed) if effective is not None and remaining else (0 if not remaining else None)
  value=dict(measured_at=now,version=version,approvals=len(events),samples=len(intervals),remaining=remaining,
    mean_seconds=mean,last_seconds=intervals[-1] if intervals else None,current_elapsed_seconds=elapsed,
    remaining_seconds=seconds,estimated_finish=now+seconds if seconds is not None else None,
    submission_deadline=progress.get('submission_deadline'),recent_approvals=events[-10:],
    basis='Last 10 approval-to-approval intervals in the current five-dog queue, including planning, scoring and retries. Assumes continuous operation; not a guarantee.')
  target=root/'approval-timing.json';temporary=target.with_suffix('.tmp')
  temporary.write_text(json.dumps(dict(summary=value,events=events),indent=2));temporary.replace(target)
  _cache.update(at=now,value=value)
  return value

def snapshot(root,repo=Path('/workspace/consistent-pet'),now=None):
 try:return _snapshot(root,repo,now)
 except (OSError,ValueError,KeyError):return dict(error='Approval timing temporarily unavailable')
