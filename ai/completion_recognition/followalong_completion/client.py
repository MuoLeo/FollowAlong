"""Small stdlib client for server teammate or local camera demo."""
import base64,json,urllib.request,urllib.error
class Client:
    def __init__(self,url='http://127.0.0.1:8765'):self.url=url.rstrip('/')
    def request(self,method,path,value=None):
        payload=None if value is None else json.dumps(value).encode('utf-8')
        req=urllib.request.Request(self.url+path,data=payload,method=method,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=30) as resp:return json.load(resp)
        except urllib.error.HTTPError as exc:
            body=exc.read().decode('utf-8');raise RuntimeError(f'HTTP {exc.code}: {body}') from exc
    def create(self,sid,stage=1,version=1):return self.request('POST','/sessions',dict(session_id=sid,stage_id=stage,stage_version=version))
    def stage(self,sid,stage,version):return self.request('POST',f'/sessions/{sid}/stage',dict(stage_id=stage,stage_version=version))
    def frame(self,sid,fid,t,version,image):return self.request('POST',f'/sessions/{sid}/frames',dict(frame_id=fid,captured_at_ms=t,stage_version=version,image_base64=base64.b64encode(image).decode('ascii')))
