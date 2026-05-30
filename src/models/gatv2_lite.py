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

# File: src/models/gatv2_lite.py
# Author: Gabriel Moraes
# Date: February 17, 2026

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATv2Conv

class GATv2Lite(nn.Module):
    """
    Implementation of the GATv2 Lite (Graph Attention Network v2) architecture.
    Used by the StrategistAgent to process the road network topology and
    generate strategic guidance vectors (latents) for local agents.
    """
    def __init__(self, input_dim, hidden_dim, output_dim, heads):
        """
        Inicializa as camadas da rede GATv2.

        Args:
            input_dim (int): Dimensão do vetor de características de entrada (nó).
            hidden_dim (int): Dimensão da camada oculta.
            output_dim (int): Dimensão do vetor de saída (orientação estratégica).
            heads (int): Número de cabeças de atenção (multi-head attention).
        """
        super(GATv2Lite, self).__init__()
        
        # GATv2 Convolution Layer 1 (Input -> Hidden)
        self.conv1 = GATv2Conv(
            input_dim, 
            hidden_dim, 
            heads=heads, 
            dropout=0.1, 
            concat=True
        )
        
        # GATv2 Convolution Layer 2 (Hidden -> Output)
        # The input is hidden_dim * heads because 'concat=True' in the previous layer
        self.conv2 = GATv2Conv(
            hidden_dim * heads, 
            output_dim, 
            heads=1, # Single head for consolidated final output
            dropout=0.1, 
            concat=False # Final output is not concatenated
        )

        # Normalization layers (LayerNorm) for training stability
        self.norm1 = nn.LayerNorm(hidden_dim * heads)
        self.norm2 = nn.LayerNorm(output_dim)

    def forward(self, x, edge_index):
        """
        Define o "forward pass" da rede.

        Args:
            x (Tensor): Tensor de características dos nós [num_nodes, input_dim].
            edge_index (Tensor): Tensor de conectividade do grafo [2, num_edges].

        Returns:
            Tensor: Tensor de vetores estratégicos [num_nodes, output_dim].
        """
        
        # 1. GATv2 First Layer + ELU Activation + Normalization
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = self.norm1(x)
        x = F.dropout(x, p=0.1, training=self.training)
        
        # 2. GATv2 Second Layer + Normalization (At the end activation, linear output)
        x = self.conv2(x, edge_index)
        x = self.norm2(x)
        
        # The result 'x' is [num_nodes, output_dim]
        return x