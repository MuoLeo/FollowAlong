"""Local development HTTP adapter. Standard library transport, one process."""
import argparse,base64,binascii,json,sys,time,traceback
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from .session import CompletionSessions,ProtocolError
MAX_BODY=8*1024*1024

class MockEngine:
    mode='mock'
    def encode(self,image_bytes):return image_bytes
    def predict(self,features,stage):return .99

class CompletionHTTPServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,sessions):self.sessions=sessions;super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def _send(self,status,value):
        data=json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def _body(self):
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ProtocolError(400,'invalid_length','Content-Length is required')
        if not 0<length<=MAX_BODY:raise ProtocolError(413,'body_size','JSON body must be 1 byte..8 MiB')
        if self.headers.get_content_type()!='application/json':raise ProtocolError(415,'content_type','Use application/json')
        try:value=json.loads(self.rfile.read(length))
        except (ValueError,UnicodeDecodeError):raise ProtocolError(400,'invalid_json','Malformed JSON')
        if not isinstance(value,dict):raise ProtocolError(422,'invalid_json','Expected an object')
        return value
    def _dispatch(self,method):
        start=time.perf_counter()
        try:
            self.connection.settimeout(15)
            parts=[p for p in urlsplit(self.path).path.split('/') if p]
            store=self.server.sessions
            if method=='GET' and parts==['health']:
                value=dict(status='ok',model_mode=store.engine.mode,threshold=store.threshold,
                           verifier_available=False,stage_owner='external_server',frame_interval_ms=500,
                           timing_tolerance_ms=store.tolerance,auto_advance=False)
            elif method=='POST' and parts==['sessions']:
                b=self._body();value=store.create(b['session_id'],b['stage_id'],b['stage_version'])
            elif len(parts)==2 and parts[0]=='sessions' and method=='GET':value=store.state(parts[1])
            elif len(parts)==2 and parts[0]=='sessions' and method=='DELETE':value=store.delete(parts[1])
            elif len(parts)==3 and parts[0]=='sessions' and parts[2]=='stage' and method=='POST':
                b=self._body();value=store.update_stage(parts[1],b['stage_id'],b['stage_version'])
            elif len(parts)==3 and parts[0]=='sessions' and parts[2]=='frames' and method=='POST':
                b=self._body();encoded=b['image_base64']
                if not isinstance(encoded,str):raise ProtocolError(422,'invalid_image','image_base64 must be a string')
                try:image=base64.b64decode(encoded,validate=True)
                except (binascii.Error,ValueError):raise ProtocolError(422,'invalid_image','Invalid base64')
                value=store.frame(parts[1],b['frame_id'],b['captured_at_ms'],b['stage_version'],image)
            else:raise ProtocolError(404,'unknown_endpoint','Unknown endpoint')
            self._send(200,dict(value,processing_ms=round((time.perf_counter()-start)*1000,3)))
        except KeyError as exc:self._send(422,dict(error='missing_field',message=f'Missing {exc}'))
        except ProtocolError as exc:self._send(exc.status,dict(error=exc.code,message=str(exc)))
        except Exception:
            traceback.print_exc(file=sys.stderr);self._send(500,dict(error='internal_error',message='See AI server console; no stage change was requested'))
    def do_GET(self):self._dispatch('GET')
    def do_POST(self):self._dispatch('POST')
    def do_DELETE(self):self._dispatch('DELETE')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--bundle',default='model_bundle');parser.add_argument('--device',default=None)
    parser.add_argument('--mock',action='store_true',help='Protocol demo only; simulated scores, no AI')
    args=parser.parse_args()
    if args.mock:engine=MockEngine();threshold=.5
    else:
        from .model import ModelEngine
        engine=ModelEngine(args.bundle,args.device);threshold=engine.threshold
    server=CompletionHTTPServer((args.host,args.port),CompletionSessions(engine,threshold))
    print(f'Listening http://{args.host}:{args.port} | model_mode={engine.mode} | external stage owner | no error verifier',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
