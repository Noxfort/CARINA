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

# File: src/memory/replay_memory.py (NEW FILE)
# Author: Gabriel Moraes
# Date: August 19, 2025

"""
Defines the ReplayMemory class and its Transition data structure.

This module, extracted from 'guardian_agent.py', implements a replay memory buffer,
a crucial data structure for "off-policy" reinforcement learning algorithms like DQN.
It stores the agent's experiences and allows the sampling of random batches to break
the temporal correlation between samples, stabilizing the training process.
"""
import torch

class ReplayMemory:
    """
    VRAM-Native Pre-allocated PyTorch Tensor Memory.
    Eliminates PCIe transit bottlenecks for HFT architecture.
    Provides O(1) device-side sampling and zero Python-side looping.
    """
    def __init__(self, capacity: int, state_shape: tuple, device: torch.device, alpha: float = 0.6, beta: float = 0.4):
        """
        Initializes the buffer pre-allocating contiguous memory chunks with Prioritized Experience Replay (PER).
        """
        self.capacity = capacity
        self.device = device
        self.state_shape = state_shape
        
        # PER Parameters
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = 0.001  # Used to anneal beta to 1 over time
        self.eps = 1e-6 # small constant to avoid zero priority
        
        # Precompute massive tensors mapping directly into GPU Memory (VRAM)
        self.states = torch.zeros((capacity, *state_shape), device=self.device, dtype=torch.float32)
        # Assuming action is a scalar integer (wrapped in tensor natively)
        self.actions = torch.zeros((capacity, 1), device=self.device, dtype=torch.long)
        self.next_states = torch.zeros((capacity, *state_shape), device=self.device, dtype=torch.float32)
        self.rewards = torch.zeros((capacity, 1), device=self.device, dtype=torch.float32)
        
        # Boolean mask to identify non-terminal states
        self.non_final_mask = torch.zeros((capacity, 1), device=self.device, dtype=torch.bool)
        
        # PER Priorities Array
        self.priorities = torch.zeros((capacity,), device=self.device, dtype=torch.float32)
        
        self.ptr = 0
        self.size = 0

    def push(self, state, action, next_state, reward):
        """
        Inserts a transition at the current pointer natively into VRAM with max priority.
        Inputs should preferably be PyTorch Tensors already on the device.
        """
        state_t = state if isinstance(state, torch.Tensor) else torch.tensor(state, device=self.device, dtype=torch.float32)
        action_t = action if isinstance(action, torch.Tensor) else torch.tensor([action], device=self.device, dtype=torch.long)
        reward_t = reward if isinstance(reward, torch.Tensor) else torch.tensor([reward], device=self.device, dtype=torch.float32)
        
        self.states[self.ptr] = state_t
        self.actions[self.ptr] = action_t.view(1)
        self.rewards[self.ptr] = reward_t.view(1)
        
        if next_state is not None:
            next_state_t = next_state if isinstance(next_state, torch.Tensor) else torch.tensor(next_state, device=self.device, dtype=torch.float32)
            self.next_states[self.ptr] = next_state_t
            self.non_final_mask[self.ptr] = True
        else:
            self.non_final_mask[self.ptr] = False
            
        # PER: New transitions are inserted with max priority to guarantee they are sampled at least once
        max_prio = self.priorities.max() if self.size > 0 else 1.0
        self.priorities[self.ptr] = max_prio
            
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int) -> tuple:
        """
        VRAM-Native Prioritized Experience Replay Sampling.
        Returns tuple of pre-batched tensors: (states, actions, next_states, non_final_mask, rewards, indices, is_weights)
        """
        if self.size == 0:
            return None
            
        # 1. Calculate probabilities: p_i = p_i^alpha / sum(p_i^alpha)
        # Using native VRAM operations for stochastic PER sampling
        valid_priorities = self.priorities[:self.size]
        probs = valid_priorities ** self.alpha
        probs /= probs.sum()
        
        # 2. Sample indices based on probabilities natively on GPU
        indices = torch.multinomial(probs, batch_size, replacement=True)
        
        # 3. Calculate Importance Sampling (IS) weights
        # w_i = (N * P(i)) ^ -beta
        # Normalize weights by max weight for stability
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        is_weights = (self.size * probs[indices]) ** (-self.beta)
        is_weights /= is_weights.max() # Normalize
        
        return (
            self.states[indices],
            self.actions[indices],
            self.next_states[indices],
            self.non_final_mask[indices].squeeze(1),
            self.rewards[indices].squeeze(1),
            indices,
            is_weights
        )
        
    def update_priorities(self, indices: torch.Tensor, td_errors: torch.Tensor):
        """
        Updates the priorities for the sampled batch based on the TD-Error.
        """
        # Absolute TD-error + epsilon (to avoid 0 probability)
        new_priorities = torch.abs(td_errors) + self.eps
        # Clip max priority to avoid extreme spikes (optional but safe)
        self.priorities[indices] = new_priorities.detach().float()

    def __len__(self) -> int:
        return self.size