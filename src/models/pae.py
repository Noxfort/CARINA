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

# File: src/models/pae.py
# Author: Gabriel Moraes
# Date: July 18, 2026

"""
Predictive Autoencoder (PAE) Universal — Shared Physics Engine (iTransformer Backbone).

This model is the core of CARINA's predictive HFT paradigm. It is
instantiated ONLY ONCE by the AgentManager and shared by reference
among all LocalAgents and GuardianAgents.

Objective: Learn the fluid dynamics of the streets in real-time (250ms
telemetry) via predictive reconstruction — given a temporal sequence of states,
predict the NEXT state. The compressed latent space is then injected as a
context vector into the decision networks of each agent.

Design Decisions:
    - iTRANSFORMER ARCHITECTURE: Inverts the sequence representation. Instead of
      applying self-attention over the time dimension, we embed each variable's history
      independently and apply self-attention over the variables. This captures correlations
      between traffic features (e.g. queue vs speed vs signal phase).
    - CONSTANT Learning Rate (default 5e-4): Allows continuous learning
      with new agents without individual maturation penalizing the collective.
      Balances plasticity (concept drift in the road network) and stability.
    - INTERNAL Optimizer (AdamW): Total encapsulation — the optimization step
      is self-contained in `training_step()`, eliminating external coupling.
    - STANDARDIZED TEMPORAL SHAPING: Accepts 2D or 3D tensors of any sequence length,
      internally padding or slicing them to a fixed history_len.
"""

import torch
import torch.nn as nn
import logging
from typing import Tuple, List, Optional, Any


