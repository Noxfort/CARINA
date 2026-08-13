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

# File: src/utils/local_agent_helpers.py
# Author: Gabriel Moraes
# Date: July 18, 2026

import os
import logging
import numpy as np
import torch
import torch.nn as nn
from typing import TYPE_CHECKING, Optional, Dict, Any, Tuple
from src.memory.replay_memory import ReplayMemory

if TYPE_CHECKING:
    from src.agents.local_agent import LocalAgent


class PAEStateAugmentor:
    """Handles PAE projection and sequence state augmentation."""
    def __init__(self, shared_pae: Optional[Any] = None) -> None:
        self.shared_pae = shared_pae
        self.latent_dim = shared_pae.latent_dim if shared_pae else 0

    def augment(self, state_tensor: torch.Tensor) -> torch.Tensor:
        if self.shared_pae is None:
            return state_tensor
        
        with torch.no_grad():
            latent = self.shared_pae.encode(state_tensor)  # [batch, latent_dim]
            latent_expanded = latent.unsqueeze(1).expand(
                -1, state_tensor.size(1), -1
            )  # [batch, seq_len, latent_dim]
            return torch.cat([state_tensor, latent_expanded], dim=-1)


class AgentHyperparameterManager:
    """Manages hyperparameters and applies them to networks and optimizers."""
    
    @staticmethod
    def load(agent: 'LocalAgent') -> None:
        agent.gamma = float(agent.hyperparams.get('gamma', 0.99))
        agent.gae_lambda = float(agent.hyperparams.get('gae_lambda', 0.95))
        agent.learning_rate = float(agent.hyperparams.get('learning_rate', 0.0001))
        agent.eps_clip = float(agent.hyperparams.get('eps_clip', 0.2))
        agent.k_epochs = int(agent.hyperparams.get('k_epochs', 4))
        agent.target_kl = float(agent.hyperparams.get('target_kl', 0.02))
        agent.grad_clip_norm = float(agent.hyperparams.get('grad_clip_norm', 0.5))
        agent.dropout_p = float(agent.hyperparams.get('dropout_p', 0.1))
        agent.critic_loss_coef = 0.5

    @staticmethod
    def update(agent: 'LocalAgent', new_hyperparams: Dict[str, Any]) -> None:
        agent.hyperparams = new_hyperparams
        AgentHyperparameterManager.load(agent)
        if agent.optimizer:
            agent.optimizer.param_groups[0]['lr'] = agent.learning_rate
        if agent.policy_net:
            for module in agent.policy_net.modules():
                if isinstance(module, nn.Dropout):
                    module.p = agent.dropout_p


