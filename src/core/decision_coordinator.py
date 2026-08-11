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

# File: src/core/decision_coordinator.py
# Author: Gabriel Moraes
# Date: 02/18/2026

"""
Defines the DecisionCoordinator class.
This component encapsulates the communication logic between agents and
coordinated decision-making at each simulation step.

Updated to include:
1. Neuro-Symbolic Logic of the Guardian Agent (Vetoes).
2. Construction of the full state vector (GAT + Neighbors + Overrides).
"""

import logging
import torch
from typing import TYPE_CHECKING, Dict, Optional

from core.observation_builder import ObservationBuilder
from core.inference_engine import InferenceEngine
from core.safety_auditor import SafetyAuditor

if TYPE_CHECKING:
    from core.strategic_coordinator import StrategicCoordinator
    from engine.environment import SumoEnvironment
    from agents.local_agent import LocalAgent
    from agents.guardian_agent import GuardianAgent # New dependency

try:
    from traci.exceptions import TraCIException
except (ImportError, ModuleNotFoundError):
    import sys, os
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        if tools not in sys.path:
            sys.path.append(tools)
        from traci.exceptions import TraCIException
    else:
        logging.warning("SUMO_HOME não definido, a importação de TraCIException pode falhar.")
        TraCIException = Exception

class DecisionCoordinator:
    def __init__(self, agents: Dict[str, 'LocalAgent'], 
                 neighborhoods: dict, 
                 environment: 'SumoEnvironment', 
                 strategic_coordinator: 'StrategicCoordinator',
                 message_size: int,
                 n_observations: int,
                 guardian_agent: Optional['GuardianAgent'] = None,
                 locale_manager=None):
        """
        Inicializa o Coordenador de Decisões.
        """
        self.agents = agents
        self.neighborhoods = neighborhoods
        self.env = environment
        self.strategic_coordinator = strategic_coordinator
        self.guardian = guardian_agent # Stores the Guardian
        self.message_size = message_size
        self.n_observations = n_observations
        self.locale_manager = locale_manager
        
        self.override_states: Dict[str, str] = {} 
        
        self.builder = ObservationBuilder(message_size, n_observations)
        self.engine = InferenceEngine()
        self.auditor = SafetyAuditor(guardian_agent)
        
        self.tl_list = list(agents.keys())
        self.tl_to_idx = {tl: i for i, tl in enumerate(self.tl_list)}
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Pre-compute Sparse Spatial Topology Tensor for O(1) graph message passing
        self.adjacency_matrix = self._build_sparse_adjacency()
        
        logging.info(self._get_string("decision_coordinator.init_info", default="[COORDINATOR] Resolutive Coordinator activated (Sparse Topological Graph: {count}x{count}).", count=len(self.tl_list)))

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _build_sparse_adjacency(self) -> torch.Tensor:
        """
        Builds a massive GPU-native sparse COO matrix mapping the neighborhood graph.
        Rows = Target intersection, Columns = Source neighbor intersection.
        """
        indices = [[], []]
        values = []
        for i, tl_id in enumerate(self.tl_list):
            neighbors = self.neighborhoods.get(tl_id, [])
            for neighbor_id in neighbors:
                if neighbor_id in self.tl_to_idx:
                    indices[0].append(i)
                    indices[1].append(self.tl_to_idx[neighbor_id])
                    values.append(1.0) # Unweighted normalized influence
        
        if not indices[0]:
            # Empty graph fallback
            return torch.sparse_coo_tensor((0, 0), dtype=torch.float32, device=self.device)
            
        i_tensor = torch.tensor(indices, dtype=torch.long, device=self.device)
        v_tensor = torch.tensor(values, dtype=torch.float32, device=self.device)
        adj = torch.sparse_coo_tensor(i_tensor, v_tensor, (len(self.tl_list), len(self.tl_list)), device=self.device)
        return adj

    def get_coordinated_actions(self, 
                                current_states: dict, 
                                state_history: dict,
                                current_operation_mode: str,
                                latest_veto_map: dict = None) -> tuple:
        """
        Executes the decision cycle:
        1. Collects messages (GAT/Neighbors).
        2. Local Agent suggests action.
        3. Guardian Agent validates (Neuro-Symbolic Veto).
        4. Returns final actions.
        """
        if not current_states:
            return {}, {}

        # --- PHASE 1: Native Vectorized Message Gathering ---
        messages = self.builder.gather_messages(current_states, self.env.state_extractor._get_green_phases_for_tl)
        
        # --- PHASE 1.5: Spatial Graph Matrix Multiplication ---
        # Instead of dynamically stitching arrays via for-loops per agent, we construct the state vector
        # matrix for the entire city, and multiply by the Adjacency matrix to get the Neighbor Graph Sums
        aggregated_neighbors = {}
        if self.tl_list and self.adjacency_matrix.shape[0] > 0:
            msg_matrix = torch.zeros((len(self.tl_list), self.message_size), device=self.device, dtype=torch.float32)
            for tl, msg in messages.items():
                if tl in self.tl_to_idx:
                    msg_matrix[self.tl_to_idx[tl]] = torch.tensor(msg, device=self.device, dtype=torch.float32)
            
            # Massive parallel graph convolution in 1 calculation: Adjacency (N x N) @ Messages (N x F) -> (N x F)
            spatial_vector_matrix = torch.sparse.mm(self.adjacency_matrix, msg_matrix).cpu().numpy()
            
            for i, tl_id in enumerate(self.tl_list):
                aggregated_neighbors[tl_id] = spatial_vector_matrix[i].tolist()
        else:
            for tl_id in self.tl_list:
                aggregated_neighbors[tl_id] = [0.0] * self.message_size

        # --- PHASE 2: Coordinated Decision and Supervision ---
        actions_to_apply = {}
        last_decision_data = {}
        vetos_applied = {} # For log/debug

        is_manual_mode = current_operation_mode == "MANUAL"

        for tl_id, agent in self.agents.items():
            local_state = current_states.get(tl_id)
            if not local_state or not isinstance(local_state, list):
                continue

            gat_vector = self.strategic_coordinator.get_strategic_vector_for_agent(tl_id)
            override_state = self.override_states.get(tl_id)

            augmented_state = self.builder.build_state(
                tl_id, local_state, aggregated_neighbors.get(tl_id, []), 
                gat_vector, override_state, is_manual_mode
            )

            if tl_id not in state_history:
                 continue

            state_history[tl_id].append(augmented_state)
            state_sequence = list(state_history[tl_id])

            try:
                # 1. Local Agent suggests the action
                suggested_action, action_tensor, log_prob, state_val, dist_entropy = self.engine.predict(agent, state_sequence)

                # 2. Guardian Audits the Decision (Symbolic + Background Neural Map)
                final_action, was_vetoed = self.auditor.audit(
                    suggested_action, 
                    tl_id, 
                    augmented_state, 
                    self.env, 
                    latest_veto_map
                )
                
                if was_vetoed:
                    vetos_applied[tl_id] = "Safety Veto"

                # Record the final action
                actions_to_apply[tl_id] = final_action

                last_decision_data[tl_id] = {
                    'state_sequence': state_sequence,
                    'action': action_tensor, # Saves the original tensioner for PPO training
                    'log_prob': log_prob,
                    'state_val': state_val,
                    'entropy': dist_entropy.item(),
                    'vetoed': tl_id in vetos_applied
                }

            except Exception as e_action:
                 logging.error(self._get_string("decision_coordinator.decision_error", default="[Coordinator] Error in decision for {tl_id}: {error}", tl_id=tl_id, error=e_action), exc_info=True)

        return actions_to_apply, last_decision_data