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
# File: tests/unit/test_guardian_agent.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import sys
import pytest
from unittest.mock import MagicMock, patch
import pytest
import sys
import torch
for submod in ['nn', 'optim', 'distributions', 'amp']:
    mock_obj = MagicMock()
    if f'torch.{submod}' not in sys.modules:
        sys.modules[f'torch.{submod}'] = mock_obj
    if not hasattr(torch, submod):
        setattr(torch, submod, mock_obj)

sys.modules['torch.nn.functional'] = MagicMock()
setattr(sys.modules['torch.nn'], 'functional', sys.modules['torch.nn.functional'])

import src.agents.guardian_agent as ga
from src.agents.guardian_agent import GuardianAgent

@pytest.fixture
def base_aiconfig():
    conf = MagicMock()
    conf.getint.side_effect = lambda k, fallback=None: fallback if fallback else 100
    conf.getfloat.side_effect = lambda k, fallback=None: fallback if fallback else 0.5
    return conf

@pytest.fixture
def traffic_rules_config():
    conf = MagicMock()
    # Mock fallback params: min_green=15, yellow=4, red=2
    def get_float(k, fallback):
        vals = {
            'min_green_time_seconds': 15.0,
            'yellow_time_seconds': 4.0,
            'all_red_time_seconds': 2.0
        }
        return vals.get(k, fallback)
    conf.getfloat.side_effect = get_float
    return conf

@pytest.fixture
def mock_locale():
    mock = MagicMock()
    mock.get_string.return_value = "Mocked Guardian String"
    return mock

@pytest.fixture
def guardian_agent(base_aiconfig, traffic_rules_config, mock_locale):
    with patch.object(ga, 'D3QN_TCN') as mock_tcn, \
         patch.object(ga.optim, 'AdamW') as mock_optim, \
         patch.object(ga.torch.amp, 'GradScaler') as mock_scaler:
        
        agent = GuardianAgent(
            aiconfig=base_aiconfig,
            traffic_rules_config=traffic_rules_config,
            locale_manager=mock_locale,
            shared_pae=None
        )
        return agent

def test_guardian_initialization(guardian_agent):
    """Tests if Guardian rules were inferred from traffic configs."""
    assert guardian_agent.min_green_time == 15.0
    assert guardian_agent.yellow_time == 4.0
    assert guardian_agent.all_red_time == 2.0
    assert guardian_agent.ACTION_KEEP_PHASE == 0

def test_symbolic_barrier_min_green_violation(guardian_agent):
    """Tests if The Guardian VETOES changes if the minimum green is not met."""
    context = {
        'current_phase_duration': 10.0,  # Below the 15s minimum
        'next_phase_has_flow': True,
        'tl_id': 'TL_TEST'
    }
    
    # Independent of neural network, due to barriers, it must keep (0)
    decision = guardian_agent.select_action([0,0], context)
    assert decision == guardian_agent.ACTION_KEEP_PHASE

def test_symbolic_barrier_ghost_green(guardian_agent):
    """Tests if The Guardian VETOES changes (saving ghost green) if no one requests green."""
    context = {
        'current_phase_duration': 50.0, # Green can change
        'next_phase_has_flow': False,   # But nobody needs it! (Avoidable Ghost Green)
        'tl_id': 'TL_TEST'
    }
    
    # The guardian holds the phase
    decision = guardian_agent.select_action([0,0], context)
    assert decision == guardian_agent.ACTION_KEEP_PHASE

@patch.object(ga, 'random')
def test_neural_inference_path(mock_random, guardian_agent):
    """Tests free path where symbolic barrier does not act and AI takes over."""
    context = {
        'current_phase_duration': 20.0, # Ok
        'next_phase_has_flow': True,    # Flow exists on crossing
        'tl_id': 'TL_FREE'
    }
    
    # We force epsilon to go into network (not pure exploration)
    mock_random.random.return_value = 1.0 # Always > eps_threshold if warmed up
    guardian_agent.epsilon_end = -1.0 # Ensures greedy
    guardian_agent.epsilon_start = -1.0
    guardian_agent.steps_done = 999999
    
    # Mock of DQN forward pass
    mock_q_values = MagicMock()
    mock_max = MagicMock()
    mock_max.item.return_value = 1  # AI decides to change
    mock_q_values.max.return_value = [None, mock_max]
    
    guardian_agent.policy_net.return_value = mock_q_values
    
    with patch.object(ga.torch, 'tensor'):
        decision = guardian_agent.select_action([0,0], context)
    
    assert decision == 1 # Neural action for change

def test_temporal_sequence_padding(guardian_agent):
    """Tests if agent's Deque manages and does PADDING of state vector."""
    state1 = [1.0, 0.0]
    
    with patch.object(ga.torch, 'tensor') as mock_tensor:
        # Insert only 1 measurement. Must pad to TEMPORAL_SEQ_LEN
        seq_tensor = guardian_agent._get_temporal_sequence(state1, 'TL_TEST')
        
        args = mock_tensor.call_args[0][0]
        # Expected: List containing 1 sublist with SEQ_LEN inner items
        assert len(args) == 1
        assert len(args[0]) == guardian_agent.TEMPORAL_SEQ_LEN
        
        # The last of subsequence must be the state itself
        assert args[0][-1] == state1
