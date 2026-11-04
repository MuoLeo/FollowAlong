"""Development reference review only. Does not train or change the V50 server."""
import argparse,csv,datetime,hashlib,html,json,shutil,uuid,webbrowser
from pathlib import Path

COMPLETIONS={1:25.,2:57.,3:90.,4:127.,5:197.}
OFFSETS=(.5,1.,1.5)

def planned_rows():
    return [dict(recording='fullstage_val_01',stage_id=stage,time_seconds=t+offset,
        role='development_reference_only',label='',review_status='pending',
        evidence='user_supplied_completion_time_plus_offset; visual_review_required',
        notes='',image=f'images/stage{stage}_{int((t+offset)*1000):06d}ms.png')
        for stage,t in COMPLETIONS.items() for offset in OFFSETS]

def select_video():
    import tkinter as tk
    from tkinter.filedialog import askopenfilename
    root=tk.Tk();root.withdraw()
    try:return askopenfilename(title='Choose fullstage_val_01.mp4 (NOT 02)',filetypes=[('MP4','*.mp4')])
    finally:root.destroy()

def write_review(out,rows):
    cards=[]
    for row in rows:
        cards.append('<article><h2>Stage '+str(row['stage_id'])+' / '+str(row['time_seconds'])+'s</h2>'
          +'<a href="'+row['image']+'"><img src="'+row['image']+'"></a>'
          +'<p>검토 전 후보입니다. 손 가림·조립 상태·부품 식별 가능 여부를 확인하세요.</p></article>')
    text='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>완성 모습 후보 검토</title>
    <style>body{font-family:sans-serif;margin:24px;background:#eef2f6;color:#172033}main{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}article{background:white;padding:14px;border-radius:10px}img{width:100%}h2{font-size:18px}p{line-height:1.6}@media(max-width:850px){main{grid-template-columns:1fr}}</style>
    <h1>단계별 완성 모습 후보 15장</h1><p>개발 영상01에서만 추출했습니다. 정상 여부를 자동 확정하거나 학습하지 않았습니다.
    각 사진을 눌러 확대하세요. 완성 형태가 보이는지, 손이 가렸는지, 다음 단계 작업이 시작됐는지 확인해야 합니다.
    사진만으로 판단할 수 없으면 확인 어려움으로 남겨야 합니다.</p><main>'''+''.join(cards)+'</main></html>'
    (out/'review.html').write_text(text,encoding='utf-8')
    with (out/'reference_review.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video');p.add_argument('--no-open',action='store_true');a=p.parse_args()
    selected=a.video or select_video()
    if not selected:raise SystemExit('No video selected. Nothing changed.')
    video=Path(selected)
    if not video.is_file() or video.name!='fullstage_val_01.mp4':
        raise SystemExit('Choose the existing development fullstage_val_01.mp4. Video02 is not used for reference preparation.')
    import cv2
    from PIL import Image,ImageDraw,ImageOps
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise SystemExit('Cannot open video.')
    fps=cap.get(cv2.CAP_PROP_FPS);frames=cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if not fps>0 or not frames>0:cap.release();raise SystemExit('Invalid video metadata.')
    duration=frames/fps;rows=planned_rows()
    if rows[-1]['time_seconds']>=duration:cap.release();raise SystemExit('Video too short for expected supplied timestamps. Nothing labeled.')
    base=Path(__file__).resolve().parent
    out=base/'error_reference_review'/('review_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6])
    (out/'images').mkdir(parents=True,exist_ok=False)
    sheet=Image.new('RGB',(1440,5*315),'white');draw=ImageDraw.Draw(sheet)
    try:
        for i,row in enumerate(rows):
            t=row['time_seconds'];cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,bgr=cap.read()
            if not ok:raise RuntimeError(f'Frame read failed: {t}s. Partial output is not a finished review.')
            im=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));im.save(out/row['image'])
            row['image_sha256']=hashlib.sha256((out/row['image']).read_bytes()).hexdigest()
            tile=ImageOps.contain(im,(470,275));x=i%3*480;y=i//3*315
            sheet.paste(tile,(x+(480-tile.width)//2,y+32));draw.text((x+8,y+8),f"Stage {row['stage_id']} | {t:.1f}s | UNREVIEWED",fill='black')
    finally:cap.release()
    sheet.save(out/'contact_sheet.jpg',quality=93);write_review(out,rows)
    status=dict(purpose='Development reference visual review, NOT a trained error verifier',source_video=str(video),
        source_duration_seconds=duration,source_recording='fullstage_val_01',frames=len(rows),
        all_labels_pending=True,model_trained=False,server_modified=False,
        test_video02_used=False,allowed_future_labels=['correct','incorrect','uncertain'],
        warning='Do not label in-progress frames as incorrect. Multiple images from one recording are correlated. References are not evidence of error-detection accuracy. Video01 has development use and must not become independent test data.')
    (out/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'README_KO.txt').write_text('단계별 정상 완성 모습 후보를 검토하는 자료입니다.\n'
        '학습·서버 수정은 하지 않았습니다. 모든 label은 비어 있고 review_status는 pending입니다.\n'
        '완료 시각 뒤라도 손 가림이나 다음 단계 작업이 있을 수 있으므로 시각 검토가 필요합니다.\n'
        '진행 중 사진이나 다음 단계 사진을 오조립이라고 임의로 라벨링하지 마세요.\n'
        '영상01은 개발 참고용입니다. 오류 학습/독립 평가는 별도 촬영 세션을 분리해야 합니다.\n'
        '최종 오류 모델에는 거의 완성된 실제 오조립과 가림 사례 자료가 필요합니다.\n',encoding='utf-8')
    archive=shutil.make_archive(str(out),'zip',out)
    print('REVIEW ZIP:',Path(archive).resolve(),flush=True)
    print('15 reference candidates extracted. No model trained; no automatic correctness labels.',flush=True)
    if not a.no_open:webbrowser.open((out/'review.html').resolve().as_uri())

if __name__=='__main__':main()
