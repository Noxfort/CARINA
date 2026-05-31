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

# File: src/engine/dqn_optimizer.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import torch
import torch.nn as nn
from typing import Callable, Dict, Any, Optional


class DQNOptimizer:
    """
    Executes the Reinforcement Learning Dueling DQN logic.
    Abstracted strictly to adhere to the Single Responsibility Principle (SOLID).
    """
    def __init__(self, hyperparams: Dict[str, Any], device: torch.device, scaler: Optional[torch.amp.GradScaler] = None) -> None:
        """
        Initializes the DQN Strategy instance.
        """
        self.device = device
        self.scaler = scaler or torch.amp.GradScaler(enabled=False)
        self.load_hyperparameters(hyperparams)

    def load_hyperparameters(self, hyperparams: Dict[str, Any]) -> None:
        """Updates internal RL hyperparameters without destroying the object."""
        self.gamma = float(hyperparams.get('gamma', 0.90))
        self.batch_size = int(hyperparams.get('batch_size', 128))

    def step(self, policy_net: nn.Module, target_net: nn.Module, optimizer: torch.optim.Optimizer, 
             memory: Any, forward_policy: Callable, forward_target: Callable) -> float:
        """
        Executes a Q-Learning optimization step (Off-Policy) using Double DQN and PER.
        
        Args:
            policy_net: The active inference network.
            target_net: The target tracking network (frozen).
            optimizer: The optimizer tied to the policy network parameters.
            memory: The replay memory buffer representing the agent's experiences.
            forward_policy: A delegate `fn(states_tensor)` returning active Q-values.
            forward_target: A delegate `fn(states_tensor)` returning target Q-values.
            
        Returns:
            float: The regression loss value.
        """
        if len(memory) < self.batch_size:
            return 0.0
            
        # Native VRAM sampling (Zero PCIe mapping overhead) with PER support
        sample_result = memory.sample(self.batch_size)
        if sample_result is None:
            return 0.0
            
        state_batch, action_batch, next_states_batch, non_final_mask, reward_batch, indices, is_weights = sample_result
        
        # Only non-terminal masks are valid
        non_final_next_states = next_states_batch[non_final_mask]

        optimizer.zero_grad()
        
        # Mixed precision and loss formulation
        with torch.amp.autocast(device_type=self.device.type, enabled=self.scaler.is_enabled()):
            # Generates current Q values and selects the expected action using gather
            state_action_values = forward_policy(state_batch).gather(1, action_batch)
            
            # Targets initialization
            next_state_values = torch.zeros(self.batch_size, device=self.device)
            
            with torch.no_grad():
                if non_final_mask.any():
                    # --- D3QN: Double DQN Logic ---
                    # 1. Main network selects the best action for the next state
                    next_state_actions = forward_policy(non_final_next_states).max(1)[1].unsqueeze(1)
                    # 2. Target network evaluates the value of the chosen action
                    next_state_values[non_final_mask] = forward_target(non_final_next_states).gather(1, next_state_actions).squeeze(1).float()
            
            # Target = r + (gamma * Q_target(s', argmax_a Q_main(s', a))) -> Double DQN value
            expected_state_action_values = (next_state_values * self.gamma) + reward_batch
            
            # Calculate Absolute TD Error for PER updates
            td_errors = torch.abs(state_action_values - expected_state_action_values.unsqueeze(1)).detach()
            
            # Smooth L1 Huber Loss with Importance Sampling weights (PER)
            # reduction='none' ensures we can multiply by is_weights before mean
            unweighted_loss = nn.SmoothL1Loss(reduction='none')(state_action_values, expected_state_action_values.unsqueeze(1))
            loss = (unweighted_loss * is_weights.unsqueeze(1)).mean()

        # Backward pass
        self.scaler.scale(loss).backward()
        torch.nn.utils.clip_grad_norm_(policy_net.parameters(), 1.0)
        self.scaler.step(optimizer)
        self.scaler.update()
        
        # Update PER priorities in memory
        memory.update_priorities(indices, td_errors.squeeze(1))
        
        return loss.item()

    def update_target_net(self, policy_net: nn.Module, target_net: nn.Module) -> None:
        """Hard override of target parameters from policy parameters."""
        target_net.load_state_dict(policy_net.state_dict())
