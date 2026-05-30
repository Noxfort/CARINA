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

# File: src/models/pae.py (NEW FILE)
# Author: Gabriel Moraes
# Date: April 14, 2026

"""
Predictive Autoencoder (PAE) Universal — Shared Physics Engine.

This model is the core of CARINA's predictive HFT paradigm. It is
instantiated ONLY ONCE by the AgentManager and shared by reference
among all LocalAgents and GuardianAgents.

Objective: Learn the fluid dynamics of the streets in real-time (250ms
telemetry) via predictive reconstruction — given the state at time t, predict
the state at time t+1. The compressed latent space is then injected as a
context vector into the decision networks of each agent.

Design Decisions:
    - CONSTANT Learning Rate (default 5e-4): Allows continuous learning
      with new agents without individual maturation penalizing the collective.
      Balances plasticity (concept drift in the road network) and stability.
    - INTERNAL Optimizer (AdamW): Total encapsulation — the optimization step
      is self-contained in `training_step()`, eliminating external coupling.
    - LIGHTWEIGHT Architecture: 2-dense-layer Encoder-Decoder. The PAE does not need
      to be deep — it compresses the observation space, not raw images.
"""

import torch
import torch.nn as nn
import logging


class PredictiveAutoencoder(nn.Module):
    """
    Lightweight Predictive Autoencoder for learning urban fluid dynamics.
    
    The encoder projects the current state into a compressed latent space.
    The decoder predicts the NEXT state from this latent space.
    Loss = MSE(decoder(encoder(state_t)), state_t+1)

    Attributes:
        latent_dim (int): Latent space dimension (default 16).
        input_dim (int): Input state vector dimension.
    """

    def __init__(self, input_dim: int, latent_dim: int = 16, lr: float = 5e-4):
        """
        Initializes the Predictive Autoencoder.

        Args:
            input_dim (int): Size of the input state vector (n_observations).
            latent_dim (int): Dimension of the compressed latent space.
            lr (float): Constant learning rate for HFT equilibrium.
        """
        super(PredictiveAutoencoder, self).__init__()

        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.lr = lr

        # --- Encoder: Compresses the state into the latent space ---
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
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
        # GradScaler accepts explicit initialization strings in 2.0+ or defaults
        self.scaler = torch.amp.GradScaler(enabled=cuda_present)

        logging.info(
            f"[PAE] Predictive Autoencoder instantiated "
            f"(input={input_dim}, latent={latent_dim}, lr={lr}, AMP_Enabled={self.scaler.is_enabled()})"
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

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Projects the state into the latent space. Used by agents during INFERENCE.
        
        Args:
            x (torch.Tensor): State vector(s) [batch_size, input_dim].
        
        Returns:
            torch.Tensor: Latent vector [batch_size, latent_dim].
        """
        x_padded = self._pad_to_input_dim(x)
        return self.encoder(x_padded)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """
        Reconstructs/predicts the state from the latent vector.
        
        Args:
            z (torch.Tensor): Latent vector [batch_size, latent_dim].
        
        Returns:
            torch.Tensor: Reconstructed state [batch_size, input_dim].
        """
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Full encoder + decoder pass.
        
        Args:
            x (torch.Tensor): Input state [batch_size, n_local_observations].
        
        Returns:
            torch.Tensor: Reconstructed/predicted state [batch_size, input_dim].
        """
        z = self.encode(x)
        return self.decode(z)

    def training_step(self, current_state: torch.Tensor, next_state: torch.Tensor) -> float:
        """
        Self-contained optimization step for predictive learning.
        
        Trains the PAE to predict state t+1 from state t.
        This method is called by the agents during their learn() cycle,
        allowing collective learning — all agents contribute
        gradients to the same model.

        Args:
            current_state (torch.Tensor): State at time t [batch, input_dim].
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
            # Prediction: encoder(state_t) → decoder → predicted_state_t+1
            # forward() already pads current_state to input_dim
            predicted_next = self.forward(current_state)
            
            # Universal Loss: Pad actual next_state to match predicted dimension
            next_state_padded = self._pad_to_input_dim(next_state)
            loss = self.loss_fn(predicted_next, next_state_padded.detach())

        self.scaler.scale(loss).backward()
        
        # Gradient clipping for stability in collective training (must unscale first)
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.parameters(), max_norm=1.0)
        
        self.scaler.step(self.optimizer)
        self.scaler.update()

        return loss.item()
