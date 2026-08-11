# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems

import time
import queue
from unittest.mock import MagicMock
from ui.clients.infrastructure_client import InfrastructureClient

def test_infrastructure_client_fetches_valid_result():
    mock_queue = queue.Queue()
    callback = MagicMock()
    
    client = InfrastructureClient(on_complete_callback=callback, sas_result_queue=mock_queue)
    
    t_trigger = time.time()
    payload = {
        "status": "success",
        "timestamp": t_trigger + 0.1,
        "report_content": "Test Report"
    }
    
    mock_queue.put(payload)
    
    # Run fetch directly (synchronously for unit testing)
    client._fetch_thread_target(trigger_time=t_trigger)
    
    callback.assert_called_once_with(payload)

def test_infrastructure_client_drains_stale_message_and_accepts_valid():
    mock_queue = queue.Queue()
    callback = MagicMock()
    
    client = InfrastructureClient(on_complete_callback=callback, sas_result_queue=mock_queue)
    
    t_trigger = time.time()
    stale_payload = {
        "status": "success",
        "timestamp": t_trigger - 10.0,
        "report_content": "Old Report"
    }
    valid_payload = {
        "status": "success",
        "timestamp": t_trigger + 0.1,
        "report_content": "New Report"
    }
    
    mock_queue.put(stale_payload)
    mock_queue.put(valid_payload)
    
    client._fetch_thread_target(trigger_time=t_trigger)
    
    callback.assert_called_once_with(valid_payload)

def test_infrastructure_client_accepts_result_with_slight_timestamp_lag():
    mock_queue = queue.Queue()
    callback = MagicMock()
    
    client = InfrastructureClient(on_complete_callback=callback, sas_result_queue=mock_queue)
    
    t_trigger = time.time()
    # Payload created 0.2s before trigger_time (microsecond drift/resolution tolerance test)
    payload = {
        "status": "success",
        "timestamp": t_trigger - 0.2,
        "report_content": "Valid Report"
    }
    
    mock_queue.put(payload)
    
    client._fetch_thread_target(trigger_time=t_trigger)
    
    callback.assert_called_once_with(payload)
