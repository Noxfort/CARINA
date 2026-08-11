import os
import sys
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.controller.connection_config_repo import ConnectionConfigRepository

def test_db_connection_persistence():
    test_id = "test_intersection_99"
    test_ip = "192.168.1.99:1610"

    # Save to DB
    saved = ConnectionConfigRepository.save_connection_db(test_id, test_ip)
    assert saved is True

    # Load from DB
    loaded_configs = ConnectionConfigRepository.load_all_connections_db()
    assert test_id in loaded_configs
    assert loaded_configs[test_id] == test_ip

    # Remove/Deactivate auto-connect
    removed = ConnectionConfigRepository.remove_connection_db(test_id)
    assert removed is True

    # Verify no longer active
    reloaded_configs = ConnectionConfigRepository.load_all_connections_db()
    assert test_id not in reloaded_configs

def test_toggle_connection_explicit_disconnect(mocker=None):
    from unittest.mock import MagicMock, patch
    from src.controller.connection_manager import HardwareConnectionManager

    test_id = "test_intersection_disconnect"
    test_ip = "192.168.1.100"

    # Pre-save to DB as auto_connect=True
    ConnectionConfigRepository.save_connection_db(test_id, test_ip)
    assert test_id in ConnectionConfigRepository.load_all_connections_db()

    with patch("src.controller.connection_manager.HardwareConnectionManager._load_and_restore_saved_connections"):
        HardwareConnectionManager._active_instance = None
        mgr = HardwareConnectionManager.get_instance()

    with patch("src.controller.connection_manager.TrafficLightDriver") as mock_driver_cls:
        # Explicit disconnect on an intersection that is NOT currently in active_connections
        result = mgr.toggle_connection(test_id, ip_address=test_ip, action="disconnect")
        
        assert result is False
        # Assert TrafficLightDriver was NEVER instantiated (no SNMP probes/handshake)
        mock_driver_cls.assert_not_called()
        # Assert auto_connect was deactivated in DB
        assert test_id not in ConnectionConfigRepository.load_all_connections_db()

