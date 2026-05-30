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

# File: src/core/learning_coordinator.py (MODIFIED FOR FULL TRANSLATION)
# Author: Gabriel Moraes
# Date: October 3, 2025

import torch
import logging
from typing import TYPE_CHECKING

from engine.ppo_optimizer import PPOOptimizer

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class LearningCoordinator:
    """
    Encapsulates the formulation of the Reinforcement Learning Cycle correctly.
    (HFT Refactored for SOLID Compliance).
    """
    def __init__(self, agents: dict, state_history: dict, locale_manager: 'LocaleManagerBackend', hyperparams: dict = None, shared_pae = None):
        """
        Inicializa o Coordenador de Aprendizado.
        """
        self.agents = agents
        self.state_history = state_history
        self.locale_manager = locale_manager
        self.shared_pae = shared_pae
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == 'cuda'))
        
        # Dependency Inversion: Extract dynamic hyperparams safely
        if not hyperparams and agents:
            first_agent = list(agents.values())[0]
            if hasattr(first_agent, 'hyperparams'):
                hyperparams = first_agent.hyperparams
                
        self.ppo_optimizer = PPOOptimizer(hyperparams or {}, self.device, self.scaler)
        
        # Initializes TensorBoard Metrics (Moved from LocalAgent)
        from utils.paths import get_base_output_dir
        import os
        from datetime import datetime
        log_dir = os.path.join(get_base_output_dir(), "logs", "rl_metrics", datetime.now().strftime("%Y%m%d-%H%M%S"))
        from torch.utils.tensorboard import SummaryWriter
        os.makedirs(log_dir, exist_ok=True)
        self.writer = SummaryWriter(log_dir)

        logging.info(self.locale_manager.get_string("learning_coordinator.init.created", fallback="LearningCoordinator created."))

    def store_experience(self, last_decision_data: dict, rewards: dict, done: bool):
        """
        Stores each agent's experience in their respective memory buffer.
        """
        for tl_id, agent in self.agents.items():
            if tl_id in last_decision_data:
                data = last_decision_data[tl_id]
                
                base_reward = rewards.get(tl_id, 0)
                policy_bonus = getattr(agent, 'current_reward_bonus', 0.0)
                final_reward = base_reward + policy_bonus
                
                if hasattr(agent, 'push_memory'):
                    agent.push_memory(
                        state_sequence=data['state_sequence'],
                        action=data['action'],
                        log_prob=data['log_prob'],
                        reward=final_reward,
                        done=done,
                        state_value=data['state_val']
                    )

    def update_agents(self, last_states: dict, last_done: bool):
        """
        Commands all agents to learn from their memories using PPO.
        Orchestrates the global PAE physics engine model sequentially.
        """
        logging.debug(self.locale_manager.get_string("learning_coordinator.update.trigger", fallback="Updating agents."))
        
        pae_loss_sum = 0.0
        pae_batches_trained = 0
        
        for tl_id, agent in self.agents.items():
            if hasattr(agent, 'memory') and len(agent.memory) > 0:
                # Extracts raw transition data directly from agent's memory abstraction
                if hasattr(agent.memory, 'get_batch'):
                    old_states, old_actions, old_log_probs, rewards, dones, old_state_values = agent.memory.get_batch()
                else:
                    return # Fallback for Guardian memory style (Replay buffer vs OnPolicy)
                    
                # 1. Strategy Invocation (PPO Mathematical update)
                memory_batch = (old_states, old_actions, old_log_probs, rewards, dones, old_state_values)
                
                total_loss = self.ppo_optimizer.step(
                    policy_net=agent.policy_net,
                    optimizer=agent.optimizer,
                    memory_batch=memory_batch,
                    evaluate_fn=agent.evaluate
                )
                
                agent.steps_done += 1
                self.writer.add_scalar(f'Treinamento/Loss_Total_{tl_id}', total_loss, agent.steps_done)
                
                # 2. Universal Batch Training for Physics Engine
                if self.shared_pae is not None and len(old_states) > 1:
                    for t in range(len(old_states) - 1):
                        current_frame = old_states[t][:, -1, :].to(self.device) if old_states[t].dim() == 3 else old_states[t].to(self.device)
                        next_frame = old_states[t + 1][:, -1, :].to(self.device) if old_states[t + 1].dim() == 3 else old_states[t + 1].to(self.device)
                        
                        pae_loss_sum += self.shared_pae.training_step(current_frame, next_frame)
                        pae_batches_trained += 1
                
                agent.memory.clear()

        # 3. Collective TensorBoard Logging
        if self.shared_pae is not None and pae_batches_trained > 0:
            avg_pae_loss = pae_loss_sum / pae_batches_trained
            most_advanced_step = max((getattr(a, 'steps_done', 0) for a in self.agents.values()), default=0)
            self.writer.add_scalar('Treinamento/PAE_Loss_Global', avg_pae_loss, most_advanced_step)