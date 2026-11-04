import csv,io,json,threading,unittest,urllib.request
from pathlib import Path
from followalong_v50.server import Sessions,Server,MockEngine
from followalong_completion.session import ProtocolError

class GateEngine:
    mode='fixture';confirmation_count=3
    def __init__(self):self.allowed=False;self.calls=0
    def encode(self,b):self.calls+=1;return b
    def predict_details(self,features,stage):
        return dict(completion_score=.99,rider_probability=.9 if self.allowed else .1,
                    rider_gate_passed=stage!=5 or self.allowed)

class V50Tests(unittest.TestCase):
    def frame(self,store,n,version=1,attempt=1):
        return store.frame('test',n,n*500,version,b'x',attempt)
    def test_three_confirmations(self):
        w=Sessions(GateEngine());w.create('test',1,1)
        for n in range(6):self.assertNotEqual(self.frame(w,n)['status'],'awaiting_review')
        value=self.frame(w,6)
        self.assertEqual(value['status'],'awaiting_review');self.assertEqual(value['consecutive_positive'],3)
        self.assertEqual(value['stage_id'],1);self.assertFalse(value['auto_advance'])
    def test_gate_blocks_stage5_and_low_score_is_not_error(self):
        e=GateEngine();w=Sessions(e);w.create('test',5,1)
        for n in range(15):
            v=self.frame(w,n);self.assertNotEqual(v['status'],'awaiting_review')
        self.assertEqual(v['consecutive_positive'],0);self.assertFalse(v['assembly_error_checked'])
        self.assertFalse(v['rider_gate_passed']);e.allowed=True
        self.assertEqual(self.frame(w,15)['consecutive_positive'],1)
        self.assertEqual(self.frame(w,16)['consecutive_positive'],2)
        self.assertEqual(self.frame(w,17)['status'],'awaiting_review')
    def test_invalid_replays_once_then_retry_needs_seven_fresh_frames(self):
        e=GateEngine();w=Sessions(e);w.create('test',3,1)
        for n in range(7):v=self.frame(w,n)
        c=v['candidate_event_id'];r=w.review('test',1,c,'invalid','bad')
        self.assertEqual(r['action']['type'],'replay_stage_video')
        for n in range(7,20):
            v=self.frame(w,n);self.assertEqual(v['status'],'correction_wait');self.assertNotIn('action',v)
        self.assertEqual(e.calls,7)
        w.retry('test',1,1,9500,'retry')
        with self.assertRaises(ProtocolError):self.frame(w,20,attempt=1)
        for n in range(20,26):self.assertNotEqual(self.frame(w,n,attempt=2)['status'],'awaiting_review')
        self.assertEqual(self.frame(w,26,attempt=2)['status'],'awaiting_review')
    def test_stage_transition_preserves_history_and_resets_count(self):
        w=Sessions(GateEngine());w.create('test',3,1)
        for n in range(7):v=self.frame(w,n)
        w.review('test',1,v['candidate_event_id'],'valid','ok');w.update_stage('test',4,2)
        self.assertEqual(len(w._get('test').features),5)
        self.assertEqual(self.frame(w,7,2)['consecutive_positive'],1)
        self.assertEqual(self.frame(w,8,2)['consecutive_positive'],2)
        self.assertEqual(self.frame(w,9,2)['status'],'awaiting_review')
    def test_saved_test_scores_reproduce_through_workflow(self):
        path=Path(__file__).resolve().parents[1]/'evaluation/fullstage_val_02_all_stage_scores.csv'
        with path.open() as f:scores={float(r['time']):r for r in csv.DictReader(f)}
        class RecordedEngine:
            mode='recorded_scores';confirmation_count=3
            def encode(self,b):return float(b)
            def predict_details(self,features,stage):
                row=scores[features[-1]];rider=float(row['rider_probability'])
                return dict(completion_score=float(row[f'p_stage{stage}']),rider_probability=rider,
                            rider_gate_passed=stage!=5 or rider>=.5)
        w=Sessions(RecordedEngine());w.create('test',1,1);version=1;found=[]
        for i in range(346):
            t=i*.5;v=w.frame('test',i,t*1000,version,str(t).encode(),1)
            if v['status']=='awaiting_review':
                stage=v['stage_id'];found.append((stage,t));self.assertFalse(v['auto_advance'])
                w.review('test',version,v['candidate_event_id'],'valid',f'r{stage}')
                version+=1;w.update_stage('test',stage+1 if stage<5 else None,version)
                if stage==5:break
        self.assertEqual(found,[(1,25.5),(2,50.),(3,78.5),(4,108.5),(5,168.5)])
    def test_http_v50_policy(self):
        server=Server(('127.0.0.1',0),Sessions(MockEngine()))
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        def req(method,path,body=None):
            request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+path,method=method,
                data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request) as f:return json.load(f)
        try:
            self.assertEqual(req('GET','/health')['confirmation_required'],3)
            req('POST','/sessions',dict(session_id='test',stage_id=1,stage_version=1))
            for n in range(7):
                v=req('POST','/sessions/test/frames',dict(frame_id=n,captured_at_ms=n*500,stage_version=1,attempt_id=1,image_base64='eA=='))
                self.assertEqual(v['status']=='awaiting_review',n==6)
            self.assertFalse(v['auto_advance'])
        finally:server.shutdown();server.server_close();worker.join()

if __name__=='__main__':unittest.main()
