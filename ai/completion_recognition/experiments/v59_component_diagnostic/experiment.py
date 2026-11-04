"""V59: offline, manually located component diagnostics; not a general error verifier."""
import csv,json,hashlib,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix,balanced_accuracy_score,precision_score,recall_score,f1_score
ROOT=Path(__file__).resolve().parent

def crop(row):
 with Image.open(ROOT/row['image']) as src:
  im=src.convert('RGB');w,h=im.size
  return im.crop(tuple(round(v*d) for v,d in zip(row['box'],[w,h,w,h])))

def yellow_fraction(im):
 # Fixed visible-yellow definition; tuned neither on held-out labels nor scores.
 hsv=np.asarray(im.convert('HSV'),dtype=float)/255.
 return float(np.mean((hsv[:,:,0]>=.08)&(hsv[:,:,0]<=.20)&(hsv[:,:,1]>=.45)&(hsv[:,:,2]>=.30)))

def tire_features(im):
 # Explicit spatial edges at higher target resolution, no frozen completion encoder.
 im=im.resize((96,64),Image.Resampling.BILINEAR);rgb=np.asarray(im,dtype=float)/255.;gray=rgb@np.array([.299,.587,.114]);gy,gx=np.gradient(gray)
 mag=np.hypot(gx,gy);bins=np.minimum((np.mod(np.arctan2(gy,gx),np.pi)/np.pi*9).astype(int),8)
 hist=[]
 for y in range(0,64,8):
  for x in range(0,96,8):
   h=np.bincount(bins[y:y+8,x:x+8].ravel(),weights=mag[y:y+8,x:x+8].ravel(),minlength=9);hist.extend(h/(np.linalg.norm(h)+1e-6))
 small=np.asarray(im.resize((16,12)),dtype=float).ravel()/255.
 return np.r_[hist,small]

def fit_yellow_threshold(values,y):
 # Threshold fitted on training groups only, with a fixed balanced-accuracy objective.
 unique=np.unique(values);candidates=np.r_[unique[0]-1e-9,(unique[:-1]+unique[1:])/2,unique[-1]+1e-9]
 best=max(candidates,key=lambda t:(balanced_accuracy_score(y,values<t),-float(t)))
 return float(best)

def metrics(y,p):
 return dict(frames=len(y),normal_frames=int(sum(y==0)),error_frames=int(sum(y==1)),accuracy=float(np.mean(y==p)),balanced_accuracy=float(balanced_accuracy_score(y,p)) if len(set(y))==2 else None,error_precision=float(precision_score(y,p,zero_division=0)),error_recall=float(recall_score(y,p,zero_division=0)),error_f1=float(f1_score(y,p,zero_division=0)),confusion_matrix_normal_error=confusion_matrix(y,p,labels=[0,1]).tolist(),normal_false_alarms=int(sum((p==1)&(y==0))),missed_errors=int(sum((p==0)&(y==1))))

def main():
 lock=json.loads((ROOT/'input_hashes.json').read_text())
 for name,h in lock.items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise ValueError('Input hash mismatch: '+name)
 rows=json.loads((ROOT/'samples.json').read_text());out=ROOT/'results';out.mkdir(exist_ok=True);report=dict(version='V59_COMPONENT_OFFLINE',automatic_target_localization=False,manual_boxes_required=True,general_assembly_error_verifier=False,deployable=False,server_integration=False,rec06_used=False,independent_final_test=False,tasks={},notes=['Scopes differ from V56/V58; do not compare overall accuracy as the same task.','Only Stage3 visible yellow-block absence and Stage5 visible rubber-tire absence are labeled here.','Reversed black parts, arbitrary malformed cars and other defect types are excluded, not relabeled normal.','Manual per-video/stage ROIs were visually reviewed; automatic camera localization/quality gating remains absent.','All four newly paired clips are grouped together to avoid reuse of their capture conditions across train/test.','Threshold/classifier fit uses outer training groups only; these are exploratory diagnostics after seeing prior results.','Pixel thresholds do not establish correct block position/orientation. A present yellow block alone cannot mean assembly is correct.','Adjacent frames are correlated. Only two capture groups contain each component error type.'])
 predictions=[]
 for task in sorted(set(r['task'] for r in rows)):
  rr=[r for r in rows if r['task']==task];y=np.array([r['error'] for r in rr]);g=np.array([r['group'] for r in rr]);ims=[crop(r) for r in rr]
  x=np.array([yellow_fraction(im) for im in ims]) if task.startswith('stage3') else np.array([tire_features(im) for im in ims])
  pred=np.full(len(rr),-1);score=np.full(len(rr),np.nan);folds=[]
  for group in sorted(set(g)):
   train=g!=group;test=~train;assert set(g[train]).isdisjoint(set(g[test]))
   if len(set(y[train]))!=2:raise ValueError('Missing training class in '+group)
   if task.startswith('stage3'):
    threshold=fit_yellow_threshold(x[train],y[train]);score[test]=threshold-x[test];pred[test]=(score[test]>0).astype(int);score_type='yellow_fraction_threshold_minus_observed_fraction_not_probability'
   else:
    scaler=StandardScaler().fit(x[train]);sizes={a:sum(g[train]==a) for a in set(g[train])};weights=np.array([1/sizes[a] for a in g[train]])
    model=LogisticRegression(C=.1,class_weight='balanced',max_iter=3000,random_state=42);model.fit(scaler.transform(x[train]),y[train],sample_weight=weights)
    score[test]=model.predict_proba(scaler.transform(x[test]))[:,1];pred[test]=(score[test]>=.5).astype(int);threshold=.5;score_type='uncalibrated_classifier_error_score'
   folds.append(dict(group=group,training_threshold=float(threshold),**metrics(y[test],pred[test])))
  new=g=='new_pairs_shared_capture';result=dict(**metrics(y,pred),folds=folds,new_capture_heldout=metrics(y[new],pred[new]),score_type=score_type)
  report['tasks'][task]=result
  for r,p,s in zip(rr,pred,score):predictions.append(dict(task=task,video=r['video'],group=r['group'],time=r['time'],true_error=r['error'],predicted_error=int(p),score=float(s),score_type=score_type))
  print(task,json.dumps({k:v for k,v in result.items() if k!='folds'}),flush=True)
 (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');(out/'samples.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 with (out/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(predictions[0]));w.writeheader();w.writerows(predictions)
 with zipfile.ZipFile(ROOT/'v59_results.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(out.iterdir()):z.write(p,p.name)
 print('V59 COMPLETE | COMPONENT DIAGNOSTIC ONLY | V50 UNCHANGED');print('SEND:',ROOT/'v59_results.zip')
if __name__=='__main__':main()
