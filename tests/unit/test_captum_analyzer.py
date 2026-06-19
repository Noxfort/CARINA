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

# File: tests/unit/test_captum_analyzer.py
# Author: Gabriel Moraes
# Date: 2026-06-19

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Mock Captum library to avoid conflicts with conftest.py's DummyTorch
mock_captum_attr = MagicMock()
mock_captum_attr.IntegratedGradients = MagicMock()
sys.modules['captum'] = MagicMock()
sys.modules['captum.attr'] = mock_captum_attr

import torch
import torch.nn as nn
import numpy as np

from src.agents.local_agent import LocalAgent
from src.utils.locale_manager_backend import LocaleManagerBackend

# Import the classes directly from their new module files
from src.xai.captum_model_wrapper import CaptumModelWrapper
from src.xai.captum_attribution_engine import CaptumAttributionEngine
from src.xai.feature_aggregator import FeatureAggregator
from src.xai.chart_renderer import ChartRenderer
from src.xai.report_writer import ReportWriter
from src.xai.captum_analyzer import CaptumAnalyzer

class SimpleMockModel(nn.Module):
    def __init__(self, in_features=10, out_features=1):
        super().__init__()
        self.training = False
        
        # Mock hierarchy for expected_dim
        self.tcn = MagicMock()
        self.tcn.network = [MagicMock()]
        self.tcn.network[0].conv1.in_channels = in_features

    def forward(self, x):
        # Returns a tuple of (output, state)
        mock_output = MagicMock()
        mock_output.__getitem__.return_value = mock_output
        return mock_output, None

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    def eval(self):
        self.training = False

    def train(self, mode=True):
        self.training = mode


@pytest.fixture
def mock_agent():
    agent = MagicMock(spec=LocalAgent)
    agent.id = "TL_test"
    agent.n_observations = 10
    agent.policy_net = SimpleMockModel(in_features=10)
    agent.policy_net.eval()
    
    # Mock Memory
    memory = MagicMock()
    memory.size = 5
    memory.capacity = 100
    memory.ptr = 5
    memory.states = MagicMock()
    agent.xai_memory = memory
    return agent


@pytest.fixture
def mock_locale():
    locale = MagicMock(spec=LocaleManagerBackend)
    locale.get_language.return_value = "en"
    locale.get_string.side_effect = lambda key, default=None, **kwargs: default if default is not None else key
    return locale


def test_captum_model_wrapper_without_pae(mock_agent):
    wrapper = CaptumModelWrapper(mock_agent.policy_net, shared_pae=None)
    x = MagicMock()
    x.shape = [1, 4, 10]
    x.__getitem__.return_value = MagicMock()
    
    # Mock torch.cat in xai/captum_model_wrapper.py
    with patch('src.xai.captum_model_wrapper.torch.cat') as mock_cat:
        mock_cat.return_value = x
        output = wrapper(x)
        assert output is not None


def test_captum_model_wrapper_with_pae(mock_agent):
    mock_pae = MagicMock()
    mock_pae.input_dim = 6
    mock_pae.latent_dim = 4
    mock_pae.encode.return_value = MagicMock()
    
    policy_net = SimpleMockModel(in_features=14)
    wrapper = CaptumModelWrapper(policy_net, shared_pae=mock_pae)
    
    x = MagicMock()
    x.shape = [1, 4, 10]
    x.size.return_value = 4
    x.__getitem__.return_value = MagicMock()
    
    # Mock torch.cat in xai/captum_model_wrapper.py
    with patch('src.xai.captum_model_wrapper.torch.cat') as mock_cat:
        mock_cat.return_value = x
        output = wrapper(x)
        assert output is not None
        assert mock_pae.encode.called


def test_feature_aggregator_topology(mock_agent, mock_locale):
    aggregator = FeatureAggregator(mock_agent, mock_locale, feature_glossary={})
    
    # Test resolve topology dims
    edges, phases = aggregator._resolve_topology_dims(13)
    assert edges == 3
    assert phases == 3


def test_feature_aggregator_aggregation(mock_agent, mock_locale):
    glossary = {
        0: {"name": "Feature 0", "description": "Desc 0"},
        1: {"name": "Feature 1", "description": "Desc 1"},
        2: {"name": "Feature 2", "description": "Desc 2"},
    }
    aggregator = FeatureAggregator(mock_agent, mock_locale, feature_glossary=glossary)
    
    importances = np.ones(13)
    sorted_data = aggregator.aggregate(importances)
    
    category_names = [item["name"] for item in sorted_data]
    assert any("Occupancy" in name or "Ocupação" in name for name in category_names)
    assert any("Speed" in name or "Velocidade" in name for name in category_names)
    assert any("Queue" in name or "Fila" in name for name in category_names)
    assert any("Phase" in name or "Semafórico" in name for name in category_names)


def test_captum_analyzer_orchestration(mock_agent, mock_locale, tmp_path):
    scenario_results_dir = str(tmp_path)
    
    analyzer = CaptumAnalyzer(
        agent=mock_agent,
        scenario_results_dir=scenario_results_dir,
        locale_manager=mock_locale,
        feature_glossary=None
    )
    
    # Mocking compute_importances to avoid full captum run
    analyzer.attribution_engine = MagicMock(spec=CaptumAttributionEngine)
    analyzer.attribution_engine.compute_importances.return_value = np.ones(13)
    
    # Mocking plotting/writing to avoid disk issues in testing
    analyzer.chart_renderer = MagicMock(spec=ChartRenderer)
    analyzer.report_writer = MagicMock(spec=ReportWriter)
    
    res = analyzer.generate_analysis()
    
    assert res is not None
    assert "image_path" in res
    assert "text_path" in res
    
    assert analyzer.chart_renderer.render.called
    assert analyzer.report_writer.write.called


def test_captum_analyzer_orchestration_in_memory(mock_agent, mock_locale, tmp_path):
    scenario_results_dir = str(tmp_path)
    
    analyzer = CaptumAnalyzer(
        agent=mock_agent,
        scenario_results_dir=scenario_results_dir,
        locale_manager=mock_locale,
        feature_glossary=None
    )
    
    # Mocking compute_importances to avoid full captum run
    analyzer.attribution_engine = MagicMock(spec=CaptumAttributionEngine)
    analyzer.attribution_engine.compute_importances.return_value = np.ones(13)
    
    # Mocking plotting/writing to avoid disk issues in testing
    analyzer.chart_renderer = MagicMock(spec=ChartRenderer)
    analyzer.chart_renderer.render_to_bytes.return_value = b"fake_png_data"
    analyzer.report_writer = MagicMock(spec=ReportWriter)
    analyzer.report_writer.write_to_string.return_value = "fake_report_text"
    
    res = analyzer.generate_analysis_in_memory()
    
    assert res is not None
    assert "image_base64" in res
    assert "text_report" in res
    assert "sorted_analysis" in res
    
    assert res["text_report"] == "fake_report_text"
    assert analyzer.chart_renderer.render_to_bytes.called
    assert analyzer.report_writer.write_to_string.called
