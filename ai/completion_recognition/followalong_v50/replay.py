"""Replay local video to real HTTP server. Explicit simulated approval is diagnostic only."""
import argparse,base64,csv,datetime,json,math,platform,shutil,time,uuid,urllib.request,urllib.error,zipfile
from pathlib import Path

def request(base,method,path,body=None):
    raw=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(base+path,data=raw,method=method,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode()}') from e

def choose_video():
    import tkinter as tk
    from tkinter.filedialog import askopenfilename
    root=tk.Tk();root.withdraw()
    try:return askopenfilename(title='Choose fullstage_val_02.mp4',filetypes=[('MP4 video','*.mp4'),('All files','*.*')])
    finally:root.destroy()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video')
    p.add_argument('--base-url',default='http://127.0.0.1:8767')
    p.add_argument('--simulate-external-approval',action='store_true',help='Simulate valid review + server stage ACK; does not test assembly correctness')
    p.add_argument('--paced',action='store_true',help='Wait for 0.5s camera schedule; overdue frames remain queued for this diagnostic')
    a=p.parse_args();health=request(a.base_url,'GET','/health')
    if health.get('model_mode')!='real_v50':raise RuntimeError('Start the real V50 server first; mock is not a model test')
    if health.get('confirmation_required')!=3:raise RuntimeError('Wrong server policy')
    path=Path(a.video or choose_video())
    if not path.is_file():raise SystemExit('No video selected. Nothing was tested.')
    import cv2
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened():raise RuntimeError('Cannot open video')
    fps=cap.get(cv2.CAP_PROP_FPS);frames=cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if not fps>0 or not frames>0:cap.release();raise RuntimeError('Invalid video metadata')
    duration=frames/fps
    out=Path('results')/('v50_api_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6])
    out.mkdir(parents=True,exist_ok=False)
    sid='replay_'+uuid.uuid4().hex[:12];stage=1;version=1;created=False;rows=[];events=[];error=None
    wall_start=time.perf_counter()
    print('Video:',path,flush=True)
    print('Simulated external approval:',a.simulate_external_approval,'(NOT an error-verifier test)',flush=True)
    try:
        request(a.base_url,'POST','/sessions',dict(session_id=sid,stage_id=stage,stage_version=version));created=True
        for i in range(math.ceil(duration/.5)):
            t=round(i*.5,3)
            if t>=duration-.1:break
            if a.paced:time.sleep(max(0.,wall_start+t-time.perf_counter()))
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,frame=cap.read()
            if not ok:raise RuntimeError(f'Video read failed at {t}s')
            ok,encoded=cv2.imencode('.png',frame)
            if not ok:raise RuntimeError('PNG encoding failed')
            # Lossless PNG preserves decoded pixels used by the offline notebook.
            body=dict(frame_id=i,captured_at_ms=t*1000,stage_version=version,attempt_id=1,
                      image_base64=base64.b64encode(encoded.tobytes()).decode('ascii'))
            start=time.perf_counter();value=request(a.base_url,'POST',f'/sessions/{sid}/frames',body)
            rows.append({**value,'frame_id':i,'captured_at_seconds':t,'roundtrip_ms':(time.perf_counter()-start)*1000})
            if i%20==0:print(f'{t:.1f}s | Stage{stage} | {value["status"]} | score={value.get("completion_score")}',flush=True)
            if value['status']=='awaiting_review':
                events.append(dict(stage=stage,confirmation_seconds=t,candidate_event_id=value['candidate_event_id']))
                print(f'Candidate Stage{stage}: {t:.1f}s',flush=True)
                if not a.simulate_external_approval:
                    print('Stopped: external/manual review required. No stage was changed.',flush=True);break
                review=request(a.base_url,'POST',f'/sessions/{sid}/review',dict(stage_version=version,
                    candidate_event_id=value['candidate_event_id'],verdict='valid',request_id=f'review_{stage}'))
                if review['status']!='awaiting_stage_event':raise RuntimeError('Unexpected review response')
                next_stage=stage+1 if stage<5 else None;version+=1
                request(a.base_url,'POST',f'/sessions/{sid}/stage',dict(stage_id=next_stage,stage_version=version))
                stage=next_stage
                if stage is None:break
    except Exception as exc:
        error=f'{type(exc).__name__}: {exc}';print(error,flush=True)
    finally:
        cap.release()
        if created:
            try:request(a.base_url,'DELETE',f'/sessions/{sid}')
            except Exception:pass
        summary=dict(video=str(path),session_id=sid,health=health,events=events,error=error,
            all_five_candidates=len(events)==5,simulated_external_approval=a.simulate_external_approval,
            actual_error_verifier_tested=False,live_camera_tested=False,paced=a.paced,
            offline_wall_seconds=time.perf_counter()-wall_start,python=platform.python_version(),opencv=cv2.__version__,
            note='Integration replay of an already evaluated video; not a new independent test. Temporal/rider scores are not assembly progress percentages.')
        if path.name=='fullstage_val_02.mp4':
            gt={1:24.,2:50.,3:77.,4:107.,5:167.}
            for event in events:event['delay_seconds']=event['confirmation_seconds']-gt[event['stage']]
            summary['premature_candidates']=sum(event['delay_seconds']<0 for event in events)
        (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        if rows:
            fields=list(dict.fromkeys(k for row in rows for k in row))
            with (out/'frames.csv').open('w',newline='',encoding='utf-8-sig') as f:
                writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        archive=shutil.make_archive(str(out),'zip',out)
        print('RESULT ZIP:',Path(archive).resolve(),flush=True)
        print('Candidates:',[(e['stage'],e['confirmation_seconds']) for e in events],flush=True)
    if error:raise SystemExit(1)
if __name__=='__main__':main()
