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

# File: src/engine/ppo_optimizer.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import torch
import torch.nn as nn
from typing import Callable

class PPOOptimizer:
    """
    Executes the Reinforcement Learning PPO (Proximal Policy Optimization) 
    mathematical logic for continuous and discrete temporal agents.
    Abstracted strictly to adhere to the Single Responsibility Principle (SOLID).
    """
    def __init__(self, hyperparams: dict, device: torch.device, scaler: torch.amp.GradScaler = None):
        """
        Initializes the PPO Strategy instance.
        """
        self.device = device
        self.scaler = scaler or torch.amp.GradScaler(enabled=False)
        self.load_hyperparameters(hyperparams)

    def load_hyperparameters(self, hyperparams: dict):
        """Updates internal RL hyperparameters without destroying the object."""
        self.gamma = float(hyperparams.get('gamma', 0.99))
        self.gae_lambda = float(hyperparams.get('gae_lambda', 0.95))
        self.eps_clip = float(hyperparams.get('eps_clip', 0.2))
        self.k_epochs = int(hyperparams.get('k_epochs', 4))
        self.target_kl = float(hyperparams.get('target_kl', 0.02))
        self.grad_clip_norm = float(hyperparams.get('grad_clip_norm', 0.5))
        self.critic_loss_coef = 0.5

    def step(self, policy_net: nn.Module, optimizer: torch.optim.Optimizer, memory_batch: tuple, evaluate_fn: Callable) -> float:
        """
        Executes a single PPO backpropagation step using Generalized Advantage Estimation.
        
        Args:
            policy_net: The agent's neural network to be optimized.
            optimizer: The optimizer (e.g., AdamW) tied to the policy network parameters.
            memory_batch: A tuple containing (old_states, old_actions, old_log_probs, rewards, dones, old_state_values).
            evaluate_fn: A delegate callback `fn(states, actions)` that triggers a forward pass on the agent's network, returning (log_probs, state_values, entropy).
            
        Returns:
            float: The total loss calculated for this batch update.
        """
        old_states, old_actions, old_log_probs, rewards, dones, old_state_values = memory_batch
        
        # Moves variables to proper tensor device computation
        old_actions = old_actions.to(self.device)
        old_log_probs = old_log_probs.to(self.device)
        old_state_values = old_state_values.to(self.device)

        # 1. Advanced Advantage Calculation (GAE)
        with torch.no_grad():
            last_state_value = old_state_values[-1]
            advantages = torch.zeros_like(torch.tensor(rewards), dtype=torch.float32, device=self.device)
            gae = 0
            for t in reversed(range(len(rewards))):
                is_done = 1.0 - float(dones[t])
                next_value = old_state_values[t+1] if t < len(rewards) - 1 else last_state_value
                delta = rewards[t] + self.gamma * next_value * is_done - old_state_values[t]
                gae = delta + self.gamma * self.gae_lambda * is_done * gae
                advantages[t] = gae
            
            rewards_to_go = advantages + old_state_values
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        total_loss_val = 0.0

        # 2. PPO Clipping iterations (k_epochs)
        for _ in range(self.k_epochs):
            optimizer.zero_grad()
            
            # Using Mixed Precision (AMP) logic
            with torch.amp.autocast(device_type=self.device.type, enabled=self.scaler.is_enabled()):
                new_log_probs, state_values, dist_entropy = evaluate_fn(old_states, old_actions)
                
                # Importance sampling
                ratios = torch.exp(new_log_probs - old_log_probs.detach())
                
                surr1 = ratios * advantages
                surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
                
                actor_loss = -torch.min(surr1, surr2).mean()
                critic_loss = nn.MSELoss()(state_values, rewards_to_go.detach())
                entropy_bonus = -0.01 * dist_entropy.mean()
                
                total_loss = actor_loss + (self.critic_loss_coef * critic_loss) + entropy_bonus
            
            # Gradient application
            self.scaler.scale(total_loss).backward()
            torch.nn.utils.clip_grad_norm_(policy_net.parameters(), self.grad_clip_norm)
            self.scaler.step(optimizer)
            self.scaler.update()
            
            total_loss_val = total_loss.item()
            
            # Early stopping divergence checking via Kullback-Leibler
            with torch.no_grad(): 
                kl_div = torch.mean(old_log_probs.detach() - new_log_probs).item()
            if abs(kl_div) > self.target_kl:
                break
                
        return total_loss_val
