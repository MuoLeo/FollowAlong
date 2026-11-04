"""V56: add reviewed normal frames; frozen encoder; offline diagnostic only."""
import csv,hashlib,io,json,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from v55_support import choose_encoder,load_encoder_bytes,square_pad,evaluate,ENCODER_SHA
ROOT=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def encode_new(rows,data):
 import torch
 from torch import nn
 from torchvision.models import resnet50,ResNet50_Weights
 from torch.nn import functional as F
 torch.set_num_threads(2)
 state=torch.load(io.BytesIO(data),map_location='cpu',weights_only=True)
 model=resnet50(weights=None);model.fc=nn.Identity();model.load_state_dict(state['backbone_state_dict'],strict=True);model.eval()
 transform=ResNet50_Weights.DEFAULT.transforms();features=[]
 with torch.inference_mode():
  for i,row in enumerate(rows):
   with Image.open(ROOT/row['image']) as src:im=square_pad(src.convert('RGB'))
   features.append(F.normalize(model(transform(im).unsqueeze(0)),dim=1).cpu().numpy()[0])
   if i%10==0 or i+1==len(rows):print(f'Encoder {i+1}/{len(rows)}',flush=True)
 return np.stack(features)

def main():
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--encoder');args=p.parse_args()
 lock=json.loads((ROOT/'input_hashes.json').read_text())
 for name,expected in lock.items():
  if digest(ROOT/name)!=expected:raise ValueError('Input hash mismatch: '+name)
 old=json.loads((ROOT/'cached_samples.json').read_text());new=json.loads((ROOT/'new_samples.json').read_text());rows=old+new
 assert len(old)==60 and len(new)==75
 assert all(not r['group'].startswith('rec06') for r in rows)
 with np.load(ROOT/'cached_v55_whole.npz',allow_pickle=False) as a:old_x=a['whole'].copy()
 assert old_x.shape==(60,2048) and np.isfinite(old_x).all()
 data=load_encoder_bytes(choose_encoder(args.encoder));new_x=encode_new(new,data);x=np.concatenate([old_x,new_x])
 assert x.shape==(135,2048) and np.isfinite(x).all()
 out=ROOT/'results';out.mkdir(exist_ok=True)
 np.savez_compressed(out/'embeddings.npz',whole=x)
 (out/'samples.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 before,before_scores=evaluate(old,old_x);after,scores=evaluate(rows,x)
 expected=json.loads((ROOT/'v55_expected.json').read_text())
 if before['confusion_matrix_normal_error']!=expected['confusion_matrix_normal_error']:raise RuntimeError('Cached V55 baseline did not reproduce')
 # Old subset is useful for before/after counts, but after training sets now contain extra recordings.
 def counts(rr,ss):
  y=np.array([r['error'] for r in rr]);pred=np.asarray(ss)>=.5
  return dict(normal_frames=int(sum(y==0)),error_frames=int(sum(y==1)),normal_false_alarms=int(sum(pred&(y==0))),missed_errors=int(sum((~pred)&(y==1))))
 report=dict(version='V56_NORMAL_EXPANSION_OFFLINE',normal_frames=120,error_frames=15,recordings=14,normal_recordings=8,error_recordings=6,rec06_used=False,encoder_sha256=ENCODER_SHA,threshold=.5,baseline_v55=before,expanded_group_cv=after,original_60_subset_after_expansion=counts(old,scores[:60]),server_integration=False,deployable=False,independent_final_test=False,stage2_error_evaluation_available=False,notes=['Fixed V55 classifier, C=0.1, threshold=0.5; no hyperparameter search.','Each outer fold holds out one entire video; adjacent frames are correlated.','Frozen encoder was previously trained on rec01..04; this is classifier group CV, not full-pipeline independence.','rec06 is reserved and never loaded by this package; it has previously been inspected in completion experiments.','Normal-only rec06 cannot validate error recall.','Prior experiment observations informed normal-data expansion; no untouched final accuracy claim.','No automatic quality gate, server integration, or production verifier is provided.'])
 (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 with (out/'group_cv_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['video','stage','time','true_error','heldout_error_score','source_set']);w.writeheader()
  for i,(r,score) in enumerate(zip(rows,scores)):w.writerow(dict(video=r['video'],stage=r['stage'],time=r['time'],true_error=r['error'],heldout_error_score=float(score),source_set='cached_v55' if i<60 else 'added_normal'))
 for name,metrics in [('V55 baseline',before),('V56 expanded',after)]:print(name,json.dumps({k:v for k,v in metrics.items() if k!='folds'}),flush=True)
 print('Original 60 after expansion:',report['original_60_subset_after_expansion'])
 with zipfile.ZipFile(ROOT/'v56_results.zip','w',zipfile.ZIP_DEFLATED) as z:
  for path in sorted(out.iterdir()):z.write(path,path.name)
 print('V56 COMPLETE | OFFLINE ONLY | V50 UNCHANGED')
 print('SEND:',ROOT/'v56_results.zip')
if __name__=='__main__':main()
