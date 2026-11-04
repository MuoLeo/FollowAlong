"""Frozen SupCon encoder: whole-image versus manually cropped target; offline only."""
import argparse,hashlib,json,csv,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
ENCODER_SHA='69c33ec5e8c0a040fabf9f203a9cfb7c21effd10a52980b9e0bd8d49789e256d'

def load_encoder_bytes(selected):
 p=Path(selected)
 if p.suffix.lower()=='.zip':
  with zipfile.ZipFile(p) as z:
   ns=[n for n in z.namelist() if n.replace('\\','/').split('/')[-1]=='encoder_supcon.pt']
   if len(ns)!=1:raise ValueError('ZIP must contain exactly one encoder_supcon.pt')
   data=z.read(ns[0])
 else:data=p.read_bytes()
 if hashlib.sha256(data).hexdigest()!=ENCODER_SHA:raise ValueError('Encoder hash mismatch. Use the selected V50 handoff encoder.')
 return data

def choose_encoder(value):
 if value:return value
 path=Path.home()/'Downloads/FollowAlong_V50_handoff.zip'
 if path.is_file():return str(path)
 import tkinter as tk
 from tkinter.filedialog import askopenfilename
 root=tk.Tk();root.withdraw()
 try:path=askopenfilename(title='Select FollowAlong_V50_handoff.zip or encoder_supcon.pt',filetypes=[('Model bundle','*.zip *.pt'),('All files','*.*')])
 finally:root.destroy()
 if not path:raise ValueError('No encoder selected. Nothing trained.')
 return path

def target_image(im,box):
 w,h=im.size
 if not(len(box)==4 and 0<=box[0]<box[2]<=1 and 0<=box[1]<box[3]<=1):raise ValueError('Invalid box')
 return im.crop(tuple(round(a*b) for a,b in zip(box,[w,h,w,h])))

def square_pad(im):
 # Padding avoids trimming off the front/rear of a long chassis at center crop.
 side=max(im.size);canvas=Image.new('RGB',(side,side),(124,116,104));canvas.paste(im,((side-im.width)//2,(side-im.height)//2));return canvas

def encode(rows,data,out):
 import io,torch
 from torch import nn
 from torchvision.models import resnet50,ResNet50_Weights
 from torch.nn import functional as F
 torch.set_num_threads(2)
 checkpoint=torch.load(io.BytesIO(data),map_location='cpu',weights_only=True)
 encoder=resnet50(weights=None);encoder.fc=nn.Identity();encoder.load_state_dict(checkpoint['backbone_state_dict'],strict=True);encoder.eval()
 transform=ResNet50_Weights.DEFAULT.transforms();features={'whole':[],'target_crop':[]}
 with torch.inference_mode():
  for i,r in enumerate(rows):
   with Image.open(ROOT/r['image']) as src:im=src.convert('RGB')
   crops=[square_pad(im),square_pad(target_image(im,r['box_xyxy_normalized']))]
   batch=torch.stack([transform(c) for c in crops]);emb=F.normalize(encoder(batch),dim=1).cpu().numpy()
   features['whole'].append(emb[0]);features['target_crop'].append(emb[1])
   if i%10==0:print(f'Encoder {i+1}/{len(rows)}',flush=True)
 for k in features:features[k]=np.stack(features[k])
 np.savez_compressed(out/'embeddings.npz',**features)
 return features

def evaluate(rows,embedding):
 from sklearn.linear_model import LogisticRegression
 from sklearn.preprocessing import StandardScaler
 from sklearn.metrics import accuracy_score,balanced_accuracy_score,precision_score,recall_score,f1_score,confusion_matrix
 y=np.array([r['error'] for r in rows]);g=np.array([r['group'] for r in rows]);stage=np.array([r['stage'] for r in rows]);x=np.c_[embedding,np.eye(5)[stage-1]]
 scores=np.full(len(rows),np.nan);folds=[]
 for group in sorted(set(g)):
  train=g!=group;test=~train;assert set(g[train]).isdisjoint(set(g[test]))
  scaler=StandardScaler();xx=scaler.fit_transform(x[train]);sizes={a:sum(g[train]==a) for a in set(g[train])}
  weights=np.array([1/sizes[a] for a in g[train]])
  classifier=LogisticRegression(C=.1,class_weight='balanced',max_iter=3000,random_state=42)
  classifier.fit(xx,y[train],sample_weight=weights);ss=classifier.predict_proba(scaler.transform(x[test]))[:,1];scores[test]=ss
  folds.append(dict(video=group,normal_frames=int(sum(y[test]==0)),error_frames=int(sum(y[test]==1)),false_alarms=int(sum((ss>=.5)&(y[test]==0))),missed_errors=int(sum((ss<.5)&(y[test]==1)))))
 assert np.isfinite(scores).all();pred=scores>=.5
 metrics=dict(accuracy=float(accuracy_score(y,pred)),balanced_accuracy=float(balanced_accuracy_score(y,pred)),error_precision=float(precision_score(y,pred,zero_division=0)),error_recall=float(recall_score(y,pred,zero_division=0)),error_f1=float(f1_score(y,pred,zero_division=0)),normal_false_alarm_rate=float(np.mean(pred[y==0])),confusion_matrix_normal_error=confusion_matrix(y,pred,labels=[0,1]).tolist(),folds=folds)
 return metrics,scores

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--encoder');a=p.parse_args()
 rows=json.loads((ROOT/'samples.json').read_text(encoding='utf-8'));data=load_encoder_bytes(choose_encoder(a.encoder));out=ROOT/'results';out.mkdir(exist_ok=True)
 embedding=encode(rows,data,out)
 report=dict(version='V55_OFFLINE_ENCODER_ABLATION',encoder_sha256=ENCODER_SHA,encoder_frozen=True,frames=len(rows),recordings=len(set(r['group'] for r in rows)),normal_recordings=3,error_recordings=6,threshold=.5,roi_source='manually_specified_per_recording_and_stage',automatic_object_detection=False,independent_final_test=False,stage2_error_evaluation_available=False,server_integration=False,deployable=False,variants={},notes=['Manual object boxes are supplied for these frames; camera localization remains unimplemented.','Both variants use square padding followed by the saved encoder preprocessing.','All frames from one video are held out together.','This is exploratory grouped cross-validation after prior experiments, not an untouched final test.','Frames from the same clip are correlated and labels remain provisional.','No V50 completion weights, threshold, or server code are modified.'])
 predictions=[]
 for name,features in embedding.items():
  metrics,scores=evaluate(rows,features);report['variants'][name]=metrics
  for r,s in zip(rows,scores):predictions.append(dict(variant=name,video=r['video'],stage=r['stage'],time=r['time'],true_error=r['error'],heldout_error_score=float(s)))
  print(name,json.dumps({k:v for k,v in metrics.items() if k!='folds'}),flush=True)
 (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 with (out/'group_cv_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(predictions[0]));w.writeheader();w.writerows(predictions)
 with zipfile.ZipFile(ROOT/'v55_results.zip','w',zipfile.ZIP_DEFLATED) as z:
  for path in sorted(out.iterdir()):z.write(path,path.name)
 print('V55 COMPLETE | OFFLINE ONLY')
 print('SEND:',ROOT/'v55_results.zip')
if __name__=='__main__':main()
