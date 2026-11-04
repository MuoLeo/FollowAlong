"""Local integration server; external backend owns reviews and stage changes."""
import argparse,time
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from followalong_workflow.server import Handler as WorkflowHandler
from followalong_workflow.session import WorkflowSessions
from followalong_completion.server import MockEngine as OriginalMock

class MockEngine(OriginalMock):
    confirmation_count=3
    def predict_details(self,features,stage):
        return dict(completion_score=.99,rider_probability=.99 if stage==5 else None,rider_gate_passed=True)

class Sessions(WorkflowSessions):
    def _base(self,sid,s):
        return dict(super()._base(sid,s),rider_gate_available=self.engine.mode!='mock',
                    assembly_error_checked=False,confirmation_required=3)
    def frame(self,*args,**kwargs):
        start=time.perf_counter();value=super().frame(*args,**kwargs)
        return dict(value,processing_ms=round((time.perf_counter()-start)*1000,3))

class Handler(WorkflowHandler):
    def _dispatch(self,method):
        if method=='GET' and urlsplit(self.path).path=='/health':
            store=self.server.sessions
            self._send(200,dict(status='ok',workflow_version='v50',model_mode=store.engine.mode,
                auto_advance=False,stage_owner='external_server',error_verifier_available=False,
                rider_gate_available=store.engine.mode!='mock',confirmation_required=3,
                frame_interval_ms=500,history_frames=5,
                provenance=getattr(store.engine,'provenance',{})))
            return
        super()._dispatch(method)

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,sessions):
        self.sessions=sessions;super().__init__(address,Handler)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8767);p.add_argument('--mock',action='store_true')
    p.add_argument('--bundle',default='model_bundle');p.add_argument('--device',default='cpu')
    a=p.parse_args()
    if a.mock:engine=MockEngine()
    else:
        from .model import ModelEngine
        engine=ModelEngine(a.bundle,a.device)
    server=Server(('127.0.0.1',a.port),Sessions(engine,getattr(engine,'threshold',.5)))
    print(f'Listening http://127.0.0.1:{a.port} | model_mode={engine.mode} | N=3 | Stage5 rider gate | NO GENERAL ERROR VERIFIER',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
