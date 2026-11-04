import unittest,threading,json,urllib.request
from followalong_workflow.session import WorkflowSessions
from followalong_workflow.server import Server
from followalong_completion.session import ProtocolError
class Engine:
 mode='mock'
 def __init__(self):self.encodes=0
 def encode(self,x):self.encodes+=1;return x
 def predict(self,x,s):return .99
class FlowTests(unittest.TestCase):
 def setUp(self):self.e=Engine();self.w=WorkflowSessions(self.e);self.w.create('test',3,1)
 def frame(self,n,attempt=1):return self.w.frame('test',n,n*500,1,b'x',attempt)
 def candidate(self):
  for n in range(6):v=self.frame(n)
  return v['candidate_event_id']
 def review(self,verdict='invalid',request='r'):
  c=self.candidate();return self.w.review('test',1,c,verdict,request)
 def assertCode(self,code,fn):
  with self.assertRaises(ProtocolError) as ctx:fn()
  self.assertEqual(ctx.exception.code,code)
 def test_candidate_never_auto_advances(self):
  self.candidate();self.assertEqual(self.w.state('test')['stage_id'],3);self.assertEqual(self.w.state('test')['status'],'awaiting_review')
 def test_repeated_frames_do_not_replay_or_encode(self):
  r=self.review();self.assertEqual(r['action']['type'],'replay_stage_video')
  for n in range(6,30):
   v=self.frame(n);self.assertEqual(v['status'],'correction_wait');self.assertNotIn('action',v)
  self.assertEqual(self.e.encodes,6)
 def test_duplicate_review_same_event(self):
  r=self.review();v=self.w.review('test',1,self.w._get('test').candidate_id,'invalid','r');self.assertTrue(v['duplicate']);self.assertEqual(v['action'],r['action'])
 def test_changed_payload_same_id(self):
  self.review();self.assertCode('request_id_reused',lambda:self.w.review('test',1,self.w._get('test').candidate_id,'valid','r'))
 def test_new_request_cannot_repeat_verdict(self):
  self.review();self.assertCode('stale_review',lambda:self.w.review('test',1,self.w._get('test').candidate_id,'invalid','other'))
 def test_uncertain_does_not_replay(self):
  r=self.review('uncertain');self.assertEqual(r['status'],'needs_clear_view');self.assertIsNone(r['action'])
 def test_valid_waits_for_server(self):
  r=self.review('valid');self.assertEqual(r['status'],'awaiting_stage_event');self.assertEqual(r['stage_id'],3)
 def test_retry_needs_six_fresh_frames(self):
  self.review();r=self.w.retry('test',1,1,2500,'retry');self.assertEqual(r['attempt_id'],2)
  for n in range(6,11):self.assertNotEqual(self.frame(n,2)['status'],'awaiting_review')
  self.assertEqual(self.frame(11,2)['status'],'awaiting_review')
 def test_retry_idempotent(self):
  self.review();self.w.retry('test',1,1,2500,'retry');r=self.w.retry('test',1,1,2500,'retry');self.assertTrue(r['duplicate']);self.assertEqual(r['attempt_id'],2)
 def test_queued_old_attempt(self):
  self.review();self.w.retry('test',1,1,2500,'retry');self.assertCode('stale_attempt',lambda:self.frame(6,1))
 def test_capture_barrier(self):
  self.review();self.w.retry('test',1,1,5000,'retry');self.assertCode('pre_retry_frame',lambda:self.frame(8,2))
 def test_old_review_after_retry(self):
  c=self.candidate();self.w.review('test',1,c,'invalid','r');self.w.retry('test',1,1,2500,'retry');self.assertCode('stale_control',lambda:self.w.review('test',1,c,'invalid','r'))
 def test_stage_invalidates_old_review(self):
  c=self.candidate();self.w.update_stage('test',4,2);self.assertCode('stale_stage_version',lambda:self.w.review('test',1,c,'invalid','r'))
 def test_duplicate_stage_preserves_attempt(self):
  self.review();self.w.retry('test',1,1,2500,'retry');r=self.w.update_stage('test',3,1);self.assertEqual(r['attempt_id'],2)
 def test_session_isolation(self):
  self.review();self.w.create('other',1,1);self.assertEqual(self.w.state('other')['status'],'active')
 def test_deleted_session(self):
  self.w.delete('test');self.assertCode('unknown_session',lambda:self.frame(0))
 def test_concurrent_duplicate_error(self):
  c=self.candidate();results=[]
  def worker():results.append(self.w.review('test',1,c,'invalid','same'))
  ts=[threading.Thread(target=worker) for _ in range(8)]
  for t in ts:t.start()
  for t in ts:t.join()
  self.assertEqual(sum(not r['duplicate'] for r in results),1);self.assertEqual(len({r['action']['event_id'] for r in results}),1)
class HTTPTests(unittest.TestCase):
 def test_http_flow(self):
  server=Server(('127.0.0.1',0),WorkflowSessions(Engine()));t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
  def req(path,body=None):
   r=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(r) as f:return json.load(f)
  try:
   self.assertFalse(req('/health')['error_verifier_available']);req('/sessions',dict(session_id='http',stage_id=1,stage_version=1))
   for n in range(6):v=req('/sessions/http/frames',dict(frame_id=n,captured_at_ms=n*500,stage_version=1,attempt_id=1,image_base64='eA=='))
   v=req('/sessions/http/review',dict(stage_version=1,candidate_event_id=v['candidate_event_id'],verdict='invalid',request_id='r'));self.assertEqual(v['status'],'correction_wait')
   v=req('/sessions/http/retry',dict(stage_version=1,attempt_id=1,captured_after_ms=2500,request_id='t'));self.assertEqual(v['attempt_id'],2)
  finally:server.shutdown();server.server_close();t.join()
if __name__=='__main__':unittest.main()
