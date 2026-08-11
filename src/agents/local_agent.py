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
from src.utils.local_agent_helpers import PAEStateAugmentor, AgentCheckpointManager, AgentHyperparameterManager


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
        self.pae_augmentor = PAEStateAugmentor(shared_pae)
        self.pae_latent_dim = self.pae_augmentor.latent_dim
        
        self.hyperparams = initial_hyperparams
        self._load_hyperparameters()
        
        self._build_network()
        self._create_optimizer()
        
        self.memory = OnPolicyBuffer()
        seq_len = self.hyperparams.get('sequence_length', 4)
        state_shape = (seq_len, self.n_observations)
        self.xai_memory = ReplayMemory(capacity=200, state_shape=state_shape, device=torch.device('cpu'))
        
        self.current_reward_bonus = 0.0

        self.steps_done = 0
        self.episodes_done = 0
        
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == 'cuda'))
        
        # --- Thinking Mode Cache (Decision Trigger on State Change) ---
        self._last_raw_state: Optional[torch.Tensor] = None
        self._last_decision: Optional[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]] = None
        
        if self.shared_pae:
            logging.info(self.locale_manager.get_string("local_agent.init.pae_integrated", default="[LocalAgent {id}] Integrated PAE (latent_dim={dim})", id=self.id, dim=self.pae_latent_dim))
        
    @property
    def shared_pae(self) -> Optional[PredictiveAutoencoder]:
        return self.pae_augmentor.shared_pae

    @shared_pae.setter
    def shared_pae(self, value: Optional[PredictiveAutoencoder]) -> None:
        self.pae_augmentor.shared_pae = value

    def _load_hyperparameters(self) -> None:
        """Loads hyperparameters from a dictionary."""
        AgentHyperparameterManager.load(self)

    def update_hyperparameters(self, new_hyperparams: Dict[str, Any]) -> None:
        """Updates hyperparameters and recreates the network and optimizer (for PBT)."""
        AgentHyperparameterManager.update(self, new_hyperparams)

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
        AgentCheckpointManager.save(self, filepath, maturity_stage)

    def load_checkpoint(self, filepath: str) -> str:
        """
        Loads the agent's state from a checkpoint file.
        
        Returns:
            str: The name of the maturity stage retrieved from the file (e.g., 'CHILD', 'TEEN'). 
                 Returns 'CHILD' if not found.
        """
        return AgentCheckpointManager.load(self, filepath)

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
        
        # Reset thinking mode cache on episode done
        if done:
            self._last_raw_state = None
            self._last_decision = None

    def _augment_with_pae(self, state_tensor: torch.Tensor) -> torch.Tensor:
        """
        PAE Orchestration: Projects the last timestep into the latent space and
        concatenates the latent vector into each frame of the temporal sequence.
        
        Args:
            state_tensor: [batch, seq_len, n_observations]
        Returns:
            Augmented tensor [batch, seq_len, n_observations + latent_dim]
        """
        return self.pae_augmentor.augment(state_tensor)

    def choose_action(self, state_tensor: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Takes a decision based on a sequence tensor of states, augmented by the PAE.
        
        Implements a "Thinking Mode" decision cache: runs neural network inference
        only when new data (state change) arrives, otherwise reusing the previous decision.
        """
        is_batch_one = False
        current_raw = None
        
        # Check if we are using DummyTensor (mocked torch in tests)
        if type(state_tensor).__name__ == "DummyTensor":
            is_batch_one = True
            current_raw = state_tensor._data
        elif hasattr(state_tensor, "size") and state_tensor.size(0) == 1:
            is_batch_one = True
            current_raw = state_tensor[0, -1]
            
        if is_batch_one and current_raw is not None:
            cache_hit = False
            if self._last_raw_state is not None and self._last_decision is not None:
                if isinstance(current_raw, torch.Tensor) and isinstance(self._last_raw_state, torch.Tensor):
                    cache_hit = torch.allclose(current_raw, self._last_raw_state, atol=1e-6)
                else:
                    cache_hit = (current_raw == self._last_raw_state)
            
            if cache_hit:
                return self._last_decision
            
            if isinstance(current_raw, torch.Tensor):
                self._last_raw_state = current_raw.clone()
            else:
                self._last_raw_state = current_raw

        state_tensor = self._augment_with_pae(state_tensor)
        
        with torch.no_grad():
            action_probs, state_val = self.policy_net(state_tensor)
            
            dist = Categorical(action_probs)
            action = dist.sample()
            action_log_prob = dist.log_prob(action)
            dist_entropy = dist.entropy()
            
        decision = (action, action_log_prob, state_val, dist_entropy)
        if is_batch_one:
            self._last_decision = decision
            
        return decision



    def evaluate(self, state_sequence_batch: torch.Tensor, action: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Re-evaluates actions for the data batch during learning (with PAE fusion)."""
        state_sequence_batch = self._augment_with_pae(state_sequence_batch)
        action_probs, state_values = self.policy_net(state_sequence_batch)
        dist = Categorical(action_probs)
        action_log_probs = dist.log_prob(action.squeeze())
        dist_entropy = dist.entropy()
        return action_log_probs, torch.squeeze(state_values), dist_entropy