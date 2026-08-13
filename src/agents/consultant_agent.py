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

# File: src/agents/consultant_agent.py
# Author: Gabriel Moraes
# Date: August 2026

import torch
import torch.nn as nn
import logging
from typing import Dict, Any, Optional, List
from models.pae import PredictiveAutoencoder
from utils.locale_manager_backend import LocaleManagerBackend
from utils.topo_scaler import TopologicalScaler

class ConsultantAgent:
    """
    Global Predictive Consultant Agent (PAE Predictive Oracle).
    Executes in a continuous event-driven cognitive loop.
    Auto-scales latent dimension (64 to 128 channels) based on urban graph node count.
    Generates individualized, directed predictive mentorship and orientation
    for each LocalAgent (TCN) and GuardianAgent without locking or overriding local autonomy.
    """
    def __init__(self, pae_model: Optional[PredictiveAutoencoder] = None, 
                 num_nodes: int = 50,
                 device: str = "cuda" if torch.cuda.is_available() else "cpu",
                 locale_manager: Optional[LocaleManagerBackend] = None):
        self.device = torch.device(device)
        self.locale_manager = locale_manager or LocaleManagerBackend()
        self.shared_pae = pae_model
        
        # Auto-scale latent dimension and attention heads based on city graph topology
        self.latent_dim, self.num_heads = TopologicalScaler.auto_scale_architecture(num_nodes)
        
        if self.shared_pae:
            self.shared_pae.to(self.device)
            self.shared_pae.eval()

        self.directed_mentorship_cache: Dict[str, Dict[str, Any]] = {}
        logging.info(f"[ConsultantAgent] Initialized for N={num_nodes} nodes -> Auto-scaled latent_dim={self.latent_dim}, num_heads={self.num_heads}")

    def process_event_telemetry(self, current_states: Dict[str, list], 
                               stgat_vectors: Dict[str, list]) -> Dict[str, Dict[str, Any]]:
        """
        Event-driven cognitive loop: Synthesizes recent telemetry history + ST-GATv2 spatiotemporal
        graph topology to produce directed, individualized predictive mentorship for each intersection.

        Args:
            current_states: Dictionary mapping agent_id -> local physical observation state.
            stgat_vectors: Dictionary mapping agent_id -> ST-GATv2 Lite spatiotemporal vector.

        Returns:
            Dictionary mapping agent_id -> {
                'latent_vector': [latent_dim] tensor list,
                'mentorship_summary': str (directed technical advisory text),
                'recommended_bias': float (stage extension/advance bias)
            }
        """
        orientations = {}

        for agent_id, state in current_states.items():
            stgat_vec = stgat_vectors.get(agent_id, [0.0] * 16)
            
            # Compute predictive latent via PAE if model available
            if self.shared_pae and isinstance(state, list) and len(state) > 0:
                try:
                    state_t = torch.tensor([state], dtype=torch.float32, device=self.device)
                    if state_t.dim() == 2:
                        state_t = state_t.unsqueeze(1)
                    device_type = self.device.type
                    with torch.no_grad(), torch.amp.autocast(device_type=device_type, enabled=(device_type == 'cuda')):
                        latent_t = self.shared_pae.encode(state_t)
                        latent_vector = latent_t.squeeze(0).cpu().numpy().tolist()
                except Exception as e:
                    logging.warning(f"[ConsultantAgent] PAE encoding fallback for {agent_id}: {e}")
                    latent_vector = [0.0] * self.latent_dim
            else:
                latent_vector = [0.0] * self.latent_dim

            # Pad or truncate latent_vector to match self.latent_dim
            if len(latent_vector) < self.latent_dim:
                latent_vector = latent_vector + [0.0] * (self.latent_dim - len(latent_vector))
            elif len(latent_vector) > self.latent_dim:
                latent_vector = latent_vector[:self.latent_dim]

            # Synthesize individualized directed mentorship advisory
            occ_sum = sum(state[:4]) if len(state) >= 4 else 0.0
            stgat_sum = sum(stgat_vec) if isinstance(stgat_vec, list) else 0.0
            
            if occ_sum > 2.0 or stgat_sum > 1.5:
                summary = f"Orientação Preditiva Direcionada para Agente {agent_id}: Pelotão denso em deslocamento. Recomendação: Manter o estágio atual para travar a Onda Verde."
                rec_bias = 0.8
            elif occ_sum < 0.3:
                summary = f"Orientação Preditiva Direcionada para Agente {agent_id}: Aproximação deserta. Recomendação: Avançar estágio para liberar vias transversais."
                rec_bias = -0.5
            else:
                summary = f"Orientação Preditiva Direcionada para Agente {agent_id}: Operação estável. Manter equilíbrio entre estágio local e sincronismo de rede."
                rec_bias = 0.0

            orientations[agent_id] = {
                "latent_vector": latent_vector,
                "mentorship_summary": summary,
                "recommended_bias": rec_bias
            }

        self.directed_mentorship_cache = orientations
        return orientations

    def get_directed_mentorship_for_agent(self, agent_id: str) -> Dict[str, Any]:
        """Returns directed individual mentorship for a specific LocalAgent or GuardianAgent."""
        return self.directed_mentorship_cache.get(agent_id, {
            "latent_vector": [0.0] * self.latent_dim,
            "mentorship_summary": f"Orientação Preditiva Padrão para {agent_id}.",
            "recommended_bias": 0.0
        })
