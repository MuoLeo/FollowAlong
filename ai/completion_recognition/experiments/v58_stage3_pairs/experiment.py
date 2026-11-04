"""V58 paired Stage3 data: frozen encoder, fixed classifier, offline comparison."""
import argparse,csv,hashlib,json,zipfile
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from v55_support import choose_encoder,load_encoder_bytes,evaluate,ENCODER_SHA
from encode_support import encode_new
ROOT=Path(__file__).resolve().parent

def train_predict(rows,x,query_rows,query_x):
 # Same V56 preprocessing, weights and classifier; no threshold fitting.
 y=np.array([r['error'] for r in rows]);g=np.array([r['group'] for r in rows]);stage=np.array([r['stage'] for r in rows]);qs=np.array([r['stage'] for r in query_rows])
 assert set(g).isdisjoint({r['group'] for r in query_rows})
 features=np.c_[x,np.eye(5)[stage-1]];q=np.c_[query_x,np.eye(5)[qs-1]]
 scaler=StandardScaler().fit(features);sizes={a:sum(g==a) for a in set(g)}
 model=LogisticRegression(C=.1,class_weight='balanced',max_iter=3000,random_state=42)
 model.fit(scaler.transform(features),y,sample_weight=np.array([1/sizes[a] for a in g]))
 return model.predict_proba(scaler.transform(q))[:,1]

def counts(rows,scores):
 y=np.array([r['error'] for r in rows]);p=np.asarray(scores)>=.5
 return dict(frames=len(rows),normal_frames=int(sum(y==0)),error_frames=int(sum(y==1)),normal_false_alarms=int(sum(p&(y==0))),missed_errors=int(sum((~p)&(y==1))))

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--encoder');args=parser.parse_args()
 for name,expected in json.loads((ROOT/'input_hashes.json').read_text()).items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('Input hash mismatch: '+name)
 old=json.loads((ROOT/'cached_samples.json').read_text());new=json.loads((ROOT/'new_samples.json').read_text());rows=old+new
 assert len(old)==135 and len(new)==18 and len(set(r['group'] for r in new))==1
 assert all(not r['video'].startswith('rec06') for r in rows)
 with np.load(ROOT/'cached_v56_whole.npz',allow_pickle=False) as a:old_x=a['whole'].copy()
 assert old_x.shape==(135,2048) and np.isfinite(old_x).all()
 baseline,baseline_scores=evaluate(old,old_x)
 expected=json.loads((ROOT/'v56_expected.json').read_text())
 if baseline['confusion_matrix_normal_error']!=expected['confusion_matrix_normal_error']:raise RuntimeError('V56 baseline reproduction failed')
 print('V56 BASELINE REPRODUCED',flush=True)
 data=load_encoder_bytes(choose_encoder(args.encoder));new_x=encode_new(new,data)
 x=np.concatenate([old_x,new_x]);assert x.shape==(153,2048) and np.isfinite(x).all()
 before=train_predict(old,old_x,new,new_x)
 expanded,scores=evaluate(rows,x)
 # Holding the entire new capture group out must equal prediction from the old-only fit.
 if not np.allclose(before,scores[len(old):],atol=1e-6):raise RuntimeError('Paired capture group isolation failed')
 stage3=[i for i,r in enumerate(old) if r['stage']==3];s3rows=[old[i] for i in stage3]
 paired_by_video={video:counts([r for r in new if r['video']==video],before[[i for i,r in enumerate(new) if r['video']==video]]) for video in sorted(set(r['video'] for r in new))}
 report=dict(version='V58_STAGE3_PAIRED_OFFLINE',frames=153,normal_frames=132,error_frames=21,videos=16,capture_groups=15,new_pair_videos_held_together=True,encoder_sha256=ENCODER_SHA,threshold=.5,baseline_v56=baseline,expanded_group_cv=expanded,original_135_before=counts(old,baseline_scores),original_135_after=counts(old,scores[:len(old)]),original_stage3_before=counts(s3rows,baseline_scores[stage3]),original_stage3_after=counts(s3rows,scores[stage3]),new_capture_heldout=counts(new,before),new_capture_by_video=paired_by_video,rec06_used=False,stage2_error_evaluation_available=False,server_integration=False,deployable=False,independent_final_test=False,notes=['Two new videos share similar capture conditions and are held out together.','New-pair heldout scores are produced by V56 old-only training; no new-pair frames enter that fit.','Expanded old-group folds may train on both new pair videos, while excluding the entire evaluated old video.','Classifier/threshold fixed to V56; no parameter search.','Frozen encoder was previously trained on rec01..04; this is classifier group CV, not full-pipeline independence.','This is exploratory development after repeated inspection; no final untouched test accuracy claim.','Both normal-before and repaired-normal states are included, but adjacent frames are correlated.','No deployable classifier or V50 server modifications are included.'])
 out=ROOT/'results';out.mkdir(exist_ok=True)
 (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'samples.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');np.savez_compressed(out/'embeddings.npz',whole=x)
 with (out/'group_cv_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['video','group','stage','time','state','true_error','heldout_error_score','source_set']);w.writeheader()
  for i,(r,s) in enumerate(zip(rows,scores)):w.writerow(dict(video=r['video'],group=r['group'],stage=r['stage'],time=r['time'],state=r.get('state','existing'),true_error=r['error'],heldout_error_score=float(s),source_set='cached_v56' if i<len(old) else 'new_pair'))
 for name,m in [('V56 baseline',baseline),('V58 expanded',expanded)]:print(name,json.dumps({k:v for k,v in m.items() if k!='folds'}),flush=True)
 print('Original Stage3 before:',report['original_stage3_before']);print('Original Stage3 after:',report['original_stage3_after']);print('New paired capture held out:',report['new_capture_heldout'])
 with zipfile.ZipFile(ROOT/'v58_results.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(out.iterdir()):z.write(p,p.name)
 print('V58 COMPLETE | OFFLINE ONLY | V50 UNCHANGED');print('SEND:',ROOT/'v58_results.zip')
if __name__=='__main__':main()
