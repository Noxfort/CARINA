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
# File: tests/unit/test_local_agent.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import sys
import pytest
from unittest.mock import MagicMock, patch
import torch
import numpy as np

import src.agents.local_agent as la
from src.agents.local_agent import LocalAgent

@pytest.fixture
def base_hyperparams():
    return {
        'gamma': 0.99,
        'gae_lambda': 0.95,
        'learning_rate': 0.0001,
        'eps_clip': 0.2,
        'k_epochs': 4,
        'target_kl': 0.02,
        'grad_clip_norm': 0.5,
        'dropout_p': 0.1,
        'sequence_length': 4
    }

@pytest.fixture
def mock_locale():
    mock = MagicMock()
    mock.get_string.return_value = "Mocked String"
    return mock

@pytest.fixture
def local_agent(base_hyperparams, mock_locale):
    with patch.object(la, 'ActorCriticNet') as mock_ac, \
         patch.object(la.optim, 'AdamW') as mock_optim, \
         patch.object(la.torch.amp, 'GradScaler') as mock_scaler:
        
        # Ignoring the real model creation to not depend on torch in the test
        agent = LocalAgent(
            tlight_id="TL_1",
            n_observations=5,
            n_actions=2,
            initial_hyperparams=base_hyperparams,
            log_dir="/tmp",
            locale_manager=mock_locale,
            shared_pae=None
        )
        return agent

def test_initialization(local_agent, base_hyperparams):
    """Tests if hyperparameters were saved correctly."""
    assert local_agent.id == "TL_1"
    assert local_agent.n_observations == 5
    assert local_agent.n_actions == 2
    assert local_agent.learning_rate == base_hyperparams['learning_rate']
    assert local_agent.gamma == base_hyperparams['gamma']

def test_update_hyperparameters(local_agent):
    """Tests if the agent can perform PBT for hyperparameters."""
    new_hyperparams = {
        'learning_rate': 0.005,
        'gamma': 0.90,
        'dropout_p': 0.2
    }
    
    local_agent.update_hyperparameters(new_hyperparams)
    assert local_agent.learning_rate == 0.005
    assert local_agent.gamma == 0.90
    assert local_agent.dropout_p == 0.2

@patch.object(la.torch, 'save')
def test_save_checkpoint(mock_save, local_agent):
    """Verifies checkpoint generation with correct metrics (maturity)."""
    filepath = "/tmp/fake_cp.pt"
    local_agent.save_checkpoint(filepath, maturity_stage="TEEN")
    
    # Validates that save method was called (and tensors were mocked correctly)
    mock_save.assert_called_once()
    
    # The checkpoint dict passed in save args
    saved_data = mock_save.call_args[0][0]
    assert saved_data['maturity_stage'] == "TEEN"
    assert saved_data['n_observations'] == 5
    assert saved_data['hyperparameters'] == local_agent.hyperparams

@patch.object(la.torch, 'load')
def test_load_checkpoint(mock_load, local_agent):
    """Tests that load_checkpoint rescues the state and maturity safely."""
    # Mocked return from torch.load
    mock_load.return_value = {
        'episodes_done': 100,
        'steps_done': 500,
        'policy_net_state_dict': {},
        'optimizer_state_dict': {},
        'hyperparameters': local_agent.hyperparams,
        'xai_memory': None,
        'n_observations': 5,
        'maturity_stage': "ADULT"
    }
    
    maturity = local_agent.load_checkpoint("/tmp/val.pt")
    
    assert maturity == "ADULT"
    assert local_agent.episodes_done == 100
    assert local_agent.steps_done == 500

@patch.object(la, 'Categorical')
def test_choose_action(mock_categorical, local_agent):
    """Tests simple forward action generation."""
    # Mock return shape from actor_critic (probs, state_value)
    mock_probs = MagicMock()
    mock_value = MagicMock()
    local_agent.policy_net.return_value = (mock_probs, mock_value)
    
    # Mock of distribution
    mock_dist = MagicMock()
    mock_dist.sample.return_value = "action_mock"
    mock_dist.log_prob.return_value = "log_prob_mock"
    mock_dist.entropy.return_value = "entropy_mock"
    mock_categorical.return_value = mock_dist
    
    fake_state_tensor = MagicMock()
    action, log_prob, state_val, dist_entropy = local_agent.choose_action(fake_state_tensor)
    
    assert action == "action_mock"
    assert log_prob == "log_prob_mock"
    assert state_val == mock_value
    assert dist_entropy == "entropy_mock"

def test_pae_augmentation(local_agent):
    """Tests PAE tree fusion with input tensor if PAE exists."""
    # Mock Shared PAE
    mock_pae = MagicMock()
    mock_pae.latent_dim = 3
    local_agent.shared_pae = mock_pae
    local_agent.pae_latent_dim = 3
    
    # Fake tensor shape = [batch=1, seq_len=4, n_obs=5]
    with patch.object(la.torch, 'cat') as mock_cat:
        with patch.object(la.torch, 'no_grad'):
            fake_state = np.zeros((1, 4, 5))
            fake_tensor = MagicMock()
            local_agent._augment_with_pae(fake_tensor)
            
            # Ensures it requested and used measurements in _augment_with_pae
            mock_pae.encode.assert_called()
            mock_cat.assert_called()
