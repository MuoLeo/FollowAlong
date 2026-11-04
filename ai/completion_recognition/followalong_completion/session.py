"""No ML imports: session isolation, external stage ownership, causal timing."""
from collections import deque, OrderedDict
from dataclasses import dataclass, field
import hashlib, math, re, threading

class ProtocolError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message); self.status=status; self.code=code

def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ProtocolError(422, 'invalid_field', f'{name} must be an integer >= {minimum}')
    return value

def timestamp(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
        raise ProtocolError(422,'invalid_timestamp','captured_at_ms must be finite and >= 0')
    return float(value)

def stage_id(value):
    if value is not None and (type(value) is not int or not 1<=value<=5):
        raise ProtocolError(422,'invalid_stage','stage_id must be 1..5, or null to finish')
    return value

@dataclass
class Session:
    stage: int | None
    # closed is declared below required fields to keep dataclass field order valid.
    version: int
    closed: bool = False
    lock: object = field(default_factory=threading.RLock)
    features: object = field(default_factory=lambda:deque(maxlen=5))
    count: int = 0
    candidate_id: str | None = None
    candidate_frame_id: int | None = None
    candidate_time_ms: float | None = None
    candidate_score: float | None = None
    last_frame_id: int = -1
    last_time_ms: float | None = None
    replies: object = field(default_factory=OrderedDict)

class CompletionSessions:
    def __init__(self, engine, threshold=.5, tolerance_ms=75., max_sessions=32):
        self.engine=engine; self.threshold=float(threshold); self.tolerance=float(tolerance_ms)
        self.max_sessions=max_sessions; self.sessions={}; self.lock=threading.RLock()
        if not 0<=self.threshold<=1 or not 0<=self.tolerance<250:
            raise ValueError('invalid threshold/timing tolerance')

    def _get(self, session_id):
        with self.lock:
            if session_id not in self.sessions:raise ProtocolError(404,'unknown_session','Create/synchronize the session first')
            return self.sessions[session_id]

    def _ensure_open(self,s):
        if s.closed:raise ProtocolError(404,'unknown_session','Session was closed')

    def _base(self, sid, s):
        return dict(session_id=sid,stage_id=s.stage,stage_version=s.version,
                    model_mode=self.engine.mode,verifier_available=False,auto_advance=False)

    def create(self, sid, stage, version):
        if not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',sid):
            raise ProtocolError(422,'invalid_session_id','Use 1..64 ASCII letters/digits/_/-')
        stage=stage_id(stage); version=integer(version,'stage_version',1)
        if stage is None:raise ProtocolError(422,'invalid_stage','Create with stage_id 1..5')
        with self.lock:
            if sid in self.sessions:
                s=self.sessions[sid]
                with s.lock:
                    if (stage,version)!=(s.stage,s.version):raise ProtocolError(409,'session_exists','Use stage update or create a new session ID')
                    return dict(self._base(sid,s),status='session_ready',duplicate=True)
            if len(self.sessions)>=self.max_sessions:raise ProtocolError(503,'session_capacity','Close an unused session')
            s=Session(stage,version); self.sessions[sid]=s
            return dict(self._base(sid,s),status='session_ready',duplicate=False)

    def update_stage(self,sid,stage,version):
        stage=stage_id(stage);version=integer(version,'stage_version',1);s=self._get(sid)
        with s.lock:
            self._ensure_open(s)
            if version==s.version and stage==s.stage:
                return dict(self._base(sid,s),status='stage_synchronized',duplicate=True)
            if version!=s.version+1:
                raise ProtocolError(409,'stage_version_conflict',f'Expected stage_version {s.version+1}; synchronize state first')
            if s.stage is None:raise ProtocolError(409,'session_finished','Create a new session to restart')
            s.stage=stage;s.version=version;s.count=0;s.candidate_id=None
            s.candidate_frame_id=None;s.candidate_time_ms=None;s.candidate_score=None
            # Keep causal history: V4.2 early-stage training includes preceding-stage frames.
            # A later gap in feature timestamps still resets history automatically.
            s.replies.clear()
            return dict(self._base(sid,s),status='session_finished' if stage is None else 'stage_synchronized',duplicate=False)

    def state(self,sid):
        s=self._get(sid)
        with s.lock:
            self._ensure_open(s)
            return dict(self._base(sid,s),status='session_finished' if s.stage is None else
                        'awaiting_stage_event' if s.candidate_id else 'active',candidate_event_id=s.candidate_id,
                        latest_frame_id=s.last_frame_id,last_captured_at_ms=s.last_time_ms)

    def delete(self,sid):
        with self.lock:
            if sid not in self.sessions:raise ProtocolError(404,'unknown_session','No such session')
            # Serialize deletion with in-flight work for this session.
            with self.sessions[sid].lock:
                self.sessions[sid].closed=True
                del self.sessions[sid]
        return dict(session_id=sid,status='session_closed')

    def frame(self,sid,frame_id,captured_at_ms,version,image_bytes):
        fid=integer(frame_id,'frame_id');t=timestamp(captured_at_ms)
        version=integer(version,'stage_version',1)
        if not isinstance(image_bytes,bytes) or not image_bytes:
            raise ProtocolError(422,'invalid_image','Image bytes are required')
        digest=hashlib.sha256(image_bytes).hexdigest(); s=self._get(sid)
        with s.lock:
            self._ensure_open(s)
            if version!=s.version:
                raise ProtocolError(409,'stale_stage_version',f'Current stage_version is {s.version}; resend with synchronized metadata')
            signature=(t,version,digest)
            if fid in s.replies:
                saved_signature,saved=s.replies[fid]
                if signature!=saved_signature:raise ProtocolError(409,'frame_id_reused','Same frame_id has different metadata/image')
                return dict(saved,duplicate=True)
            if fid<=s.last_frame_id or (s.last_time_ms is not None and t<=s.last_time_ms):
                raise ProtocolError(409,'out_of_order_frame','frame_id and captured_at_ms must increase; do not retry a timed-out request with a new ID')
            base=dict(self._base(sid,s),frame_id=fid,captured_at_ms=t,duplicate=False,
                      completion_score=None,candidate_event_id=s.candidate_id,requires_server_stage_event=False)
            if s.stage is None:
                result=dict(base,status='session_finished')
            elif s.candidate_id is not None:
                # No encoder/temporal work while waiting for the server/reviewer.
                result=dict(base,status='awaiting_stage_event',candidate_event_id=s.candidate_id,
                            candidate_frame_id=s.candidate_frame_id,candidate_captured_at_ms=s.candidate_time_ms,
                            candidate_score=s.candidate_score,requires_server_stage_event=True)
            else:
                try:feature=self.engine.encode(image_bytes)
                except ProtocolError:raise
                except (ValueError,OSError) as exc:raise ProtocolError(422,'invalid_image',str(exc)) from exc
                history=list(s.features)
                reset=bool(history and abs(t-history[-1][0]-500.)>self.tolerance)
                if reset:history=[]
                history=(history+[(t,feature)])[-5:]
                if len(history)==5 and abs(history[-1][0]-history[0][0]-2000.)>2*self.tolerance:
                    history=[(t,feature)];reset=True
                count=0 if reset else s.count
                if len(history)<5:
                    result=dict(base,status='warming_up',history_frames=len(history),history_reset=reset)
                else:
                    details={}
                    if hasattr(self.engine,'predict_details'):
                        details=self.engine.predict_details([v for _,v in history],s.stage)
                        probability=float(details['completion_score'])
                    else:probability=float(self.engine.predict([v for _,v in history],s.stage))
                    if not math.isfinite(probability) or not 0<=probability<=1:
                        raise ProtocolError(500,'invalid_model_output','Model returned a non-finite/out-of-range score')
                    gate=details.get('rider_gate_passed',True)
                    if type(gate) is not bool:raise ProtocolError(500,'invalid_model_output','Gate must be boolean')
                    count=count+1 if probability>=self.threshold and gate else 0
                    candidate=count>=getattr(self.engine,'confirmation_count',2)
                    event_id=f'{sid}:{s.version}:{fid}' if candidate else None
                    result=dict(base,status='completion_candidate' if candidate else 'progressing',
                                completion_score=probability,consecutive_positive=count,
                                history_frames=5,history_reset=reset,candidate_event_id=event_id,
                                requires_server_stage_event=candidate)
                    if details:
                        result.update(rider_probability=details.get('rider_probability'),rider_gate_passed=gate,
                                      confirmation_required=getattr(self.engine,'confirmation_count',2),
                                      assembly_error_checked=False)
                    if candidate:
                        s.candidate_id=event_id;s.candidate_frame_id=fid;s.candidate_time_ms=t;s.candidate_score=probability
                s.features=deque(history,maxlen=5);s.count=count
            s.last_frame_id=fid;s.last_time_ms=t
            s.replies[fid]=(signature,dict(result))
            while len(s.replies)>16:s.replies.popitem(last=False)
            return result