class PredictiveAutoencoder(nn.Module):
    """
    iTransformer Predictive Autoencoder for learning urban fluid dynamics.
    
    The encoder projects the temporal sequence of states (inverted over variables)
    into a compressed latent space.
    The decoder predicts the NEXT state from this latent space.
    Loss = MSE(decoder(encoder(state_seq_t)), state_t+1)

    Attributes:
        latent_dim (int): Latent space dimension (default 16).
        input_dim (int): Input state vector dimension.
    """

    def __init__(self, input_dim: int, latent_dim: int = 16, lr: float = 5e-4,
                 history_len: int = 16, d_model: int = 32, nhead: int = 4,
                 num_layers: int = 2, dropout: float = 0.1) -> None:
        """
        Initializes the iTransformer Predictive Autoencoder.

        Args:
            input_dim (int): Size of the input state vector (n_observations).
            latent_dim (int): Dimension of the compressed latent space.
            lr (float): Constant learning rate for HFT equilibrium.
            history_len (int): Internal target length for the input sequence history.
            d_model (int): Hidden embedding dimension for the transformer.
            nhead (int): Number of attention heads.
            num_layers (int): Number of transformer encoder layers.
            dropout (float): Dropout probability.
        """
        super(PredictiveAutoencoder, self).__init__()

        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.lr = lr
        self.history_len = history_len
        self.d_model = d_model

        # --- iTransformer Encoder Components ---
        # 1. Temporal projection: Map history_len to d_model for each variable
        self.value_embedding = nn.Linear(history_len, d_model)
        
        # 2. Variable/Channel embedding (learnable position-like bias for each variable)
        self.var_embedding = nn.Parameter(torch.randn(1, input_dim, d_model) * 0.02)
        
        # 3. Transformer Encoder over the variables/channels
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            activation='relu',
            layer_norm_eps=1e-5,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # 4. Latent Space Projection (MLP projection from flattened transformer output to latent)
        self.latent_proj = nn.Sequential(
            nn.Linear(input_dim * d_model, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Linear(64, latent_dim)
        )

        # --- Decoder (Predictive): Reconstructs/predicts the NEXT state ---
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Linear(64, input_dim)
        )

        # Internal optimizer — total encapsulation
        self.optimizer = torch.optim.AdamW(self.parameters(), lr=self.lr)
        self.loss_fn = nn.MSELoss()
        
        # Hardware Accel: Internal GradScaler for massive multi-agent batches
        cuda_present = torch.cuda.is_available()
        self.scaler = torch.amp.GradScaler(enabled=cuda_present)

        logging.info(
            f"[PAE] iTransformer Predictive Autoencoder instantiated "
            f"(input={input_dim}, latent={latent_dim}, lr={lr}, history={history_len}, AMP_Enabled={self.scaler.is_enabled()})"
        )

    def _pad_to_input_dim(self, x: torch.Tensor) -> torch.Tensor:
        """
        Pads or truncates agent local state vectors to the universal PAE input_dim.
        This enables agents with different intersection sizes (e.g. 3 edges vs 5 edges)
        to share the same Physics Engine without shape multiplier crashes.
        """
        current_dim = x.size(-1)
        if current_dim < self.input_dim:
            pad_size = self.input_dim - current_dim
            return torch.nn.functional.pad(x, (0, pad_size))
        elif current_dim > self.input_dim:
            return x[..., :self.input_dim]
        return x

    def _standardize_sequence(self, x: torch.Tensor) -> torch.Tensor:
        """
        Standardizes any input tensor (2D [batch, input_dim] or 3D [batch, seq_len, input_dim])
        to a fixed 3D shape [batch, history_len, input_dim].
        """
        x_padded = self._pad_to_input_dim(x)
        
        if x_padded.dim() == 2:
            x_padded = x_padded.unsqueeze(1)  # [batch, 1, input_dim]
            
        batch, seq_len, input_dim = x_padded.size()
        
        if seq_len == self.history_len:
            return x_padded
        elif seq_len < self.history_len:
            # Replicate the first frame to pad sequence to history_len
            pad_size = self.history_len - seq_len
            first_frame = x_padded[:, :1, :]
            padding = first_frame.repeat(1, pad_size, 1)
            return torch.cat([padding, x_padded], dim=1)
        else:
            # Slice last history_len states
            return x_padded[:, -self.history_len:, :]

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Projects the state sequence into the latent space. Used by agents during INFERENCE.
        
        Args:
            x (torch.Tensor): State sequence [batch_size, seq_len, input_dim]
                              or state vector [batch_size, input_dim].
        
        Returns:
            torch.Tensor: Latent vector [batch_size, latent_dim].
        """
        x_std = self._standardize_sequence(x)  # [batch_size, history_len, input_dim]
        
        # Invert dimensions: variables become tokens
        # [batch_size, history_len, input_dim] -> [batch_size, input_dim, history_len]
        x_vars = x_std.transpose(1, 2)
        
        # Temporal embedding for each variable: [batch_size, input_dim, d_model]
        x_emb = self.value_embedding(x_vars)
        
        # Add variable positional encoding
        x_emb = x_emb + self.var_embedding
        
        # Attention over variables: [batch_size, input_dim, d_model]
        x_out = self.transformer_encoder(x_emb)
        
        # Flatten and project to latent space: [batch_size, latent_dim]
        x_flat = x_out.reshape(x_out.size(0), -1)
        return self.latent_proj(x_flat)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """
        Reconstructs/predicts the state from the latent vector.
        
        Args:
            z (torch.Tensor): Latent vector [batch_size, latent_dim].
        
        Returns:
            torch.Tensor: Reconstructed/predicted next state [batch_size, input_dim].
        """
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Full encoder + decoder pass.
        
        Args:
            x (torch.Tensor): Input state sequence [batch_size, seq_len, input_dim]
                              or state vector [batch_size, input_dim].
        
        Returns:
            torch.Tensor: Predicted next state [batch_size, input_dim].
        """
        z = self.encode(x)
        return self.decode(z)

    def training_step(self, current_state: torch.Tensor, next_state: torch.Tensor) -> float:
        """
        Self-contained optimization step for predictive learning.
        
        Trains the PAE to predict state t+1 from state sequence t.
        This method is called by the agents during their learn() cycle,
        allowing collective learning — all agents contribute
        gradients to the same model.

        Args:
            current_state (torch.Tensor): State sequence at time t [batch, seq_len, input_dim]
                                          or single state [batch, input_dim].
            next_state (torch.Tensor): Actual state at time t+1 [batch, input_dim].

        Returns:
            float: Loss value for logging/monitoring.
        """
        self.train()
        self.optimizer.zero_grad()
        
        # Dynamically infer computational device
        device_type = 'cuda' if current_state.is_cuda else 'cpu'

        # Hardware Accel: AMP Precision Wrapper
        with torch.amp.autocast(device_type=device_type, enabled=self.scaler.is_enabled()):
            # Prediction: encoder(state_seq_t) → decoder → predicted_state_t+1
            predicted_next = self.forward(current_state)
            
            # Universal Loss: Pad actual next_state to match predicted dimension
            next_state_padded = self._pad_to_input_dim(next_state)
            if next_state_padded.dim() == 3:
                # Target must be a single step (take the last frame if it's 3D)
                next_state_padded = next_state_padded[:, -1, :]
            
            loss = self.loss_fn(predicted_next, next_state_padded.detach())

        self.scaler.scale(loss).backward()
        
        # Gradient clipping for stability in collective training (must unscale first)
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.parameters(), max_norm=1.0)
        
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()
