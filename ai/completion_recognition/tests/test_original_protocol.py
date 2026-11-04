import base64,json,threading,unittest,urllib.request,urllib.error
from followalong_completion.session import CompletionSessions,ProtocolError
from followalong_completion.server import CompletionHTTPServer,MockEngine

class CountingEngine:
    mode='test'
    def __init__(self):self.encodes=0;self.predicts=[];self.score=.99
    def encode(self,image):
        if image==b'bad':raise ValueError('bad image')
        self.encodes+=1;return image
    def predict(self,features,stage):self.predicts.append(stage);return self.score

class SessionTests(unittest.TestCase):
    def setUp(self):self.e=CountingEngine();self.s=CompletionSessions(self.e);self.s.create('a',1,1)
    def frame(self,i,t=None,v=1):return self.s.frame('a',i,i*500 if t is None else t,v,b'photo')
    def candidate(self):
        for i in range(6):r=self.frame(i)
        return r
    def test_no_gt_stage_and_no_automatic_advance(self):
        r=self.candidate();self.assertEqual(r['status'],'completion_candidate');self.assertEqual(self.s.state('a')['stage_id'],1)
        self.assertEqual(r['candidate_event_id'],'a:1:5');self.assertFalse(r['verifier_available'])
    def test_candidate_latched_encoder_paused(self):
        r=self.candidate();n=self.e.encodes
        for i in range(6,12):
            r2=self.frame(i);self.assertEqual(r2['status'],'awaiting_stage_event');self.assertEqual(r2['candidate_event_id'],r['candidate_event_id'])
        self.assertEqual(self.e.encodes,n)
    def test_external_change_and_new_conditioning(self):
        self.candidate();self.s.update_stage('a',3,2)
        r=self.frame(6,v=2);self.assertEqual(r['consecutive_positive'],1)
        self.assertEqual(self.e.predicts[-1],3);self.assertEqual(self.s.state('a')['stage_id'],3)
    def test_stage_event_retry_does_not_reset(self):
        for i in range(5):self.frame(i)
        self.assertTrue(self.s.update_stage('a',1,1)['duplicate'])
        self.assertEqual(self.frame(5)['status'],'completion_candidate')
    def test_old_frame_version_rejected_before_model(self):
        self.s.update_stage('a',2,2);n=self.e.encodes
        with self.assertRaises(ProtocolError) as c:self.frame(0,v=1)
        self.assertEqual(c.exception.code,'stale_stage_version');self.assertEqual(self.e.encodes,n)
    def test_duplicate_frame_idempotent(self):
        r=self.frame(0);n=self.e.encodes;r2=self.frame(0)
        self.assertTrue(r2['duplicate']);self.assertEqual(r['status'],r2['status']);self.assertEqual(self.e.encodes,n)
    def test_duplicate_frame_changed_bytes_rejected(self):
        self.frame(0)
        with self.assertRaises(ProtocolError):self.s.frame('a',0,0,1,b'changed')
    def test_out_of_order_time_rejected(self):
        self.frame(1)
        with self.assertRaises(ProtocolError):self.frame(2,t=400)
    def test_gap_and_jitter(self):
        for i,t in enumerate([0,503,1006,1498,2002]):self.frame(i,t=t)
        self.assertEqual(self.frame(5,t=2504)['status'],'completion_candidate')
        s=CompletionSessions(self.e);s.create('b',1,1)
        for i in range(5):s.frame('b',i,i*500,1,b'x')
        r=s.frame('b',5,5000,1,b'x');self.assertEqual(r['status'],'warming_up');self.assertTrue(r['history_reset'])
    def test_sessions_do_not_share_history(self):
        self.candidate();self.s.create('b',4,1)
        self.assertEqual(self.s.frame('b',0,0,1,b'x')['status'],'warming_up')
    def test_invalid_image_does_not_consume_frame(self):
        with self.assertRaises(ProtocolError):self.s.frame('a',0,0,1,b'bad')
        self.assertEqual(self.s.state('a')['latest_frame_id'],-1)
        self.frame(0)
    def test_invalid_numeric_values(self):
        for t in [float('nan'),float('inf'),True,-1]:
            with self.assertRaises(ProtocolError):self.frame(0,t=t)
    def test_server_can_finish(self):
        self.s.update_stage('a',None,2)
        self.assertEqual(self.frame(0,v=2)['status'],'session_finished')
        with self.assertRaises(ProtocolError):self.s.update_stage('a',1,3)
    def test_score_low_is_progressing_not_assembly_error(self):
        self.e.score=.01
        for i in range(6):r=self.frame(i)
        self.assertEqual(r['status'],'progressing');self.assertFalse(r['requires_server_stage_event'])
    def test_inflight_frame_cannot_revive_closed_session(self):
        session=self.s._get('a');retrieved=threading.Event();errors=[]
        original_get=self.s._get
        def get(sid):
            value=original_get(sid);retrieved.set();return value
        self.s._get=get
        def worker():
            try:self.frame(0)
            except ProtocolError as exc:errors.append(exc.code)
        with session.lock:
            thread=threading.Thread(target=worker);thread.start()
            self.assertTrue(retrieved.wait(2));self.s.delete('a')
        thread.join(2)
        self.assertEqual(errors,['unknown_session']);self.assertEqual(self.e.encodes,0)

    def test_version_must_be_next_or_identical_retry(self):
        with self.assertRaises(ProtocolError):self.s.update_stage('a',2,3)
        with self.assertRaises(ProtocolError):self.s.update_stage('a',2,1)

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=CompletionHTTPServer(('127.0.0.1',0),CompletionSessions(MockEngine()))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_address[1])
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,method,path,obj=None):
        data=None if obj is None else json.dumps(obj).encode();req=urllib.request.Request(self.url+path,data=data,method=method,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    def test_end_to_end_mock_protocol(self):
        self.assertEqual(self.request('GET','/health')[1]['model_mode'],'mock')
        self.assertEqual(self.request('POST','/sessions',dict(session_id='http',stage_id=1,stage_version=1))[0],200)
        for i in range(6):status,r=self.request('POST','/sessions/http/frames',dict(frame_id=i,captured_at_ms=i*500,stage_version=1,image_base64=base64.b64encode(b'x').decode()))
        self.assertEqual(status,200);self.assertEqual(r['status'],'completion_candidate')
        self.assertEqual(self.request('GET','/sessions/http')[1]['stage_id'],1)
        self.request('POST','/sessions/http/stage',dict(stage_id=2,stage_version=2))
        self.assertEqual(self.request('GET','/sessions/http')[1]['stage_id'],2)
        self.assertEqual(self.request('DELETE','/sessions/http')[0],200)
    def test_invalid_base64_and_missing_fields(self):
        self.request('POST','/sessions',dict(session_id='bad',stage_id=1,stage_version=1))
        self.assertEqual(self.request('POST','/sessions/bad/frames',dict(frame_id=0,captured_at_ms=0,stage_version=1,image_base64='!'))[0],422)
        self.assertEqual(self.request('POST','/sessions',{})[0],422)
        self.request('DELETE','/sessions/bad')

if __name__=='__main__':unittest.main(verbosity=2)
