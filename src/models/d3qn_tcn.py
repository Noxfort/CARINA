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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/models/d3qn_tcn.py
# Author: Gabriel Moraes
# Date: April 14, 2026

"""
Dueling Double DQN (D3QN) with self-contained Temporal Convolutional Network (TCN) backbone
and PAE latent space fusion.

This module is fully independent — it does NOT import from actor_critic_tcn.py.
The TCN classes (Chomp1d, TemporalBlock, TemporalConvNet) are internalized here
to eliminate coupling between the DQN (Guardian) and PPO (Local) paradigms.

Architecture:
    1. TCN Backbone: Processes the temporal state sequence to capture
       flow patterns and temporal trends (causal dilation).

    2. PAE Latent Fusion: Receives the latent vector from the shared Universal PAE,
       which encodes the spillback projection (risk of overflow).

    3. Dueling Architecture: Separates the estimation of state value V(s) and
       advantage of each action A(s,a), leading to more stable Q-values.

Flow: sequence -> TCN -> temporal_features --+
       PAE encode -> latent_vector -----------+
                                              +-> Fusion -> Advantage Stream -> Q(s,a)
                                              +-> Fusion -> Value Stream ------>
"""

import torch
import torch.nn as nn
from torch.nn.utils import weight_norm


# =============================================================================
# Temporal Convolutional Network (TCN) — Self-contained Implementation
# =============================================================================

class Chomp1d(nn.Module):
    """
    Removes extra right padding to ensure causality.
    This ensures that the output at t depends only on inputs t, t-1, ...
    """
    def __init__(self, chomp_size):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        return x[:, :, :-self.chomp_size].contiguous()


class TemporalBlock(nn.Module):
    """
    A standard TCN residual block consisting of two dilated convolutions,
    weight normalization, ReLU, Dropout and Chomp (causal trimming).
    """
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(TemporalBlock, self).__init__()

        # First convolutional layer
        self.conv1 = weight_norm(nn.Conv1d(n_inputs, n_outputs, kernel_size,
                                           stride=stride, padding=padding, dilation=dilation))
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        # Second convolutional layer
        self.conv2 = weight_norm(nn.Conv1d(n_outputs, n_outputs, kernel_size,
                                           stride=stride, padding=padding, dilation=dilation))
        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(self.conv1, self.chomp1, self.relu1, self.dropout1,
                                 self.conv2, self.chomp2, self.relu2, self.dropout2)

        # Residual connection (downsample if dimensions change)
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()
        self.init_weights()

    def init_weights(self):
        self.conv1.weight.data.normal_(0, 0.01)
        self.conv2.weight.data.normal_(0, 0.01)
        if self.downsample is not None:
            self.downsample.weight.data.normal_(0, 0.01)

    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)


class TemporalConvNet(nn.Module):
    """
    The complete TCN network, composed of a stack of TemporalBlocks.
    """
    def __init__(self, num_inputs, num_channels, kernel_size=2, dropout=0.2):
        super(TemporalConvNet, self).__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = num_inputs if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            layers += [TemporalBlock(in_channels, out_channels, kernel_size, stride=1,
                                     dilation=dilation_size,
                                     padding=(kernel_size-1) * dilation_size, dropout=dropout)]

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


# =============================================================================
# D3QN with TCN Backbone
# =============================================================================

class D3QN_TCN(nn.Module):
    """
    D3QN architecture with TCN temporal backbone and PAE latent space fusion.

    Designed for the Guardian Agent — combines temporal perception (TCN) with
    fluid dynamics projection (PAE) for safety decisions informed
    by spillback risk.
    """

    def __init__(self, n_observations: int = 2, n_actions: int = 2,
                 pae_latent_dim: int = 16, hidden_size: int = 64,
                 tcn_channels: list = None, kernel_size: int = 3,
                 dropout: float = 0.1):
        """
        Initializes the D3QN neural network with TCN and PAE fusion.

        Args:
            n_observations (int): Dimension of the state vector per timestep.
            n_actions (int): Number of possible actions (KEEP=0, CHANGE=1).
            pae_latent_dim (int): Dimension of the PAE latent vector (0 = no PAE).
            hidden_size (int): Neurons in hidden layers.
            tcn_channels (list): Channels for each TCN level.
            kernel_size (int): Size of the TCN kernel.
            dropout (float): Dropout rate.
        """
        super(D3QN_TCN, self).__init__()

        if tcn_channels is None:
            tcn_channels = [hidden_size, hidden_size]

        self.n_observations = n_observations
        self.n_actions = n_actions
        self.pae_latent_dim = pae_latent_dim
        self.hidden_size = hidden_size

        # --- TCN Backbone: Processes the temporal sequence ---
        self.tcn = TemporalConvNet(
            num_inputs=n_observations,
            num_channels=tcn_channels,
            kernel_size=kernel_size,
            dropout=dropout
        )

        # --- Fusion Layer: Combines temporal features + PAE latent space ---
        fusion_input_dim = hidden_size + pae_latent_dim
        self.fusion_layer = nn.Sequential(
            nn.Linear(fusion_input_dim, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # --- Advantage Stream: Estimates relative advantage of each action ---
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, n_actions)
        )

        # --- Value Stream: Estimates the state value V(s) ---
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1)
        )

    def forward(self, state_sequence: torch.Tensor,
                pae_latent: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with temporal-predictive fusion.

        Args:
            state_sequence (torch.Tensor): Temporal sequence of states
                [batch_size, seq_len, n_observations].
            pae_latent (torch.Tensor): Latent vector from the shared PAE
                [batch_size, pae_latent_dim].

        Returns:
            torch.Tensor: Q-values for each action [batch_size, n_actions].
        """
        # --- 1. TCN: Extract temporal features ---
        # TCN expects [batch, channels, seq_len]
        x = state_sequence.transpose(1, 2)
        temporal_out = self.tcn(x)  # [batch, hidden_size, seq_len]

        # Get only the last timestep (causal output)
        temporal_features = temporal_out[:, :, -1]  # [batch, hidden_size]

        # --- 2. Fusion: Temporal + PAE Latent ---
        fused = torch.cat([temporal_features, pae_latent], dim=-1)  # [batch, hidden + latent]
        fused = self.fusion_layer(fused)  # [batch, hidden_size]

        # --- 3. Dueling: Value/Advantage separation ---
        advantages = self.advantage_stream(fused)  # [batch, n_actions]
        value = self.value_stream(fused)  # [batch, 1]

        # Q(s, a) = V(s) + (A(s, a) - mean(A(s, a')))
        q_values = value + (advantages - advantages.mean(dim=1, keepdim=True))

        return q_values
