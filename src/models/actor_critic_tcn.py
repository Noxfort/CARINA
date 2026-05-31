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

# File: src/models/actor_critic_tcn.py (NEW FILE - TCN Implementation)
# Author: Gabriel Moraes
# Date: November 22, 2025

import torch
import torch.nn as nn
from torch.distributions import Categorical
from torch.nn.utils import weight_norm
from typing import Tuple, List, Optional, Any

class Chomp1d(nn.Module):
    """
    Removes extra right padding to ensure causality.
    This ensures that the output at t depends only on inputs t, t-1, ...
    """
    def __init__(self, chomp_size: int) -> None:
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x[:, :, :-self.chomp_size].contiguous()

class TemporalBlock(nn.Module):
    """
    Um bloco residual TCN padrão consistindo de duas convoluções dilatadas,
    normalização de peso, ReLU, Dropout e corte (Chomp).
    """
    def __init__(self, n_inputs: int, n_outputs: int, kernel_size: int, stride: int, dilation: int, padding: int, dropout: float = 0.2) -> None:
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

    def init_weights(self) -> None:
        self.conv1.weight.data.normal_(0, 0.01)
        self.conv2.weight.data.normal_(0, 0.01)
        if self.downsample is not None:
            self.downsample.weight.data.normal_(0, 0.01)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TemporalConvNet(nn.Module):
    """
    A rede TCN completa, composta por uma pilha de TemporalBlocks.
    """
    def __init__(self, num_inputs: int, num_channels: List[int], kernel_size: int = 2, dropout: float = 0.2) -> None:
        super(TemporalConvNet, self).__init__()
        layers: List[nn.Module] = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = num_inputs if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            layers += [TemporalBlock(in_channels, out_channels, kernel_size, stride=1,
                                     dilation=dilation_size,
                                     padding=(kernel_size-1) * dilation_size, dropout=dropout)]

        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)

class ActorCriticNet(nn.Module):
    """
    Actor-Critic network using TCN as the base for temporal processing.
    Replaces the LSTM-based version while maintaining I/O compatibility.
    """
    def __init__(self, n_observations: int, n_actions: int, hidden_size: int = 128, dropout_p: float = 0.1) -> None:
        super(ActorCriticNet, self).__init__()
        
        # TCN Configuration
        # We define 2 levels with hidden_size channels each.
        # This creates a reasonable receptive field for short/medium sequences.
        num_channels = [hidden_size, hidden_size]
        kernel_size = 3
        
        # TCN processes the temporal dimension
        self.tcn = TemporalConvNet(n_observations, num_channels, kernel_size=kernel_size, dropout=dropout_p)
        
        # Processing layers after TCN
        self.post_tcn_layer = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_p)
        )
        
        # Actor Head (Policy): Determines the probability of each action
        self.actor_head = nn.Sequential(
            nn.Linear(hidden_size, n_actions),
            nn.Softmax(dim=-1)
        )
        
        # Critical Head (Value): Estimates the value of the current state
        self.critic_head = nn.Sequential(
            nn.Linear(hidden_size, 1)
        )

    def forward(self, state_sequence: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            state_sequence: Tensor [batch_size, sequence_length, n_observations]
        Returns:
            tuple: (action_probs, state_value)
        """
        # The TCN expects input in the format [batch_size, channels (n_obs), sequence_length]
        # We need to transpose the input, as the PPO sends [batch, seq, obs]
        x = state_sequence.transpose(1, 2)
        
        # Pass through TCN
        y = self.tcn(x) 
        # Output y: [batch_size, hidden_size, sequence_length]
        
        # We only take the output of the last time step (equivalent to LSTM output[-1])
        # This represents the encoding of all history up to the present moment.
        last_timestep = y[:, :, -1]
        
        # Final processing
        features = self.post_tcn_layer(last_timestep)
        
        # Heads
        action_probs = self.actor_head(features)
        state_value = self.critic_head(features)
        
        return action_probs, state_value