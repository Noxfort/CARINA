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

# File: src/xai/captum_attribution_engine.py
# Author: Gabriel Moraes
# Date: June 19, 2026

import torch
import numpy as np
from typing import Optional
from captum.attr import IntegratedGradients
from agents.local_agent import LocalAgent
from xai.captum_model_wrapper import CaptumModelWrapper

class CaptumAttributionEngine:
    """
    Responsibility: Handle PyTorch and Captum mathematical operations.
    Computes raw feature importances using Integrated Gradients.
    """
    def __init__(self, agent: LocalAgent, device: torch.device) -> None:
        self.agent = agent
        self.device = device
        self.wrapped_model = CaptumModelWrapper(
            self.agent.policy_net, 
            shared_pae=getattr(self.agent, 'shared_pae', None)
        ).to(self.device)
        self.ig = IntegratedGradients(self.wrapped_model)

    def compute_importances(self, limit: int = 100) -> Optional[np.ndarray]:
        try:
            if self.agent.xai_memory is None or self.agent.xai_memory.size == 0:
                import logging
                logging.info(f"[CaptumAttributionEngine] No tensor data in memory for agent {getattr(self.agent, 'id', 'N/A')}.")
                return None

            # Limit the number of samples to avoid excessive CPU compute times (max 100 samples)
            limit = min(self.agent.xai_memory.size, limit)
            if self.agent.xai_memory.size <= limit:
                input_tensors = self.agent.xai_memory.states[:self.agent.xai_memory.size].to(self.device)
            else:
                ptr = self.agent.xai_memory.ptr
                indices = [(ptr - 1 - i) % self.agent.xai_memory.capacity for i in range(limit)]
                indices_t = torch.tensor(indices, device=self.agent.xai_memory.states.device, dtype=torch.long)
                input_tensors = self.agent.xai_memory.states[indices_t].to(self.device)

            baselines = torch.zeros_like(input_tensors)
            
            # Run Integrated Gradients (n_steps=25 for TCN efficiency)
            try:
                attributions, _ = self.ig.attribute(
                    input_tensors, baselines, target=0, 
                    return_convergence_delta=True, n_steps=25
                )
            except Exception:
                attributions, _ = self.ig.attribute(
                    input_tensors, baselines,
                    return_convergence_delta=True, n_steps=25
                )
            
            # Aggregation for TCN
            attributions = attributions.abs().sum(dim=0).sum(dim=0)

            # Normalization
            if torch.norm(attributions) > 0:
                attributions = attributions / torch.norm(attributions)
            
            return attributions.cpu().detach().numpy()
        except Exception as e:
            import logging
            logging.error(f"[CaptumAttributionEngine] Failed to compute importances: {e}")
            return None
