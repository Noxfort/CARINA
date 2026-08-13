# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/models/cross_attention.py
# Author: Gabriel Moraes
# Date: August 2026

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict, Any, Optional

class CrossAttentionFusion(nn.Module):
    """
    Multi-Head Cross-Attention Transformer Fusion Layer.
    Dynamically weights and fuses multimodal input tensors:
    - Local Physical Sensors (t_local) [Present]
    - ST-GATv2 Lite Network Vectors (t_stgat) [Spatial Graph Topology]
    - Consultant PAE Predictive Latents (t_pae) [Future Projection]

    Dual-Policy Mode:
    - is_fixed=False (LocalAgent): Adaptive trainable weights with PBT evolution.
    - is_fixed=True (GuardianAgent): Deterministic frozen weights for safety veto auditing.
    """
    def __init__(self, local_dim: int = 17, stgat_dim: int = 16, pae_dim: int = 16, 
                 embed_dim: int = 32, num_heads: int = 4, is_fixed: bool = False):
        super(CrossAttentionFusion, self).__init__()
        self.local_dim = local_dim
        self.stgat_dim = stgat_dim
        self.pae_dim = pae_dim
        self.embed_dim = embed_dim
        self.is_fixed = is_fixed
        self.temperature = 1.0  # PBT tunable softmax temperature

        # Projection heads to unified embedding space
        self.proj_local = nn.Linear(local_dim, embed_dim)
        self.proj_stgat = nn.Linear(stgat_dim, embed_dim)
        self.proj_pae = nn.Linear(pae_dim, embed_dim)

        # Multi-Head Attention Mechanism
        self.mha = nn.MultiheadAttention(embed_dim=embed_dim, num_heads=num_heads, batch_first=True)
        self.norm = nn.LayerNorm(embed_dim)
        self.gating_head = nn.Linear(embed_dim * 3, 3)

        if self.is_fixed:
            self.eval()
            for p in self.parameters():
                p.requires_grad = False

    def update_pbt_hyperparameters(self, temperature: float = 1.0):
        """Updates PBT dynamic hyperparameters (softmax temperature)."""
        if not self.is_fixed:
            self.temperature = max(0.1, min(temperature, 5.0))

    def forward(self, t_local: torch.Tensor, t_stgat: torch.Tensor, t_pae: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Fuses inputs dynamically.

        Args:
            t_local: [B, local_dim] or [B, S, local_dim]
            t_stgat: [B, stgat_dim]
            t_pae:   [B, pae_dim]

        Returns:
            fused_tensor: [B, embed_dim * 3]
            attention_weights: [B, 3] softmax weights (Local, ST-GATv2, PAE)
        """
        # Ensure 2D [B, D]
        if t_local.dim() == 3:
            t_local_flat = t_local.mean(dim=1)
        else:
            t_local_flat = t_local

        if t_stgat.dim() == 3:
            t_stgat_flat = t_stgat.mean(dim=1)
        else:
            t_stgat_flat = t_stgat

        if t_pae.dim() == 3:
            t_pae_flat = t_pae.mean(dim=1)
        else:
            t_pae_flat = t_pae

        e_local = self.proj_local(t_local_flat)   # [B, E]
        e_stgat = self.proj_stgat(t_stgat_flat)   # [B, E]
        e_pae = self.proj_pae(t_pae_flat)         # [B, E]

        # Stack as sequence of 3 modality tokens: [B, 3, E]
        tokens = torch.stack([e_local, e_stgat, e_pae], dim=1)

        # Self-Attention across modality tokens
        if self.is_fixed:
            with torch.no_grad():
                attn_out, _ = self.mha(tokens, tokens, tokens)
                tokens = self.norm(tokens + attn_out)
                B = tokens.size(0)
                fused_tensor = tokens.reshape(B, -1)
                gating_logits = self.gating_head(fused_tensor)
                attention_weights = F.softmax(gating_logits / self.temperature, dim=-1)
        else:
            attn_out, _ = self.mha(tokens, tokens, tokens)
            tokens = self.norm(tokens + attn_out)
            B = tokens.size(0)
            fused_tensor = tokens.reshape(B, -1)
            gating_logits = self.gating_head(fused_tensor)
            attention_weights = F.softmax(gating_logits / self.temperature, dim=-1)

        return fused_tensor, attention_weights
