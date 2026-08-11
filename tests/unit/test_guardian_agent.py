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
import torch

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
    mock.get_string.side_effect = lambda key, default=None, **kwargs: default if default is not None else key
    return mock

@pytest.fixture
def guardian_agent(base_aiconfig, traffic_rules_config, mock_locale):
    with patch.object(ga, 'D3QN_TCN') as mock_tcn, \
         patch.object(ga.optim, 'AdamW') as mock_optim, \
         patch.object(ga.torch.amp, 'GradScaler') as mock_scaler, \
         patch.object(ga.SafetyRules, 'get_green', return_value=15.0), \
         patch.object(ga.SafetyRules, 'get_yellow', return_value=4.0), \
         patch.object(ga.SafetyRules, 'get_all_red', return_value=2.0), \
         patch.object(ga.SafetyRules, 'get_red', return_value=10.0):
        
        agent = GuardianAgent(
            aiconfig=base_aiconfig,
            traffic_rules_config=traffic_rules_config,
            locale_manager=mock_locale,
            shared_pae=None
        )
        return agent

def test_guardian_initialization(guardian_agent):
    """Tests if Guardian rules were inferred from traffic configs."""
    assert guardian_agent.green_time == 15.0
    assert guardian_agent.yellow_time == 4.0
    assert guardian_agent.all_red_time == 2.0
    assert guardian_agent.ACTION_KEEP_STAGE == 0

def test_symbolic_barrier_min_green_violation(guardian_agent):
    """Tests if The Guardian VETOES changes if the minimum green is not met."""
    context = {
        'current_stage_duration': 10.0,  # Below the 15s minimum
        'current_stage_state': 'G',
        'next_stage_has_flow': True,
        'tl_id': 'TL_TEST'
    }
    
    # Independent of neural network, due to barriers, it must keep (0)
    decision, reason = guardian_agent.select_action([0,0], context)
    assert decision == guardian_agent.ACTION_KEEP_STAGE
    assert "Minimum Green limits" in reason

def test_symbolic_barrier_ghost_green(guardian_agent):
    """Tests if The Guardian VETOES changes (saving ghost green) if no one requests green."""
    context = {
        'current_stage_duration': 50.0, # Green can change
        'current_stage_state': 'G',
        'next_stage_has_flow': False,   # But nobody needs it! (Avoidable Ghost Green)
        'tl_id': 'TL_TEST'
    }
    
    # The guardian holds the phase
    decision, reason = guardian_agent.select_action([0,0], context)
    assert decision == guardian_agent.ACTION_KEEP_STAGE
    assert "Ghost Green constraint" in reason

@patch.object(ga, 'random')
def test_neural_inference_path(mock_random, guardian_agent):
    """Tests free path where symbolic barrier does not act and AI takes over."""
    context = {
        'current_stage_duration': 20.0, # Ok
        'current_stage_state': 'G',
        'next_stage_has_flow': True,    # Flow exists on crossing
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
        decision, reason = guardian_agent.select_action([0,0], context)
    
    assert decision == guardian_agent.ACTION_CHANGE_STAGE # Neural action for change (1)

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


def test_symbolic_barrier_all_red_violation(guardian_agent):
    """Tests if The Guardian VETOES changes if the minimum All-Red is not met."""
    context = {
        'current_stage_duration': 1.0,  # Below the 2.0s minimum all-red
        'current_stage_state': 'R',     # Red stage (no G or Y)
        'next_stage_has_flow': True,
        'is_clearance_red': True,
        'tl_id': 'TL_TEST'
    }
    decision, reason = guardian_agent.select_action([0,0], context)
    assert decision == guardian_agent.ACTION_KEEP_STAGE
    assert "Minimum All Red limits" in reason


def test_symbolic_barrier_red_violation(guardian_agent):
    """Tests if The Guardian VETOES changes if the minimum Red is not met."""
    context = {
        'current_stage_duration': 5.0,  # Below the 10.0s minimum red
        'current_stage_state': 'R',     # Red stage (no G or Y)
        'next_stage_has_flow': True,
        'is_clearance_red': False,
        'tl_id': 'TL_TEST'
    }
    decision, reason = guardian_agent.select_action([0,0], context)
    assert decision == guardian_agent.ACTION_KEEP_STAGE
    assert "Minimum Red limits" in reason


def test_fallback_durations_and_clearance_determination():
    """Tests if StateExtractor fallback durations are correct, and StageTransitionManager distinguishes clearance red properly."""
    from src.engine.state_extractor import StateExtractor
    from src.engine.stage_transition_manager import StageTransitionManager
    
    mock_locale = MagicMock()
    mock_locale.get_string.return_value = "Mocked String"
    
    extractor = StateExtractor(locale_manager=mock_locale)
    
    # Mocking sumolib.net.readNet to return a net with one traffic light with no programs to trigger the fallback logic
    mock_net = MagicMock()
    mock_tls = MagicMock()
    mock_tls.getID.return_value = "TL_MOCK"
    mock_tls.getConnections.return_value = []
    mock_tls.getPrograms.return_value = {} # Trigger fallback
    mock_net.getTrafficLights.return_value = [mock_tls]
    
    with patch('sumolib.net.readNet', return_value=mock_net):
        extractor.load_topology("mock_path.net.xml")
        
    assert "TL_MOCK" in extractor.tl_stage_durations
    # Stage 2 should be clearance (3.0s), stage 5 should be normal red (10.0s)
    assert extractor.tl_stage_durations["TL_MOCK"][2] == 3.0
    assert extractor.tl_stage_durations["TL_MOCK"][5] == 10.0
    
    # Initialize StageTransitionManager
    mock_supervisor = MagicMock()
    stm = StageTransitionManager(state_extractor=extractor, action_supervisor=mock_supervisor)
    
    # Stage 2 is 'r' (All-Red clearance)
    # In stm.auto_advance_transitions:
    # prev stage of 2 is 1 ('y').
    # Let's test the logic for stage 2 and stage 5
    stage_codes = extractor.tl_stage_codes["TL_MOCK"]
    
    # Stage 2 logic test:
    prev_state_string = stage_codes.get(1, "").upper()
    stage_durations = extractor.tl_stage_durations["TL_MOCK"]
    default_duration_2 = stage_durations.get(2, 0.0)
    is_clearance_2 = ('Y' in prev_state_string) and (default_duration_2 <= stm.all_red_time)
    assert is_clearance_2 is True
    
    # Stage 5 logic test:
    prev_state_string_5 = stage_codes.get(4, "").upper()
    default_duration_5 = stage_durations.get(5, 0.0)
    is_clearance_5 = ('Y' in prev_state_string_5) and (default_duration_5 <= stm.all_red_time)
    assert is_clearance_5 is False


