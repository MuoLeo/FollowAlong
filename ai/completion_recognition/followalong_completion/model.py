"""V4.2 weights, unchanged preprocessing and architecture. No checkpoint download."""
from pathlib import Path
import hashlib,io,json,threading
import numpy as np
from PIL import Image,UnidentifiedImageError
import torch
from torch import nn
from torch.nn import functional as F
from torchvision.models import resnet50,ResNet50_Weights
from .architecture import StageConditionedTemporalTransformer,state_digest
from .session import ProtocolError

class ModelEngine:
    mode='real_v42'
    def __init__(self,bundle='model_bundle',device=None):
        root=Path(bundle)
        policy=json.loads((root/'SAFETY_POLICY_LOCK.json').read_text(encoding='utf-8'))
        head_bytes=(root/'temporal_final.pt').read_bytes()
        if hashlib.sha256(head_bytes).hexdigest()!=policy['head_file_sha256']:
            raise ValueError('Head checkpoint does not match the locked policy')
        self.threshold=float(policy['threshold']);self.device=torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
        if self.device.type=='cpu':torch.set_num_threads(2)
        self.lock=threading.RLock()
        enc=torch.load(root/'encoder_supcon.pt',map_location='cpu',weights_only=True)
        self.encoder=resnet50(weights=None);self.encoder.fc=nn.Identity()
        self.encoder.load_state_dict(enc['backbone_state_dict']);self.encoder.eval().to(self.device)
        head=torch.load(io.BytesIO(head_bytes),map_location='cpu',weights_only=True)
        if state_digest(self.encoder)!=head['config']['input_sha256']['encoder_state_sha256']:
            raise ValueError('Encoder does not match Temporal training provenance')
        self.temporal=StageConditionedTemporalTransformer()
        self.temporal.load_state_dict(head['model_state_dict']);self.temporal.eval().to(self.device)
        self.prototypes=torch.load(root/'stage_prototypes.pt',map_location='cpu',weights_only=True)
        if set(self.prototypes)!=set(range(1,6)):raise ValueError('Expected five stage prototypes')
        for value in self.prototypes.values():
            if value.numel()!=2048 or not torch.isfinite(value).all():raise ValueError('Invalid prototype')
        self.transform=ResNet50_Weights.DEFAULT.transforms()
        self.provenance=dict(torch_version=str(torch.__version__),device=str(self.device),
                             head_file_sha256=hashlib.sha256(head_bytes).hexdigest(),threshold=self.threshold)

    @torch.inference_mode()
    def encode(self,image_bytes):
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                if image.format not in ('JPEG','PNG'):raise ValueError('Use JPEG or PNG')
                if image.width*image.height>12_000_000:raise ValueError('Image exceeds 12 megapixels')
                x=self.transform(image.convert('RGB')).unsqueeze(0).to(self.device)
        except (UnidentifiedImageError,OSError,ValueError) as exc:
            raise ProtocolError(422,'invalid_image',str(exc)) from exc
        with self.lock:return F.normalize(self.encoder(x),dim=1)[0].cpu()

    @torch.inference_mode()
    def predict(self,features,stage):
        frames=torch.stack(features).unsqueeze(0).to(self.device)
        prototype=self.prototypes[stage].reshape(1,2048).to(self.device)
        with self.lock:return torch.sigmoid(self.temporal(frames,prototype)).item()
