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
# File: tests/integration/test_system_integration.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import pytest
import configparser
from unittest.mock import MagicMock, patch
from importlib import import_module

try:
    from src.central_controller import CentralController
except ImportError:
    pass

@pytest.fixture
def mock_settings():
    config = configparser.ConfigParser()
    config.add_section('WATCHDOG')
    config.set('WATCHDOG', 'heartbeat_timeout_seconds', '0.30')
    config.add_section('SYNAPSE')
    config.set('SYNAPSE', 'port', '50051')
    config.set('SYNAPSE', 'max_workers', '10')
    return config

@pytest.fixture
def mock_queues():
    q_watchdog = MagicMock()
    q_sds = MagicMock()
    q_sas = MagicMock()
    q_ui = MagicMock()
    return q_watchdog, q_sds, q_sas, q_ui

@pytest.fixture
def mock_pipe_conn():
    conn = MagicMock()
    conn.poll.return_value = False
    return conn

@pytest.fixture
def mock_locale():
    locale = MagicMock()
    locale.get_string.return_value = "Locale String"
    return locale

@pytest.fixture
def central_controller(mock_settings, mock_pipe_conn, mock_queues, mock_locale):
    q_watchdog, q_sds, q_sas, q_ui = mock_queues
    
    with patch('src.central_controller.MonitorClient'), \
         patch('src.central_controller.FailsafeManager'), \
         patch('src.central_controller.TopologyManager'), \
         patch('src.central_controller.RequestProcessor'), \
         patch('src.central_controller.TrafficFrameProcessor'), \
         patch('src.central_controller.TelemetryAggregator'):
        
        cc = CentralController(
            settings=mock_settings,
            ai_pipe_conn=mock_pipe_conn,
            watchdog_queue=q_watchdog,
            sds_data_queue=q_sds,
            sas_data_queue=q_sas,
            ui_command_queue=q_ui,
            locale_manager=mock_locale
        )
        return cc

def test_central_controller_initialization(central_controller):
    """Ensures that the Manager mesh was instantiated."""
    assert central_controller.failsafe_manager is not None
    assert central_controller.topology_manager is not None
    assert central_controller.request_processor is not None
    assert central_controller.traffic_frame_processor is not None
    assert central_controller.health_monitor is not None

def test_readiness_latch(central_controller):
    """Tests the Two-Stage Latch (Frontend + Backend) unlocking the AI."""
    # Initially locked
    assert central_controller.readiness_latch.is_ui_ready is False
    assert central_controller.readiness_latch.is_backend_ready is False
    
    # UI goes ready
    central_controller.readiness_latch.set_ui_ready()
    assert central_controller.readiness_latch.is_ui_ready is True
    # The TrafficFrameProcessor MUST NOT receive set_system_ready(True) yet
    central_controller.traffic_frame_processor.set_system_ready.assert_not_called()
    
    # Backend goes ready
    central_controller.readiness_latch.set_backend_ready()
    assert central_controller.readiness_latch.is_backend_ready is True
    
    # Latch must unlock
    central_controller.traffic_frame_processor.set_system_ready.assert_called_with(True)

@patch('src.central_controller.time.sleep', return_value=None)
@patch('src.central_controller.grpc')
def test_controller_shutdown_signal(mock_grpc, mock_sleep, central_controller, mock_pipe_conn):
    """Tests if the main loop catches the shutdown signal sent by the OS PIPE and stops running."""
    
    # Simulates the pipe receiving a shutdown signal on the first iteration
    mock_pipe_conn.poll.return_value = True
    mock_pipe_conn.recv.return_value = ("system", "shutdown", (), {})
    
    # Executes. run() is an infinite loop that runs while is_running=True
    # The mock will force a break logic on the first check
    central_controller.run()
    
    # Since break was triggered, it turns off flag
    assert central_controller.is_running is False
    # Ensures cleanup routines ran
    mock_pipe_conn.send.assert_called_with(("system", "shutdown", (), {}))
