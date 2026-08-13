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

# File: src/models/st_gatv2_lite.py
# Author: Gabriel Moraes
# Date: February 17, 2026 (Updated August 2026 for ST-GATv2 Lite)

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATv2Conv
from typing import Optional, Any

class STGATv2Lite(nn.Module):
    """
    Implementation of the ST-GATv2 Lite (Spatiotemporal Graph Attention Network v2) architecture.
    Used by the StrategistAgent to process the road network topology and spatiotemporal dynamics,
    generating strategic guidance vectors (latents) for local agents and the consultant agent.
    """
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, heads: int = 4) -> None:
        """
        Initializes the ST-GATv2 Lite layers.

        Args:
            input_dim (int): Dimension of node feature input vector.
            hidden_dim (int): Hidden dimension.
            output_dim (int): Output strategic guidance dimension.
            heads (int): Number of spatial attention heads.
        """
        super(STGATv2Lite, self).__init__()
        
        # GATv2 Convolution Layer 1 (Input -> Hidden)
        self.conv1 = GATv2Conv(
            input_dim, 
            hidden_dim, 
            heads=heads, 
            dropout=0.1, 
            concat=True
        )
        
        # GATv2 Convolution Layer 2 (Hidden -> Output)
        self.conv2 = GATv2Conv(
            hidden_dim * heads, 
            output_dim, 
            heads=1,
            dropout=0.1, 
            concat=False
        )

        # Normalization layers (LayerNorm) for training stability
        self.norm1 = nn.LayerNorm(hidden_dim * heads)
        self.norm2 = nn.LayerNorm(output_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Defines the forward pass for spatiotemporal graph convolution.

        Args:
            x (Tensor): Node feature tensor [num_nodes, input_dim].
            edge_index (Tensor): Graph connectivity tensor [2, num_edges].

        Returns:
            Tensor: Strategic spatiotemporal vectors [num_nodes, output_dim].
        """
        # 1. GATv2 First Layer + ELU Activation + Normalization
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = self.norm1(x)
        x = F.dropout(x, p=0.1, training=self.training)
        
        # 2. GATv2 Second Layer + Normalization
        x = self.conv2(x, edge_index)
        x = self.norm2(x)
        
        return x

# Alias for backward compatibility
GATv2Lite = STGATv2Lite
