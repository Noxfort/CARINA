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
# File: tests/integration/test_traffic_light_drivers.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import pytest
from src.drivers.ntcip_driver import NtcipDriver
from src.drivers.utmc_driver import UtmcDriver

@pytest.fixture
def ntcip_driver():
    """Initializes an NTCIP Driver connected to a dummy IP for testing."""
    return NtcipDriver(ip_address="192.168.1.100", port=161, community_string="public")

@pytest.mark.integration
def test_ntcip_send_action(ntcip_driver, mock_snmp_hardware):
    """
    Scenario 1: Safe Command Dispatch (Action Translation).
    Ensures that the CARINA logical action is encoded in the correct mathematical base of NTCIP.
    """
    # CARINA decides to force green on Phase 3
    carina_decision = {'action_type': 'hold', 'phase': 3}
    
    # Base 2 arithmetic must bit-shift (1 << (phase - 1)) = (1 << 2) = 4
    expected_octet = 4 

    # Execute the translation and dispatch
    success = ntcip_driver.send_action(carina_decision)
    
    # Validations
    assert success is True, "Driver must report success to AI"
    # Ensure it precisely hit the industrial OID required by NTCIP 1202
    assert ntcip_driver.OID_PHASE_HOLD in mock_snmp_hardware
    # Ensure mathematics match
    assert mock_snmp_hardware[ntcip_driver.OID_PHASE_HOLD] == expected_octet

@pytest.mark.integration
def test_ntcip_telemetry_fidelity(ntcip_driver, mock_snmp_hardware):
    """
    Scenario 2: Faithful Telemetry Ingestion.
    The real intersection memory sends us the street condition.
    """
    # Simulate physical detectors reporting Phases 1 and 5 are Green
    # Phase 1 (bit 0 = 1) and Phase 5 (bit 4 = 16) = 1 + 16 = 17
    mock_snmp_hardware[ntcip_driver.OID_PHASE_STATUS_GREENS] = 17
    mock_snmp_hardware[ntcip_driver.OID_PHASE_STATUS_REDS] = 0
    
    # Driver should fetch data from our memory (SNMP via mock)
    telemetry = ntcip_driver.get_telemetry()
    
    assert telemetry['protocol'] == "NTCIP 1202"
    assert telemetry['status'] == "online"
    assert telemetry['active_greens'] == 17
    assert telemetry['active_reds'] == 0

@pytest.mark.integration
def test_ntcip_connection_loss_resilience(ntcip_driver, mock_snmp_hardware):
    """
    Scenario 3: Connection Loss Resilience ("Cut network cable").
    Ensures that the SNMP request failure returns OFFLINE without severely crashing CARINA.
    """
    # Memory is EMPTY. When the driver attempts to run `snmp_get`, our 
    # Fixture will return 'False, TIMEOUT' as programmed.
    
    telemetry = ntcip_driver.get_telemetry()
    
    # Driver's core logic should absorb the shock and return OFFLINE.
    assert telemetry['status'] == "offline"
    # It must not freeze the engine and must fill primary data with zeros/nulls
    assert telemetry['active_greens'] == 0

@pytest.fixture
def utmc_driver():
    """Initializes a UTMC2 Driver connected to a dummy IP for testing."""
    return UtmcDriver(ip_address="192.168.1.101", port=161, community_string="public")

@pytest.mark.integration
def test_utmc_send_action(utmc_driver, mock_snmp_hardware):
    """
    Scenario 1 (UTMC2): Safe Command Dispatch (Action Translation).
    Ensures that the CARINA logical action is encoded in the correct mathematical base of UTMC (where phase = stage).
    """
    # CARINA decides to force green on Stage 2
    carina_decision = {'action_type': 'force_off', 'phase': 2}
    
    # Base 2 arithmetic must bit-shift (1 << (stage - 1)) = (1 << 1) = 2
    expected_octet = 2

    # Execute translation and dispatch
    success = utmc_driver.send_action(carina_decision)
    
    # Validations
    assert success is True, "Driver must report success to AI"
    # Ensure it hit exactly the industrial OID required by UTMC
    assert utmc_driver.OID_STAGE_FORCE_OFF in mock_snmp_hardware
    # Ensure mathematics match
    assert mock_snmp_hardware[utmc_driver.OID_STAGE_FORCE_OFF] == expected_octet

@pytest.mark.integration
def test_utmc_telemetry_fidelity(utmc_driver, mock_snmp_hardware):
    """
    Scenario 2 (UTMC2): Faithful Telemetry Ingestion.
    The real intersection memory sends us the street condition.
    """
    # Simulate physical detectors reporting Stage 3 is green (bit 2 = 4)
    mock_snmp_hardware[utmc_driver.OID_STAGE_STATUS_ACTIVE] = 4
    
    # Driver should fetch data from our memory (SNMP via mock)
    telemetry = utmc_driver.get_telemetry()
    
    assert telemetry['protocol'] == "UTMC2"
    assert telemetry['status'] == "online"
    assert telemetry['active_greens'] == 4

@pytest.mark.integration
def test_utmc_connection_loss_resilience(utmc_driver, mock_snmp_hardware):
    """
    Scenario 3 (UTMC2): Connection Loss Resilience ("Cut network cable").
    Ensures that the SNMP request failure returns OFFLINE without severely crashing CARINA.
    """
    # Memory is EMPTY.
    telemetry = utmc_driver.get_telemetry()
    
    assert telemetry['status'] == "offline"
    assert telemetry['active_greens'] == 0
