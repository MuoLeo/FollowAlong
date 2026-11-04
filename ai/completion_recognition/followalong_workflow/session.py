from collections import OrderedDict
from followalong_completion.session import CompletionSessions,ProtocolError,integer,timestamp

class WorkflowSessions(CompletionSessions):
    def _flow(self,s):
        if not hasattr(s,'phase'):
            s.phase='active';s.attempt=1;s.after_ms=-1.;s.controls=OrderedDict();s.video_event=None
    def _base(self,sid,s):
        self._flow(s)
        return dict(super()._base(sid,s),workflow_phase=s.phase,attempt_id=s.attempt,
                    captured_after_ms=s.after_ms,error_verifier_available=False)
    def _version(self,s,version):
        self._ensure_open(s);integer(version,'stage_version',1)
        if version!=s.version:raise ProtocolError(409,'stale_stage_version','Synchronize current stage first')
    def _control(self,s,request_id,signature):
        if not isinstance(request_id,str) or not 1<=len(request_id)<=128:
            raise ProtocolError(422,'invalid_request_id','request_id must be 1..128 characters')
        if request_id in s.controls:
            sig,result=s.controls[request_id]
            if sig!=signature:raise ProtocolError(409,'request_id_reused','Request ID payload changed')
            if result.get('attempt_id')!=s.attempt:raise ProtocolError(409,'stale_control','This control belongs to a previous attempt')
            return dict(result,duplicate=True)
    def _save(self,s,key,sig,result):
        s.controls[key]=(sig,dict(result))
        while len(s.controls)>128:s.controls.popitem(last=False)
        return result
    def state(self,sid):
        s=self._get(sid)
        with s.lock:
            value=super().state(sid)
            return dict(value,status=s.phase,video_replay_event_id=s.video_event)
    def frame(self,sid,frame_id,captured_at_ms,version,image_bytes,attempt_id):
        s=self._get(sid)
        with s.lock:
            self._flow(s);self._version(s,version)
            integer(attempt_id,'attempt_id',1)
            if attempt_id!=s.attempt:raise ProtocolError(409,'stale_attempt','Discard queued frames and use current attempt_id')
            if timestamp(captured_at_ms)<=s.after_ms:
                raise ProtocolError(409,'pre_retry_frame','Frame was captured before the recheck barrier')
            value=super().frame(sid,frame_id,captured_at_ms,version,image_bytes)
            if value['status']=='completion_candidate' and s.phase=='active':s.phase='awaiting_review'
            if value['status'] in ('completion_candidate','awaiting_stage_event'):
                value=dict(value,status=s.phase,workflow_phase=s.phase,
                           requires_review=s.phase=='awaiting_review',
                           requires_server_stage_event=s.phase=='awaiting_stage_event')
            # Frames and polling never emit a video replay instruction.
            return value
    def review(self,sid,version,candidate_event_id,verdict,request_id):
        s=self._get(sid)
        with s.lock:
            self._flow(s);self._version(s,version)
            if verdict not in ('valid','invalid','uncertain'):
                raise ProtocolError(422,'invalid_verdict','Use valid, invalid, or uncertain')
            if not isinstance(candidate_event_id,str):raise ProtocolError(422,'invalid_candidate','candidate_event_id required')
            sig=('review',version,candidate_event_id,verdict)
            saved=self._control(s,request_id,sig)
            if saved:return saved
            if s.phase!='awaiting_review' or candidate_event_id!=s.candidate_id:
                raise ProtocolError(409,'stale_review','Review must match the current pending candidate')
            s.phase={'valid':'awaiting_stage_event','invalid':'correction_wait','uncertain':'needs_clear_view'}[verdict]
            action=None
            if verdict=='invalid':
                s.video_event=f'replay:{candidate_event_id}'
                action=dict(type='replay_stage_video',event_id=s.video_event,stage_id=s.stage,
                            stage_version=s.version,attempt_id=s.attempt)
            value=dict(self._base(sid,s),status=s.phase,duplicate=False,action=action,
                       review_source='external_backend_or_manual',requires_server_stage_event=verdict=='valid')
            return self._save(s,request_id,sig,value)
    def retry(self,sid,version,attempt_id,captured_after_ms,request_id):
        s=self._get(sid)
        with s.lock:
            self._flow(s);self._version(s,version)
            integer(attempt_id,'attempt_id',1);barrier=timestamp(captured_after_ms)
            sig=('retry',version,attempt_id,barrier)
            saved=self._control(s,request_id,sig)
            if saved:return saved
            if attempt_id!=s.attempt:raise ProtocolError(409,'stale_attempt','Use the current attempt_id')
            if s.phase not in ('active','correction_wait','needs_clear_view'):
                raise ProtocolError(409,'wrong_phase','Wait for review or server stage update')
            if s.stage is None:raise ProtocolError(409,'session_finished','Session already ended')
            s.after_ms=max(barrier,s.last_time_ms if s.last_time_ms is not None else -1.)
            s.attempt+=1;s.phase='active';s.features.clear();s.count=0;s.replies.clear()
            s.candidate_id=None;s.candidate_frame_id=None;s.candidate_time_ms=None;s.candidate_score=None;s.video_event=None
            value=dict(self._base(sid,s),status='recheck_started',duplicate=False,action=None,history_frames=0)
            return self._save(s,request_id,sig,value)
    def update_stage(self,sid,stage,version):
        s=self._get(sid)
        with s.lock:
            value=super().update_stage(sid,stage,version);self._flow(s)
            if not value['duplicate']:
                s.phase='finished' if stage is None else 'active';s.attempt=1;s.controls.clear();s.video_event=None
            return dict(value,**{k:v for k,v in self._base(sid,s).items() if k in ('workflow_phase','attempt_id')})