class AgentCheckpointManager:
    """Handles serialization and deserialization of local agent states."""
    
    @staticmethod
    def save(agent: 'LocalAgent', filepath: str, maturity_stage: str) -> None:
        checkpoint = {
            'episodes_done': agent.episodes_done, 
            'steps_done': agent.steps_done,
            'policy_net_state_dict': agent.policy_net.state_dict(),
            'optimizer_state_dict': agent.optimizer.state_dict(),
            'hyperparameters': agent.hyperparams,
            'xai_memory': agent.xai_memory,
            'n_observations': agent.n_observations,
            'maturity_stage': maturity_stage
        }
        torch.save(checkpoint, filepath)
        try:
            from database.database_manager import DatabaseManager
            from utils.paths import get_base_output_dir
            db = getattr(agent, 'db_manager', None) or DatabaseManager(agent.locale_manager)
            base_dir = os.path.join(get_base_output_dir(), "results")
            db.sync_file_to_vault(filepath, base_dir)
        except Exception:
            pass

    @staticmethod
    def load(agent: 'LocalAgent', filepath: str) -> str:
        lm = agent.locale_manager
        saved_maturity = "CHILD"

        # If file is not present on disk, attempt auto-restoration from PostgreSQL Cloud Vault
        if not os.path.exists(filepath):
            try:
                from database.database_manager import DatabaseManager
                from utils.paths import get_base_output_dir
                db = getattr(agent, 'db_manager', None) or DatabaseManager(lm)
                base_dir = os.path.join(get_base_output_dir(), "results")
                rel_path = os.path.relpath(filepath, base_dir)
                db.restore_file_from_vault(rel_path, filepath)
            except Exception as e:
                logging.warning(f"[AgentCheckpointManager] Vault restoration check error for {filepath}: {e}")

        try:
            checkpoint = torch.load(filepath, map_location=agent.device, weights_only=False)
            
            # Observation compatibility check
            if agent.n_observations != checkpoint.get('n_observations'):
                logging.warning(lm.get_string(
                    "local_agent.load.obs_mismatch_warning", 
                    agent_id=agent.id, 
                    chk_obs=checkpoint.get('n_observations'), 
                    cur_obs=agent.n_observations
                ))
            
            saved_maturity = checkpoint.get('maturity_stage', "CHILD")
            
            # Dynamic Dimension Fallback & Auto-Adaptation
            should_load_weights = True
            try:
                state_dict = checkpoint['policy_net_state_dict']
                in_channels = state_dict['tcn.network.0.conv1.weight_v'].shape[1]
                expected_channels = agent.n_observations + getattr(agent, 'pae_latent_dim', 0)
                if in_channels != expected_channels:
                    latent_diff = in_channels - agent.n_observations
                    if latent_diff > 0:
                        logging.info(f"[LocalAgentHelpers] Auto-adapting PAE latent dimension to {latent_diff} for agent {agent.id} (matching {in_channels} channels).")
                        agent.pae_latent_dim = latent_diff
                        agent._build_network()
                        agent._create_optimizer()
                    else:
                        logging.warning(lm.get_string(
                            "local_agent.load.dim_mismatch",
                            default="Dimension mismatch detected: checkpoint weight has {fnd} channels but current model expects {exp} channels. Skipping policy weights loading.",
                            exp=expected_channels,
                            fnd=in_channels
                        ))
                        should_load_weights = False
                        agent._build_network()
                        agent._create_optimizer()
            except KeyError:
                pass

            agent.update_hyperparameters(checkpoint['hyperparameters'])
            if should_load_weights:
                agent.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
                agent.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            agent.episodes_done = checkpoint.get('episodes_done', 0)
            agent.steps_done = checkpoint.get('steps_done', 0)

            loaded_xai_memory = checkpoint.get('xai_memory')
            if loaded_xai_memory:
                if getattr(loaded_xai_memory, 'capacity', 0) > 200:
                    new_mem = ReplayMemory(capacity=200, state_shape=agent.xai_memory.state_shape, device=torch.device('cpu'))
                    num_to_copy = min(loaded_xai_memory.size, 200)
                    for i in range(num_to_copy):
                        idx = (loaded_xai_memory.ptr - num_to_copy + i) % loaded_xai_memory.capacity
                        st = loaded_xai_memory.states[idx].cpu()
                        act = loaded_xai_memory.actions[idx].cpu()
                        rew = loaded_xai_memory.rewards[idx].cpu()
                        new_mem.push(st, act, None, rew)
                    agent.xai_memory = new_mem
                else:
                    agent.xai_memory = loaded_xai_memory
                    agent.xai_memory.device = torch.device('cpu')
                    agent.xai_memory.states = agent.xai_memory.states.cpu()
                    agent.xai_memory.actions = agent.xai_memory.actions.cpu()
                    agent.xai_memory.next_states = agent.xai_memory.next_states.cpu()
                    agent.xai_memory.rewards = agent.xai_memory.rewards.cpu()
                    agent.xai_memory.non_final_mask = agent.xai_memory.non_final_mask.cpu()
                    agent.xai_memory.priorities = agent.xai_memory.priorities.cpu()
            
            agent.policy_net.train()
            agent._last_raw_state = None
            agent._last_decision = None
            logging.info(lm.get_string(
                "local_agent.load.success", 
                agent_id=agent.id, 
                path=filepath, 
                count=len(agent.xai_memory)
            ))
            
        except FileNotFoundError:
            logging.warning(lm.get_string("local_agent.load.not_found_warning", agent_id=agent.id, path=filepath))
        except Exception as e:
            logging.error(lm.get_string("local_agent.load.error", agent_id=agent.id, error=e), exc_info=True)
            
        return saved_maturity
