"""Unchanged V4.2 architecture and state digest; no training code."""
import hashlib
import torch
from torch import nn
class StageConditionedTemporalTransformer(nn.Module):

    def __init__(
        self,
        input_dim=2048,
        d_model=256,
        nhead=4,
        num_layers=2,
        dropout=0.1,
        clip_len=5
    ):

        super().__init__()

        # Frame feature와 prototype 둘 다
        # 같은 embedding 공간으로 projection
        self.input_proj = nn.Linear(
            input_dim,
            d_model
        )

        # CLS token
        self.cls_token = nn.Parameter(
            torch.zeros(
                1,
                1,
                d_model
            )
        )

        # sequence:
        # CLS + Prototype + 5 Frames
        self.pos_embed = nn.Parameter(
            torch.zeros(
                1,
                clip_len + 2,
                d_model
            )
        )

        encoder_layer = nn.TransformerEncoderLayer(

            d_model=d_model,
            nhead=nhead,

            dim_feedforward=512,

            dropout=dropout,

            batch_first=True,
            norm_first=True
        )

        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        self.classifier = nn.Sequential(

            nn.LayerNorm(
                d_model
            ),

            nn.Linear(
                d_model,
                1
            )
        )


    def forward(
        self,
        frames,
        prototype
    ):

        # frames
        # [B, 5, 2048]
        frame_tokens = self.input_proj(
            frames
        )

        # prototype
        # [B, 2048]
        prototype_token = self.input_proj(
            prototype
        )

        # [B, 1, 256]
        prototype_token = (
            prototype_token.unsqueeze(1)
        )

        batch_size = frames.size(0)

        # [B, 1, 256]
        cls = self.cls_token.expand(
            batch_size,
            -1,
            -1
        )

        # [CLS, Prototype, Frame1 ... Frame5]
        x = torch.cat(
            [
                cls,
                prototype_token,
                frame_tokens
            ],
            dim=1
        )

        x = (
            x
            +
            self.pos_embed
        )

        x = self.transformer(
            x
        )

        # CLS output
        cls_feature = x[:, 0]

        logits = self.classifier(
            cls_feature
        ).squeeze(1)

        return logits

def state_digest(model):
    h = hashlib.sha256()
    for key, tensor in model.state_dict().items():
        h.update(key.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
