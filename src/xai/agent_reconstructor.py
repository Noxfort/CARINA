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

# File: src/xai/agent_reconstructor.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import os
import torch
import logging

from agents.local_agent import LocalAgent
from models.pae import PredictiveAutoencoder
from utils.locale_manager_backend import LocaleManagerBackend

class AgentReconstructor:
    """
    Responsibility: Load physical PyTorch Checkpoints (.pth) from the disk,
    validate their structure, and instantiate 'Blind' LocalAgents (disconnected 
    from the live SUMO/Synapse network) strictly for Mathematical Analysis.
    """

    def __init__(self, checkpoints_dir: str):
        self.checkpoints_dir = checkpoints_dir
        self.locale_manager = LocaleManagerBackend()
        
        # --- Load PAE Universal from checkpoint ---
        self.shared_pae = self._load_pae()
    
    def _load_pae(self):
        """
        Loads the Universal PAE from the pae_universal.pth checkpoint.
        Returns the instance in eval() mode or None if not found.
        """
        pae_path = os.path.join(self.checkpoints_dir, "pae_universal.pth")
        if not os.path.exists(pae_path):
            logging.info("[AgentReconstructor] PAE checkpoint not found. Agents will be reconstructed without PAE.")
            return None
        
        try:
            # Load state_dict to inspect dimensions
            state_dict = torch.load(pae_path, map_location=torch.device('cpu'), weights_only=True)
            
            # Infer dimensions from encoder weights
            input_dim = state_dict['encoder.0.weight'].shape[1]
            latent_dim = state_dict['encoder.3.weight'].shape[0]
            
            pae = PredictiveAutoencoder(input_dim=input_dim, latent_dim=latent_dim)
            pae.load_state_dict(state_dict)
            pae.eval()  # Inference-only for XAI analysis
            
            logging.info(f"[AgentReconstructor] Universal PAE loaded (input={input_dim}, latent={latent_dim})")
            return pae
        except Exception as e:
            logging.warning(f"[AgentReconstructor] Failed to load PAE: {e}. Continuing without PAE.")
            return None
        
    def reconstruct_agent(self, agent_id: str) -> LocalAgent:
        """Loads weights from disk and reconstructs the Agent memory (with PAE integration)."""
        checkpoint_path = os.path.join(self.checkpoints_dir, f"agent_{agent_id}.pth")
        
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        try:
            checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu'), weights_only=False)
        except Exception as e:
            raise RuntimeError(f"Corrupted checkpoint for {agent_id}: {e}")
            
        n_observations = checkpoint.get('n_observations')
        
        if n_observations is None:
            raise ValueError(f"Invalid checkpoint structure for {agent_id}. Missing 'n_observations'.")

        # Reconstruct Agent (Blind Mode - with PAE for full XAI analysis)
        agent = LocalAgent(
            tlight_id=agent_id,
            n_observations=n_observations,
            n_actions=3, 
            initial_hyperparams={},
            log_dir="",
            locale_manager=self.locale_manager,
            shared_pae=self.shared_pae
        )
        
        agent.load_checkpoint(checkpoint_path)
        pae_status = "with PAE" if self.shared_pae else "without PAE"
        logging.info(f"[AgentReconstructor] Agent {agent_id} reconstructed ({pae_status}).")
        return agent
