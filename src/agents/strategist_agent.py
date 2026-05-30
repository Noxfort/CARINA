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

# File: src/agents/strategist_agent.py
# Author: Gabriel Moraes - Noxfort Systems
# Date: 02/19/2026

import os
import logging
import torch
import torch.optim as optim
import sumolib
from collections import deque
from typing import Dict, Any, Optional, List, Tuple, Set
from src.models.gatv2_lite import GATv2Lite

class StrategistAgent:
    """
    The Strategist Agent (Global) utilizes a GATv2 (Graph Attention Network)
    to analyze the network topology and generate context vectors (latents)
    to coordinate Local Agents.
    
    It autonomously parses SUMO network files to build the graph topology
    using a traversal algorithm to handle intermediate geometry nodes.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        heads: int = 4,
        lr: float = 0.001,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        map_path: str = "results/hft_live_session/maps/hft_live_session.net.xml"
    ):
        """
        Initializes the Strategist Agent and builds the static graph from the SUMO net file.
        """
        self.device = torch.device(device)
        self.logger = logging.getLogger(__name__)
        
        # Initialize GAT model
        self.model = GATv2Lite(input_dim, hidden_dim, output_dim, heads=heads).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        
        # Topology storage
        self.edge_index: Optional[torch.Tensor] = None
        self.tls_id_to_idx: Dict[str, int] = {}
        self.idx_to_tls_id: Dict[int, str] = {}
        self.num_nodes = 0
        
        # Build graph from file immediately upon instantiation
        self._build_topology_from_sumo(map_path)

    def _build_topology_from_sumo(self, net_file: str):
        """
        Parses the SUMO .net.xml file to extract traffic lights as nodes
        and physical connections as edges using BFS traversal.
        """
        print(f"INFO: [Strategist] Building Graph from: {net_file}")
        
        if not os.path.exists(net_file):
            msg = f"SUMO Network file not found at: {net_file}. Graph not built."
            print(f"ERROR: [Strategist] {msg}")
            self.logger.error(msg)
            return

        self.logger.info(f"Building Strategist Graph from: {net_file}")
        
        try:
            # Load the network with sumolib
            net = sumolib.net.readNet(net_file)
            traffic_lights = net.getTrafficLights()
            
            # 1. Create Node Mapping (TLS ID -> Index)
            # We assume TLS ID matches the Junction ID (Standard in OSM/SUMO)
            self.tls_id_to_idx = {tls.getID(): i for i, tls in enumerate(traffic_lights)}
            self.idx_to_tls_id = {i: tls.getID() for i, tls in enumerate(traffic_lights)}
            self.num_nodes = len(traffic_lights)
            
            source_nodes = []
            target_nodes = []
            
            # Cache known TLS IDs for fast lookup
            tls_ids_set = set(self.tls_id_to_idx.keys())

            # 2. Build Edges based on Reachability (BFS)
            for tls in traffic_lights:
                tls_id = tls.getID()
                src_idx = self.tls_id_to_idx[tls_id]
                
                # Get the node associated with this TLS
                node = net.getNode(tls_id)
                if not node:
                    continue # Should not happen if ID matches
                
                # Find all downstream TLS neighbors
                neighbors = self._find_downstream_tls(node, tls_ids_set, net)
                
                for neighbor_id in neighbors:
                    if neighbor_id != tls_id: # Avoid self-loops
                        tgt_idx = self.tls_id_to_idx[neighbor_id]
                        source_nodes.append(src_idx)
                        target_nodes.append(tgt_idx)
            
            # Convert to Tensor [2, num_edges]
            if source_nodes:
                edge_index_tensor = torch.tensor([source_nodes, target_nodes], dtype=torch.long)
                self.edge_index = edge_index_tensor.to(self.device)
                
                success_msg = f"INFO: [Strategist] Graph built successfully. Nodes: {self.num_nodes}, Edges: {len(source_nodes)}"
                print(success_msg)
                self.logger.info(success_msg)
            else:
                warn_msg = "WARNING: [Strategist] No connections found between traffic lights. Graph is disconnected."
                print(warn_msg)
                self.logger.warning(warn_msg)
                self.edge_index = torch.empty((2, 0), dtype=torch.long, device=self.device)

        except Exception as e:
            err_msg = f"Failed to build graph topology: {e}"
            print(f"ERROR: [Strategist] {err_msg}")
            self.logger.error(err_msg)
            raise e

    def _find_downstream_tls(self, start_node, tls_ids_set: Set[str], net) -> Set[str]:
        """
        Traverses the network starting from start_node to find reachable Traffic Lights.
        Stops traversing a branch when a TLS is found.
        """
        found_neighbors = set()
        visited_nodes = set()
        queue = deque([start_node])
        
        visited_nodes.add(start_node.getID())
        
        # Max depth to prevent infinite search in huge nets
        max_depth = 10 
        depth_tracker = {start_node.getID(): 0}

        while queue:
            current_node = queue.popleft()
            current_depth = depth_tracker[current_node.getID()]
            
            if current_depth >= max_depth:
                continue

            # Iterate all outgoing edges from this node
            for edge in current_node.getOutgoing():
                next_node = edge.getToNode()
                next_node_id = next_node.getID()
                
                if next_node_id in visited_nodes:
                    continue
                
                visited_nodes.add(next_node_id)
                depth_tracker[next_node_id] = current_depth + 1
                
                # Check if this node is a Traffic Light we control
                if next_node_id in tls_ids_set:
                    found_neighbors.add(next_node_id)
                    # We stop exploring this branch because we found the immediate neighbor
                    continue 
                else:
                    # Continue searching downstream
                    queue.append(next_node)
                    
        return found_neighbors

    def get_strategic_vectors(self, node_features: torch.Tensor, edge_index: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Executes the GAT to obtain strategic vectors.
        """
        self.model.eval()
        graph_edges = edge_index if edge_index is not None else self.edge_index
        
        if graph_edges is None:
            raise RuntimeError("Strategist Agent: Graph topology not initialized.")

        with torch.no_grad():
            x = node_features.to(self.device)
            edges = graph_edges.to(self.device)
            strategic_vectors = self.model(x, edges)
            
        return strategic_vectors

    def update(self, loss: torch.Tensor):
        self.model.train()
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.optimizer.step()

    def save_checkpoint(self, path: str):
        torch.save(self.model.state_dict(), path)
        self.logger.info(f"Strategist Agent checkpoint saved to {path}")

    def load_checkpoint(self, path: str):
        if os.path.exists(path):
            self.model.load_state_dict(torch.load(path, map_location=self.device))
            self.logger.info(f"Strategist Agent checkpoint loaded from {path}")
        else:
            self.logger.warning(f"Checkpoint not found at {path}")

    def get_node_index(self, tls_id: str) -> int:
        return self.tls_id_to_idx.get(tls_id, -1)