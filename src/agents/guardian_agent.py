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

# File: src/agents/guardian_agent.py
# Author: Gabriel Moraes
# Date: 02/18/2026

import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
import logging
from collections import deque
from typing import TYPE_CHECKING, Optional, Dict, Any, List, Tuple

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend

from src.models.d3qn_tcn import D3QN_TCN
from src.models.pae import PredictiveAutoencoder
from src.memory.replay_memory import ReplayMemory
from src.utils.safety_rules import SafetyRules

class GuardianAgent:
    """
    The Neuro-Symbolic Guardian Agent (HFT Predictive).
    
    Combines a D3QN_TCN (Temporal neural with predictive
    latent space fusion) with dynamic safety rules (Symbolic) loaded from
    settings.ini. Acts as a safety shield, vetoing actions that violate
    engineering constraints (Min Green, Ghost Green).
    
    The shared PAE projects overflow risks (spillback) which
    are fused with the temporal Q-Values for informed decisions.
    """
    
    # Action Constants
    ACTION_KEEP_STAGE = 0
    ACTION_CHANGE_STAGE = 1
    
    # Temporal depth for spillback projection
    TEMPORAL_SEQ_LEN = 8

    def __init__(self, aiconfig: Any, traffic_rules_config: Any, locale_manager: 'LocaleManagerBackend', shared_pae: Optional[PredictiveAutoencoder] = None, n_observations: int = 2) -> None:
        """
        Args:
            aiconfig: Configuration section for AI hyperparameters.
            traffic_rules_config: Configuration section [TRAFFIC_RULES] from settings.ini.
            locale_manager: Backend locale manager.
            shared_pae: Reference to the shared Universal PAE (may be None).
            n_observations: Observation space size.
        """
        self.locale_manager = locale_manager
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_hyperparameters(aiconfig)
        
        # --- Universal PAE (Shared Physics Engine) ---
        self.shared_pae = shared_pae
        self.pae_latent_dim = shared_pae.latent_dim if shared_pae else 0
        
        # --- Temporal Deques (one per tl_id to accumulate sequences) ---
        self.state_deques: Dict[str, deque] = {}
        
        # --- Configurable Safety Rules (Symbolic Layer) ---
        self.green_time = SafetyRules.get_green()
        self.yellow_time = SafetyRules.get_yellow()
        self.all_red_time = SafetyRules.get_all_red()
        self.red_time = SafetyRules.get_red()
        
        logging.info(self.locale_manager.get_string("guardian_agent.init", default="[GUARDIAN] Initialized with Safety Rules -> Green: {green}s | Yellow: {yellow}s | All-Red: {all_red}s | Red: {red}s", green=self.green_time, yellow=self.yellow_time, all_red=self.all_red_time, red=self.red_time))

        # --- Neural Layer (D3QN + TCN + PAE Fusion) ---
        self.n_observations = n_observations
        self.policy_net = D3QN_TCN(
            n_observations=self.n_observations,
            n_actions=2,
            pae_latent_dim=self.pae_latent_dim
        ).to(self.device)
        self.target_net = D3QN_TCN(
            n_observations=self.n_observations,
            n_actions=2,
            pae_latent_dim=self.pae_latent_dim
        ).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=self.learning_rate)
        state_shape = (self.TEMPORAL_SEQ_LEN, self.n_observations)
        self.memory = ReplayMemory(self.memory_size, state_shape=state_shape, device=self.device)
        
        self.steps_done = 0
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == 'cuda'))
        
        pae_status = self.locale_manager.get_string("guardian_agent.pae_with", default="PAE latent={dim}", dim=self.pae_latent_dim) if self.shared_pae else self.locale_manager.get_string("guardian_agent.pae_without", default="without PAE")
        logging.info(self.locale_manager.get_string("guardian_agent.neural_layer", default="[GUARDIAN] Neural Layer: D3QN_TCN ({pae_status}) | AMP: {amp}", pae_status=pae_status, amp=self.scaler.is_enabled()))

    def _load_hyperparameters(self, cfg: Any) -> None:
        """Loads hyperparameters from configuration."""
        self.batch_size = cfg.getint('batch_size', 128)
        self.gamma = cfg.getfloat('gamma', 0.90)
        self.epsilon_start = cfg.getfloat('epsilon_start', 1.0)
        self.epsilon_end = cfg.getfloat('epsilon_end', 0.05)
        self.epsilon_decay = cfg.getint('epsilon_decay', 30000)
        self.learning_rate = cfg.getfloat('learning_rate', 0.00025)
        self.memory_size = cfg.getint('memory_size', 50000)

    def _get_temporal_sequence(self, state: List[float], tl_id: str) -> torch.Tensor:
        """
        Manages the temporal deque for a specific tl_id and returns
        the standardized temporal sequence as a tensor.
        
        Args:
            state: Current state vector of the traffic light.
            tl_id: Traffic light identifier.
        
        Returns:
            Tensor [1, TEMPORAL_SEQ_LEN, n_obs]
        """
        if tl_id not in self.state_deques:
            self.state_deques[tl_id] = deque(maxlen=self.TEMPORAL_SEQ_LEN)
        
        self.state_deques[tl_id].append(state)
        
        # Padding by repeating the first frame if the sequence is incomplete
        seq = list(self.state_deques[tl_id])
        while len(seq) < self.TEMPORAL_SEQ_LEN:
            seq.insert(0, seq[0])
        
        seq_np = np.array(seq, dtype=np.float32)
        return torch.from_numpy(seq_np).unsqueeze(0).to(self.device)

    def _get_pae_latent(self, seq_tensor: torch.Tensor) -> torch.Tensor:
        """
        Projects the sequence of states into the PAE latent space
        for spillback risk projection.
        
        Returns:
            Tensor [batch, pae_latent_dim] (zeros if PAE not available)
        """
        if self.shared_pae is not None:
            with torch.no_grad():
                return self.shared_pae.encode(seq_tensor)  # [batch, latent_dim]
        return torch.zeros(seq_tensor.size(0), self.pae_latent_dim, device=self.device)

    def select_action(self, state: List[float], context: Dict[str, Any]) -> Tuple[int, str]:
        """
        Combines Symbolic rules (instantaneous) and Neural prediction (spillback).
        Returns: Tuple of (Action, Reason String). Action 0 = Veto. Action 1 = Allow.
        """
        tl_id = context.get('tl_id', 'unknown')
        
        # 1. Symbolic layer (Hard constraints)
        sym_action, sym_reason = self.symbolic_audit(context)
        if sym_action == self.ACTION_KEEP_STAGE:
            return sym_action, sym_reason
            
        # 2. Neural layer (Spillback projection)
        risk_level = self.evaluate_spillback_risk(state, tl_id)
        if risk_level >= 1.0:
            return self.ACTION_KEEP_STAGE, self.locale_manager.get_string("guardian_agent.reasons.spillback", default="High spillback risk detected (Neural)")
            
        return self.ACTION_CHANGE_STAGE, self.locale_manager.get_string("guardian_agent.reasons.neuro_passed", default="Neuro-Symbolic audit passed")

    def symbolic_audit(self, context: Dict[str, Any]) -> Tuple[int, str]:
        """
        Executes the instantaneous safety firewall rules.
        Returns: Tuple of (Action, Reason String). Action 0 = Veto. Action 1 = Allow.
        """
        current_stage_duration = context.get('current_stage_duration', 0.0)
        current_stage_state = context.get('current_stage_state', 'G').upper()
        next_stage_has_flow = context.get('next_stage_has_flow', True)
        
        has_y = 'Y' in current_stage_state
        has_g = 'G' in current_stage_state
        
        if has_y:
            # Rule: Yellow Time Violation
            if current_stage_duration < self.yellow_time:
                return self.ACTION_KEEP_STAGE, self.locale_manager.get_string("guardian_agent.reasons.min_yellow", default="Minimum Yellow limits")
        elif has_g:
            # Rule: Minimum Green Time Violation
            if current_stage_duration < self.green_time:
                return self.ACTION_KEEP_STAGE, self.locale_manager.get_string("guardian_agent.reasons.min_green", default="Minimum Green limits")
            # Rule 2: No Flow / Empty Road (Ghost Green)
            if not next_stage_has_flow:
                return self.ACTION_KEEP_STAGE, self.locale_manager.get_string("guardian_agent.reasons.ghost_green", default="Ghost Green constraint")
        else:
            # If it has neither Y nor G, it's a Red stage
            is_clearance_red = context.get('is_clearance_red', True)
            threshold = self.all_red_time if is_clearance_red else self.red_time
            
            # Rule: Red Time Violation
            if current_stage_duration < threshold:
                reason = self.locale_manager.get_string("guardian_agent.reasons.min_all_red", default="Minimum All Red limits") if is_clearance_red else self.locale_manager.get_string("guardian_agent.reasons.min_red", default="Minimum Red limits")
                return self.ACTION_KEEP_STAGE, reason

        return self.ACTION_CHANGE_STAGE, self.locale_manager.get_string("guardian_agent.reasons.symbolic_passed", default="Symbolic audit passed")

    def evaluate_spillback_risk(self, state: List[float], tl_id: str) -> float:
        """
        Executed in the background 'Thinking Mode' loop.
        Evaluates the spillback risk using D3QN_TCN and PAE.
        Returns the Q-value for KEEP_PHASE (Risk level).
        """
        seq_tensor = self._get_temporal_sequence(state, tl_id)

        # Neural Inference (D3QN_TCN)
        eps_threshold = self.epsilon_end + (self.epsilon_start - self.epsilon_end) * \
                        (1. - min(1., self.steps_done / self.epsilon_decay))
        self.steps_done += 1
        
        if random.random() > eps_threshold:
            with torch.no_grad():
                # Spillback projection via PAE
                pae_latent = self._get_pae_latent(seq_tensor)
                # Temporal Q-values with predictive fusion
                q_values = self.policy_net(seq_tensor, pae_latent)
                # We return the Q-value difference. If KEEP_PHASE (0) is much higher than CHANGE_PHASE (1), risk is high.
                # Actually, returning the chosen action is simpler.
                neural_action = q_values.max(1)[1].item()
                if neural_action == self.ACTION_KEEP_STAGE:
                    return 1.0 # High risk (Veto)
                return 0.0 # Low risk (Allow)
        else:
            # Random exploration
            rand_action = random.randrange(2)
            if rand_action == self.ACTION_KEEP_STAGE:
                return 1.0
            return 0.0

    def forward_policy(self, states_batch: torch.Tensor) -> torch.Tensor:
        """Helper for DQNOptimizer to compute Q-values through the active network."""
        pae_latent = self._get_pae_latent(states_batch)
        return self.policy_net(states_batch, pae_latent)

    def forward_target(self, states_batch: torch.Tensor) -> torch.Tensor:
        """Helper for DQNOptimizer to compute Q-values through the target network."""
        pae_latent = self._get_pae_latent(states_batch)
        return self.target_net(states_batch, pae_latent)