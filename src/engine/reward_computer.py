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

# File: src/engine/reward_computer.py
# Author: Gabriel Moraes
# Date: February 17, 2026

import logging

class RewardComputer:
    """
    Component specialized in calculating the Reward Function.
    Isolates the mathematical logic of evaluating agent performance.
    """

    def __init__(self, settings, state_extractor):
        """
        Args:
            settings: ConfigParser object with settings.
            state_extractor: Reference to the state extractor (for lane map access).
        """
        self.state_extractor = state_extractor
        
        # Load weights from configuration or use defensive default values
        self.weights = {
            'queue': settings.getfloat('REWARD_WEIGHTS', 'weight_waiting_time', fallback=-2.0),
            'occupancy': settings.getfloat('REWARD_WEIGHTS', 'weight_flow', fallback=-0.5)
        }
        
        logging.info(f"[REWARD_COMPUTER] Pesos carregados: {self.weights}")

    def calculate(self, tl_id: str, edges_data: dict) -> float:
        """
        Calculates the immediate reward for a specific agent based on edge states.
        
        Args:
            tl_id (str): Traffic light ID.
            edges_data (dict): Edge traffic data (queues, occupancy).
            
        Returns:
            float: Scalar reward value.
        """
        reward = 0.0
        
        # Check if we have the lane mapping for this traffic light
        if hasattr(self.state_extractor, 'tl_lanes') and tl_id in self.state_extractor.tl_lanes:
            lanes = self.state_extractor.tl_lanes[tl_id]
            
            # Identifies unique edges (edges) associated with controlled lanes
            unique_edges = set()
            for lane in lanes:
                # Remove the lane index to get the edge ID (ex: "edge_0" from "edge_0_1")
                edge = lane.rpartition('_')[0]
                unique_edges.add(edge)
            
            # Sums the penalties/rewards of all connected edges
            for edge in unique_edges:
                if edge in edges_data:
                    data = edges_data[edge]
                    reward += data.get('queue_length', 0) * self.weights['queue']
                    reward += data.get('occupancy', 0) * self.weights['occupancy']
                    
        return reward