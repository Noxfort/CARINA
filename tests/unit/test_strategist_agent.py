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
#
# File: tests/unit/test_strategist_agent.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import sys
import pytest
from unittest.mock import MagicMock, patch
import torch

import src.agents.strategist_agent as sa
from src.agents.strategist_agent import StrategistAgent

@pytest.fixture
def mock_sumo_net():
    """Creates a fake traffic mesh (structural graph) where A points to B and C."""
    net = MagicMock()
    
    # Create Nodes
    node_a = MagicMock()
    node_b = MagicMock()
    node_c = MagicMock()
    
    node_a.getID.return_value = "TL_A"
    node_b.getID.return_value = "TL_B"
    node_c.getID.return_value = "TL_C"
    
    # Map A -> B and A -> C
    edge_ab = MagicMock()
    edge_ab.getToNode.return_value = node_b
    edge_ac = MagicMock()
    edge_ac.getToNode.return_value = node_c
    
    node_a.getOutgoing.return_value = [edge_ab, edge_ac]
    node_b.getOutgoing.return_value = []
    node_c.getOutgoing.return_value = []
    
    # Traffic Lights on network
    tls_a = MagicMock()
    tls_a.getID.return_value = "TL_A"
    tls_b = MagicMock()
    tls_b.getID.return_value = "TL_B"
    tls_c = MagicMock()
    tls_c.getID.return_value = "TL_C"
    
    net.getTrafficLights.return_value = [tls_a, tls_b, tls_c]
    
    def get_node(tl_id):
        return {"TL_A": node_a, "TL_B": node_b, "TL_C": node_c}.get(tl_id)
    
    net.getNode = get_node
    return net

@patch.object(sa.os.path, 'exists', return_value=True) # Fakes that SUMO XML exists
@patch.object(sa.sumolib.net, 'readNet')
@patch.object(sa, 'GATv2Lite')
@patch.object(sa.optim, 'Adam')
def test_strategist_topology_builder(mock_adam, mock_gat, mock_readnet, mock_exists, mock_sumo_net):
    """Ensures Breadth-First Search (BFS) maps physical connections correctly."""
    mock_readnet.return_value = mock_sumo_net
    
    # Instance
    agent = StrategistAgent(input_dim=10, hidden_dim=8, output_dim=4, map_path="dummy.xml")
    
    # 3 mocked Traffic Lights
    assert agent.num_nodes == 3
    assert agent.tls_id_to_idx["TL_A"] == 0
    assert agent.tls_id_to_idx["TL_B"] == 1
    assert agent.tls_id_to_idx["TL_C"] == 2
    
    # Edges must be [0 -> 1] and [0 -> 2] for Pytorch Geometric Edge Index
    edges_tensor = agent.edge_index
    assert edges_tensor is not None
    
    # source_nodes = [0, 0]
    # target_nodes = [1, 2]
    # edge_index.shape deve ser [2, 2]
    assert tuple(edges_tensor.shape) == (2, 2)
    # Sources list
    assert edges_tensor[0][0].item() == 0
    assert edges_tensor[0][1].item() == 0
    # Targets list
    assert edges_tensor[1][0].item() == 1
    assert edges_tensor[1][1].item() == 2

@patch.object(sa.os.path, 'exists', return_value=True)
@patch.object(sa.sumolib.net, 'readNet')
@patch.object(sa, 'GATv2Lite')
@patch.object(sa.optim, 'Adam')
def test_strategic_vectors_generation(mock_adam, mock_gat, mock_readnet, mock_exists, mock_sumo_net):
    """Tests context features extraction (Strategist Action)."""
    mock_readnet.return_value = mock_sumo_net
    
    agent = StrategistAgent(input_dim=10, hidden_dim=8, output_dim=4, map_path="dummy.xml")
    
    # Mocking GATv2 output
    mock_nn_output = torch.zeros((3, 4)) # 3 nodes, dimension 4
    agent.model.return_value = mock_nn_output
    
    # Fake tensor
    fake_node_features = torch.rand((3, 10))
    
    result = agent.get_strategic_vectors(fake_node_features)
    assert tuple(result.shape) == (3, 4)
