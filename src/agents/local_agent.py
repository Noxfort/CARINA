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

# File: src/agents/local_agent.py
# Author: Gabriel Moraes
# Date: February 17, 2026

import torch
import torch.nn as nn
from torch.distributions import Categorical
import torch.optim as optim

import logging
import numpy as np
from typing import TYPE_CHECKING, Optional, Dict, Any, List, Tuple
from src.models.pae import PredictiveAutoencoder

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend

from src.models.actor_critic_tcn import ActorCriticNet
from src.memory.on_policy_buffer import OnPolicyBuffer
from src.memory.replay_memory import ReplayMemory


class LocalAgent:
    """
    The tactical agent that controls a single traffic light using the PPO algorithm.
    Utilizes a TCN (Temporal Convolutional Network) to process
    the temporal sequence of states.
    """
    def __init__(self, tlight_id: str, n_observations: int, n_actions: int, initial_hyperparams: Dict[str, Any], log_dir: str, locale_manager: 'LocaleManagerBackend', shared_pae: Optional[PredictiveAutoencoder] = None) -> None:
        self.id = tlight_id
        self.n_actions = n_actions
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.n_observations = n_observations
        self.locale_manager = locale_manager
        
        # --- Universal PAE (Shared Physics Engine) ---
        self.shared_pae = shared_pae
        self.pae_latent_dim = shared_pae.latent_dim if shared_pae else 0
        
        self.hyperparams = initial_hyperparams
        self._load_hyperparameters()
        
        self._build_network()
        self._create_optimizer()
        
        self.memory = OnPolicyBuffer()
        seq_len = self.hyperparams.get('sequence_length', 4)
        state_shape = (seq_len, self.n_observations)
        self.xai_memory = ReplayMemory(capacity=5000, state_shape=state_shape, device=self.device)
        
        self.current_reward_bonus = 0.0

        self.steps_done = 0
        self.episodes_done = 0
        
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == 'cuda'))
        
        if self.shared_pae:
            logging.info(self.locale_manager.get_string("local_agent.init.pae_integrated", default="[LocalAgent {id}] Integrated PAE (latent_dim={dim})", id=self.id, dim=self.pae_latent_dim))
        
    def _load_hyperparameters(self) -> None:
        """Loads hyperparameters from a dictionary."""
        self.gamma = float(self.hyperparams.get('gamma', 0.99))
        self.gae_lambda = float(self.hyperparams.get('gae_lambda', 0.95))
        self.learning_rate = float(self.hyperparams.get('learning_rate', 0.0001))
        self.eps_clip = float(self.hyperparams.get('eps_clip', 0.2))
        self.k_epochs = int(self.hyperparams.get('k_epochs', 4))
        self.target_kl = float(self.hyperparams.get('target_kl', 0.02))
        self.grad_clip_norm = float(self.hyperparams.get('grad_clip_norm', 0.5))
        self.dropout_p = float(self.hyperparams.get('dropout_p', 0.1))
        self.critic_loss_coef = 0.5

    def update_hyperparameters(self, new_hyperparams: Dict[str, Any]) -> None:
        """Updates hyperparameters and recreates the network and optimizer (for PBT)."""
        self.hyperparams = new_hyperparams
        self._load_hyperparameters()
        if self.optimizer:
            self.optimizer.param_groups[0]['lr'] = self.learning_rate
        if self.policy_net:
             for module in self.policy_net.modules():
                if isinstance(module, nn.Dropout):
                    module.p = self.dropout_p

    def _build_network(self) -> None:
        """Instantiates the Actor-Critic network with expanded input to accommodate the PAE latent vector."""
        augmented_input_dim = self.n_observations + self.pae_latent_dim
        self.policy_net = ActorCriticNet(augmented_input_dim, self.n_actions, dropout_p=self.dropout_p).to(self.device)

    def _create_optimizer(self) -> None:
        """Creates the optimizer for the network."""
        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=self.learning_rate)
    
    def save_checkpoint(self, filepath: str, maturity_stage: str = "CHILD") -> None:
        """
        Saves the agent's state to a checkpoint file.
        
        Args:
            filepath (str): Path to save the file.
            maturity_stage (str): The current maturity stage of the agent (CHILD, TEEN, ADULT) for persistence.
        """
        checkpoint = {
            'episodes_done': self.episodes_done, 
            'steps_done': self.steps_done,
            'policy_net_state_dict': self.policy_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'hyperparameters': self.hyperparams,
            'xai_memory': self.xai_memory,
            'n_observations': self.n_observations,
            'maturity_stage': maturity_stage  # Maturity phase persistence
        }
        torch.save(checkpoint, filepath)

    def load_checkpoint(self, filepath: str) -> str:
        """
        Loads the agent's state from a checkpoint file.
        
        Returns:
            str: The name of the maturity stage retrieved from the file (e.g., 'CHILD', 'TEEN'). 
                 Returns 'CHILD' if not found.
        """
        lm = self.locale_manager
        saved_maturity = "CHILD"
        
        try:
            checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)
            
            # Observation compatibility check
            if self.n_observations != checkpoint.get('n_observations'):
                logging.warning(lm.get_string(
                    "local_agent.load.obs_mismatch_warning", 
                    agent_id=self.id, 
                    chk_obs=checkpoint.get('n_observations'), 
                    cur_obs=self.n_observations
                ))
            
            # Retrieves the saved maturity (default CHILD if it does not exist)
            saved_maturity = checkpoint.get('maturity_stage', "CHILD")
            
            self.update_hyperparameters(checkpoint['hyperparameters'])
            self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.episodes_done = checkpoint.get('episodes_done', 0)
            self.steps_done = checkpoint.get('steps_done', 0)

            loaded_xai_memory = checkpoint.get('xai_memory')
            if loaded_xai_memory:
                self.xai_memory = loaded_xai_memory
            
            self.policy_net.train()
            logging.info(lm.get_string(
                "local_agent.load.success", 
                agent_id=self.id, 
                path=filepath, 
                count=len(self.xai_memory)
            ))
            
        except FileNotFoundError:
            logging.warning(lm.get_string("local_agent.load.not_found_warning", agent_id=self.id, path=filepath))
        except Exception as e:
            logging.error(lm.get_string("local_agent.load.error", agent_id=self.id, error=e), exc_info=True)
            
        return saved_maturity

    def push_memory(self, state_sequence: List[List[float]], action: torch.Tensor, log_prob: torch.Tensor, reward: float, done: bool, state_value: torch.Tensor) -> None:
        """Adds a transition to the agent's memories."""
        self.memory.push(
            state_sequence, 
            action.cpu().numpy(),
            log_prob.cpu().numpy(), 
            np.float32(reward), 
            done, 
            state_value.cpu().numpy().flatten()
        )
        state_for_xai = np.array(state_sequence, dtype=np.float32)
        # XAI memory only extracts states for analysis; provide dummies for action and reward
        self.xai_memory.push(state_for_xai, 0, None, 0.0)

    def _augment_with_pae(self, state_tensor: torch.Tensor) -> torch.Tensor:
        """
        PAE Orchestration: Projects the last timestep into the latent space and
        concatenates the latent vector into each frame of the temporal sequence.
        
        Args:
            state_tensor: [batch, seq_len, n_observations]
        Returns:
            Augmented tensor [batch, seq_len, n_observations + latent_dim]
        """
        if self.shared_pae is None:
            return state_tensor
        
        with torch.no_grad():
            # Extract last timestep as current context
            last_frame = state_tensor[:, -1, :]  # [batch, n_obs]
            latent = self.shared_pae.encode(last_frame)  # [batch, latent_dim]
            # Expand latent for the entire temporal sequence
            latent_expanded = latent.unsqueeze(1).expand(
                -1, state_tensor.size(1), -1
            )  # [batch, seq_len, latent_dim]
            # Concatenate to the original state
            return torch.cat([state_tensor, latent_expanded], dim=-1)

    def choose_action(self, state_tensor: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Takes a decision based on a sequence tensor of states, augmented by the PAE."""
        state_tensor = self._augment_with_pae(state_tensor)
        
        with torch.no_grad():
            action_probs, state_val = self.policy_net(state_tensor)
            
            dist = Categorical(action_probs)
            action = dist.sample()
            action_log_prob = dist.log_prob(action)
            dist_entropy = dist.entropy()
            
        return action, action_log_prob, state_val, dist_entropy



    def evaluate(self, state_sequence_batch: torch.Tensor, action: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Re-evaluates actions for the data batch during learning (with PAE fusion)."""
        state_sequence_batch = self._augment_with_pae(state_sequence_batch)
        action_probs, state_values = self.policy_net(state_sequence_batch)
        dist = Categorical(action_probs)
        action_log_probs = dist.log_prob(action.squeeze())
        dist_entropy = dist.entropy()
        return action_log_probs, torch.squeeze(state_values), dist_entropy