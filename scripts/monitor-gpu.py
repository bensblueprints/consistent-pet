"""Aggregate GPU telemetry only: no process arguments, prompts or input images."""
import json
import subprocess
import time
from portrait_reviews import ROOT

ROOT.mkdir(parents=True,exist_ok=True)
samples=[]
while True:
    try:
        line=subprocess.check_output(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw','--format=csv,noheader,nounits'],timeout=8,text=True).splitlines()[0]
        values=line.split(',')
        data=dict(name=values[0].strip(),**{k:float(v) for k,v in zip(('utilization','memory_used_mib','memory_total_mib','temperature','power_w'),values[1:])},sampled_at=time.time())
        samples.append(dict(time=data['sampled_at'],utilization=data['utilization']));samples=samples[-120:]
        data['samples']=samples
    except Exception as error:
        data=dict(error=type(error).__name__,sampled_at=time.time())
    temp=ROOT/'gpu-status.tmp';temp.write_text(json.dumps(data));temp.replace(ROOT/'gpu-status.json')
    time.sleep(2)
