# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_mfd_db_reconstruction.py
# Author: Gabriel Moraes
# Date: July 10, 2026

import sys
from unittest.mock import MagicMock, patch

# Mock Captum library to avoid conflicts with conftest.py's DummyTorch
mock_captum_attr = MagicMock()
mock_captum_attr.IntegratedGradients = MagicMock()
sys.modules['captum'] = MagicMock()
sys.modules['captum.attr'] = mock_captum_attr

from mfd.mfd_history_reconstructor import MFDHistoryReconstructor
from mfd.mfd_worker import MFDOrchestrator

@patch("database.database_manager.DatabaseManager")
@patch("utils.locale_manager_backend.LocaleManagerBackend")
def test_reconstruct_mfd_history_from_db(mock_locale, mock_db_manager):
    # Setup mocks
    mock_db = MagicMock()
    mock_db_manager.return_value = mock_db
    
    mock_conn = MagicMock()
    mock_db.engine.get_connection.return_value = mock_conn
    
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock some DB rows: collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length
    mock_rows = [
        ("2026-07-10 12:00:00", "edge_1", 0.1, 10.0, 2, 0.2, 150.0),
        ("2026-07-10 12:00:00", "edge_2", 0.05, 12.0, 1, 0.1, 200.0),
        ("2026-07-10 12:00:01", "edge_1", 0.15, 8.0, 4, 0.3, 150.0),
        ("2026-07-10 12:00:01", "edge_2", 0.08, 10.0, 2, 0.15, 200.0)
    ]
    
    # cursor.fetchmany will return mock_rows first, then empty list
    mock_cursor.fetchmany.side_effect = [mock_rows, []]
    
    # Instantiate history reconstructor directly
    reconstructor = MFDHistoryReconstructor(scenario_results_dir="/tmp/carina_test_mfd", db_manager=mock_db)
    
    # Mock os.path.exists and XML parsing for the net file
    with patch("os.path.exists", return_value=False):
        res = reconstructor.reconstruct_from_db()
        
    assert res is not None
    assert "peak_production" in res
    assert "peak_accumulation" in res
    assert "history" in res
    
    history = res["history"]
    assert len(history) == 2
    
    # Check first step
    step1 = history[0]
    assert step1["timestamp"] == "2026-07-10 12:00:00"
    assert step1["accumulation"] > 0
    assert step1["production"] > 0
    assert step1["mean_speed"] > 0
    assert step1["active_edges"] == 2
    
    # Check second step
    step2 = history[1]
    assert step2["timestamp"] == "2026-07-10 12:00:01"
    
    # Assert cursor and connection cleanup
    assert mock_cursor.execute.call_count >= 1
    assert mock_conn.close.call_count >= 1


def test_mfd_orchestrator_dependency_injection():
    # Setup a mock reconstructor
    mock_reconstructor = MagicMock()
    mock_reconstructor.reconstruct_from_db.return_value = {
        "peak_production": 1.2,
        "peak_accumulation": 0.5,
        "history": [{"timestamp": 1.0, "production": 1.2, "accumulation": 0.5}]
    }
    
    orchestrator = MFDOrchestrator(
        scenario_results_dir="/tmp/carina_test_mfd",
        mfd_reconstructor=mock_reconstructor
    )
    
    # Assert dependency inversion injection worked
    assert orchestrator.mfd_reconstructor == mock_reconstructor
    
    # Trigger MFD report generation and verify delegates
    orchestrator.generate_mfd_report = MagicMock()
    
    orchestrator.process_mfd_job("req_123")
    
    mock_reconstructor.reconstruct_from_db.assert_called_once()
    orchestrator.generate_mfd_report.assert_called_once_with({
        "peak_production": 1.2,
        "peak_accumulation": 0.5,
        "history": [{"timestamp": 1.0, "production": 1.2, "accumulation": 0.5}]
    })
