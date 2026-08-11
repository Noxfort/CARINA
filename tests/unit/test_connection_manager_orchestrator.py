# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# File: tests/unit/test_connection_manager_orchestrator.py

import pytest
from unittest.mock import MagicMock
from src.utils.network_address_parser import NetworkAddressParser
from src.controller.intersection_resolver import IntersectionResolver
from src.controller.connection_operation_handler import ConnectionOperationHandler


def test_network_address_parser():
    """Verify NetworkAddressParser RegEx extraction and IPv4 validation."""
    valid, ip, port, clean = NetworkAddressParser.parse_and_validate_ip("192.168.1.50:80161")
    assert valid is True
    assert ip == "192.168.1.50"
    assert port == 80161
    assert clean == "192.168.1.50:80161"

    # Default port fallback
    valid, ip, port, clean = NetworkAddressParser.parse_and_validate_ip("10.0.0.1")
    assert valid is True
    assert ip == "10.0.0.1"
    assert port == 161
    assert clean == "10.0.0.1"

    # Invalid IPv4 address
    valid, ip, port, clean = NetworkAddressParser.parse_and_validate_ip("999.999.999.999")
    assert valid is False


def test_intersection_resolver():
    """Verify IntersectionResolver IP mapping and status resolution."""
    active_conn = {}
    saved_ips = {"tl_1": "192.168.1.100"}

    mock_driver = MagicMock()
    mock_driver.is_connected = True
    mock_driver.ip_address = "192.168.1.50"
    mock_driver.hardware_driver.brand = "Noxfort"
    mock_driver.hardware_driver.model = "NTCIP-2026"
    active_conn["tl_2"] = mock_driver

    resolver = IntersectionResolver(active_conn, saved_ips)

    # Resolve IP of active driver
    assert resolver.find_intersection_by_ip("192.168.1.50") == "tl_2"
    # Resolve IP of saved IP
    assert resolver.find_intersection_by_ip("192.168.1.100") == "tl_1"
    # Connection state check
    assert resolver.is_intersection_connected("tl_2") is True
    assert resolver.is_intersection_connected("tl_1") is False

    # Hardware info check
    info = resolver.get_hardware_info("tl_2")
    assert info["is_connected"] is True
    assert info["brand"] == "Noxfort"
    assert info["model"] == "NTCIP-2026"
