"""Optional native ComfyUI websocket progress for the private comparison board."""
import io,json,threading,time
from pathlib import Path
from PIL import Image

class ComfyProgress:
 def __init__(self,api,job,root):
  if Path(job).name!=job:raise ValueError('Invalid job name')
  self.api,self.job,self.root=api,job,Path(root);self.ws=None;self.stopped=threading.Event();self.data={}
 def start(self):
  try:
   import websocket
   self.ws=websocket.create_connection(self.api.replace('https://','wss://').replace('http://','ws://')+'/ws?clientId='+self.job,timeout=5)
   self.ws.settimeout(1)
   self.data.update(progress_connection='connected');self._save()
   threading.Thread(target=self._read,daemon=True).start()
  except Exception as error:
   self.ws=None
   self.data.update(progress_connection='unavailable',progress_error=type(error).__name__);self._save()
 def _save(self):
  folder=self.root/'progress';folder.mkdir(exist_ok=True);temp=folder/(self.job+'.tmp')
  temp.write_text(json.dumps(self.data));temp.replace(folder/(self.job+'.json'))
 def _read(self):
  import websocket
  while not self.stopped.is_set():
   try:
    message=self.ws.recv()
    if isinstance(message,str):
     event=json.loads(message)
     if event.get('type')=='progress':
      self.data.update(progress_value=event['data']['value'],progress_max=event['data']['max']);self._save()
    elif isinstance(message,bytes):
     # Official ComfyUI websocket example specifies an eight-byte preview header.
     try:
      preview=Image.open(io.BytesIO(message[8:])).convert('RGB');preview.thumbnail((832,1040))
      name=self.job+'-preview.jpg';temp=self.root/'media'/(name+'.tmp')
      preview.save(temp,format='JPEG',quality=85);temp.replace(self.root/'media'/name)
      self.data.update(preview=name,progress_seq=time.time());self._save()
     except (OSError,ValueError):pass
   except websocket.WebSocketTimeoutException:continue
   except Exception:break
 def close(self):
  self.stopped.set()
  if self.ws:
   try:self.ws.close()
   except Exception:pass
