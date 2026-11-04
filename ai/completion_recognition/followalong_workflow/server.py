"""V4.6 workflow server. Review is an external/manual verdict, never an AI verdict."""
import argparse,base64,binascii,time,traceback
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from followalong_completion.server import Handler as BaseHandler,MockEngine
from followalong_completion.session import ProtocolError
from .session import WorkflowSessions

class Handler(BaseHandler):
    def _dispatch(self,method):
        try:
            self.connection.settimeout(15)
            parts=[p for p in urlsplit(self.path).path.split('/') if p]
            store=self.server.sessions
            if method=='GET' and parts in ([],['demo']):
                if store.engine.mode!='mock':raise ProtocolError(403,'mock_only','Demo buttons send fake frames. Use mock mode.')
                data=Path(__file__).with_name('demo.html').read_bytes()
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if method=='GET' and parts==['health']:
                self._send(200,dict(status='ok',workflow_version='v46',model_mode=store.engine.mode,
                    error_verifier_available=False,review_source='external_backend_or_manual',auto_advance=False));return
            if len(parts)==3 and parts[0]=='sessions' and method=='POST':
                sid=parts[1];b=self._body()
                if parts[2]=='review':
                    v=store.review(sid,b['stage_version'],b['candidate_event_id'],b['verdict'],b['request_id'])
                elif parts[2]=='retry':
                    v=store.retry(sid,b['stage_version'],b['attempt_id'],b['captured_after_ms'],b['request_id'])
                elif parts[2]=='frames':
                    if not isinstance(b['image_base64'],str):raise ProtocolError(422,'invalid_image','Expected base64 string')
                    try:raw=base64.b64decode(b['image_base64'],validate=True)
                    except (ValueError,binascii.Error):raise ProtocolError(422,'invalid_image','Malformed base64')
                    v=store.frame(sid,b['frame_id'],b['captured_at_ms'],b['stage_version'],raw,b['attempt_id'])
                elif parts[2]=='stage':v=store.update_stage(sid,b['stage_id'],b['stage_version'])
                else:raise ProtocolError(404,'unknown_endpoint','Unknown endpoint')
                self._send(200,v);return
        except KeyError as exc:self._send(422,dict(error='missing_field',message=str(exc)));return
        except ProtocolError as exc:self._send(exc.status,dict(error=exc.code,message=str(exc)));return
        except Exception:
            traceback.print_exc();self._send(500,dict(error='internal_error',message='See server console'));return
        # Original creation/state/deletion routes retain original validation.
        super()._dispatch(method)

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,sessions):self.sessions=sessions;super().__init__(address,Handler)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8766)
    p.add_argument('--mock',action='store_true');p.add_argument('--bundle');p.add_argument('--device',default='cpu')
    a=p.parse_args()
    if a.mock:engine=MockEngine()
    else:
        if not a.bundle:p.error('Supply --mock for workflow tests, or --bundle for the existing real completion model')
        from followalong_completion.model import ModelEngine
        engine=ModelEngine(a.bundle,a.device)
    server=Server(('127.0.0.1',a.port),WorkflowSessions(engine,getattr(engine,'threshold',.5)))
    print(f'Listening http://127.0.0.1:{a.port}/demo | completion={engine.mode} | NO ERROR VERIFIER | external stage owner',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
