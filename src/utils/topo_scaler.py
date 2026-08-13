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

# File: src/utils/topo_scaler.py
# Author: Gabriel Moraes
# Date: August 2026

import math
import logging
from typing import Tuple

class TopologicalScaler:
    """
    Topological Auto-Scaling Utility (Zero-Config AutoML).
    Computes power-of-2 neural dimensions and attention head counts based on the
    graph node density (N traffic lights) of the city network.
    Guarantees optimal TensorCore alignment and prevents overfitting.
    """

    @staticmethod
    def calculate_latent_dim(num_nodes: int) -> int:
        """
        Calculates optimal PAE Consultant latent dimension based on graph node count.

        Args:
            num_nodes (int): Total number of traffic light nodes in the city map.

        Returns:
            int: Power-of-2 latent dimension (32, 64, 128, or 256).
        """
        if num_nodes <= 0:
            return 64
        elif num_nodes <= 20:
            return 32
        elif num_nodes <= 80:
            return 64
        elif num_nodes <= 250:
            return 128  # Mid-sized cities (e.g., Londrina)
        else:
            return 256  # Megalopolis

    @staticmethod
    def calculate_num_heads(num_nodes: int) -> int:
        """
        Calculates optimal Transformer Multi-Head Attention head count.

        Args:
            num_nodes (int): Total number of traffic light nodes.

        Returns:
            int: Number of attention heads (2, 4, 8, or 16).
        """
        if num_nodes <= 20:
            return 2
        elif num_nodes <= 80:
            return 4
        elif num_nodes <= 250:
            return 8
        else:
            return 16

    @classmethod
    def auto_scale_architecture(cls, num_nodes: int) -> Tuple[int, int]:
        """
        Auto-scales both latent dimension and head count.

        Args:
            num_nodes (int): Number of nodes.

        Returns:
            Tuple[int, int]: (latent_dim, num_heads)
        """
        latent_dim = cls.calculate_latent_dim(num_nodes)
        num_heads = cls.calculate_num_heads(num_nodes)
        logging.info(f"[TopologicalScaler] Auto-scaled for N={num_nodes} nodes -> latent_dim={latent_dim}, num_heads={num_heads}")
        return latent_dim, num_heads
