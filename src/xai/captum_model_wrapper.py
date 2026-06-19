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

# File: src/xai/captum_model_wrapper.py
# Author: Gabriel Moraes
# Date: June 19, 2026

import torch
import torch.nn as nn
from typing import Optional
from models.pae import PredictiveAutoencoder

class CaptumModelWrapper(nn.Module):
    """
    Wrapper that encapsulates the agent's model for Captum compatibility.
    If the agent has a PAE, the wrapper applies the PAE augmentation internally
    so that the attribution covers the augmented input space.
    """
    def __init__(self, model: nn.Module, shared_pae: Optional[PredictiveAutoencoder] = None) -> None:
        super(CaptumModelWrapper, self).__init__()
        self.model = model
        self.shared_pae = shared_pae

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # If we have PAE, augment the input with the latent vector
        if self.shared_pae is not None:
            with torch.no_grad():
                last_frame = x[:, -1, :]  # [batch, n_obs]
                # Extract only the original features (without latent) for the encode
                original_dim = self.shared_pae.input_dim
                original_frame = last_frame[:, :original_dim]
                latent = self.shared_pae.encode(original_frame)
                latent_expanded = latent.unsqueeze(1).expand(-1, x.size(1), -1)
                x = torch.cat([x, latent_expanded], dim=-1)
        else:
            # Fallback: if model expects more features than x provides, pad with zeros
            # This happens when the agent was trained with PAE but PAE is lost.
            expected_dim = self.model.tcn.network[0].conv1.in_channels
            if x.shape[-1] < expected_dim:
                padding_dim = expected_dim - x.shape[-1]
                zeros = torch.zeros(*x.shape[:-1], padding_dim, device=x.device, dtype=x.dtype)
                x = torch.cat([x, zeros], dim=-1)
                
        return self.model(x)[0]

    def to(self, *args, **kwargs) -> "CaptumModelWrapper":
        # Call parent's to if it exists (real PyTorch nn.Module)
        if hasattr(super(CaptumModelWrapper, self), 'to'):
            super(CaptumModelWrapper, self).to(*args, **kwargs)
        return self

    def __call__(self, *args, **kwargs) -> torch.Tensor:
        return self.forward(*args, **kwargs)
