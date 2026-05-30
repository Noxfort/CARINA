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

# File: src/core/inference_engine.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import torch
from typing import TYPE_CHECKING, Tuple, Any

if TYPE_CHECKING:
    from agents.local_agent import LocalAgent

class InferenceEngine:
    """
    Handles the tensor translation and Neural Network interface for LocalAgents.
    """

    def predict(self, agent: 'LocalAgent', state_sequence: list) -> Tuple[int, Any, Any, Any, Any]:
        """
        Converts sequence to tensor, infers action, and returns components for PPO training.
        Returns: (suggested_action_int, action_tensor, log_prob, state_value, entropy)
        """
        state_sequence_tensor = torch.tensor([state_sequence], dtype=torch.float32).to(agent.device)
        
        # 0 = CHANGE PHASE, 1 = KEEP PHASE
        action_tensor, log_prob, state_val, dist_entropy = agent.choose_action(state_sequence_tensor)
        suggested_action = action_tensor.item()
        
        return suggested_action, action_tensor, log_prob, state_val, dist_entropy
