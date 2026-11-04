"""Frozen selected models. Stage5 gate is rider evidence, never error detection."""
import io,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch.nn import functional as F
from followalong_completion.model import ModelEngine as LegacyEngine

EXPECTED={
 'encoder_supcon.pt':'69c33ec5e8c0a040fabf9f203a9cfb7c21effd10a52980b9e0bd8d49789e256d',
 'stage_prototypes.pt':'0c8ca50bbaf2e2b6f856601cf8017cac4ffcf1eb93ad4a5d6e520bb699cba8d4',
 'temporal_final.pt':'e0317fad6ce5074fdb6acb98b23ebf25b5d7f56a20042a3da9415a43932c2592',
 'rider_verifier.npz':'40b8c9f9f8b11cd157c9de76086aeabef39de7de9be26d97dfb9b07b5f944e4c',
}
class ModelEngine(LegacyEngine):
    mode='real_v50'
    confirmation_count=3
    def __init__(self,bundle='model_bundle',device='cpu'):
        root=Path(bundle)
        for name,digest in EXPECTED.items():
            if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
                raise ValueError(f'Incorrect selected model: {name}')
        raw=(root/'POLICY_LOCK_BEFORE_TEST.json').read_bytes();lock=json.loads(raw)
        expected_policy=dict(temporal_threshold=.5,rider_threshold=.5,consecutive=3,
                             stage5_rider_required=True,frame_interval=.5,history_frames=5)
        if lock['policy']!=expected_policy or lock['roi']!=[.45,.48,.9,.96]:
            raise ValueError('Policy must match the policy selected before final test')
        super().__init__(bundle,device)
        if self.threshold!=.5:raise ValueError('Temporal threshold must stay 0.5')
        with np.load(root/'rider_verifier.npz',allow_pickle=False) as v:
            self.v={k:v[k].copy() for k in ['mean','scale','coef','intercept','roi']}
        if not all(np.isfinite(v).all() for v in self.v.values()):raise ValueError('Nonfinite verifier')
        if any(self.v[k].shape!=(2048,) for k in ['mean','scale','coef']):raise ValueError('Invalid verifier shape')
        if not np.all(self.v['scale']>0) or not np.allclose(self.v['roi'],lock['roi']):raise ValueError('Invalid verifier ROI/scale')
        self.provenance.update(policy=lock['policy'],policy_lock_sha256=hashlib.sha256(raw).hexdigest(),
                               verifier_sha256=EXPECTED['rider_verifier.npz'],error_verifier_available=False)

    def encode(self,image_bytes):
        return dict(whole=super().encode(image_bytes),image_bytes=image_bytes)

    @torch.inference_mode()
    def predict_details(self,features,stage):
        temporal=float(super().predict([f['whole'] for f in features],stage))
        rider=None;gate=True
        # Compute the second image embedding only for Stage5 completion candidates.
        # This preserves the selected decision: below temporal=.5 the count resets anyway.
        if stage==5:
            gate=False
            if temporal>=self.threshold:
                with Image.open(io.BytesIO(features[-1]['image_bytes'])) as source:
                    im=source.convert('RGB');w,h=im.size
                    crop=im.crop(tuple(round(a*b) for a,b in zip(self.v['roi'],[w,h,w,h])))
                    x=self.transform(crop).unsqueeze(0).to(self.device)
                with self.lock:vector=F.normalize(self.encoder(x),dim=1)[0].cpu().numpy()
                z=((vector-self.v['mean'])/self.v['scale'])@self.v['coef']+self.v['intercept']
                rider=float(1/(1+np.exp(-np.clip(z,-60,60))));gate=bool(rider>=.5)
        return dict(completion_score=temporal,rider_probability=rider,rider_gate_passed=gate)
