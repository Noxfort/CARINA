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
    # CARINA decides to force green on Stage 3
    carina_decision = {'action_type': 'hold', 'stage': 3}
    
    # In stage_to_phase_map: 3 maps to (1 << 0) | (1 << 4) = 17
    expected_octet = 17 

    # Execute the translation and dispatch
    success = ntcip_driver.send_action(carina_decision)
    
    # Validations
    assert success is True, "Driver must report success to AI"
    hold_oid = ntcip_driver.oids["phase_control"].get("hold")
    # Ensure it precisely hit the industrial OID required by NTCIP 1202
    assert hold_oid in mock_snmp_hardware
    # Ensure mathematics match
    assert mock_snmp_hardware[hold_oid] == expected_octet

@pytest.mark.integration
def test_ntcip_telemetry_fidelity(ntcip_driver, mock_snmp_hardware):
    """
    Scenario 2: Faithful Telemetry Ingestion.
    The real intersection memory sends us the street condition.
    """
    greens_oid = ntcip_driver.oids["telemetry"].get("status_greens")
    yellows_oid = ntcip_driver.oids["telemetry"].get("status_yellows")
    reds_oid = ntcip_driver.oids["telemetry"].get("status_reds")
    ped_calls_oid = ntcip_driver.oids["telemetry"].get("status_ped_calls")

    # Simulate physical detectors reporting Phases 1 and 5 are Green
    # Phase 1 (bit 0 = 1) and Phase 5 (bit 4 = 16) = 1 + 16 = 17
    mock_snmp_hardware[greens_oid] = 17
    mock_snmp_hardware[yellows_oid] = 2 # Phase 2 is yellow
    mock_snmp_hardware[reds_oid] = 0
    mock_snmp_hardware[ped_calls_oid] = 8 # Ped call on phase 4
    
    # Driver should fetch data from our memory (SNMP via mock)
    telemetry = ntcip_driver.get_telemetry()
    
    assert telemetry['protocol'] == "NTCIP 1202"
    assert telemetry['status'] == "online"
    assert telemetry['active_greens'] == 17
    assert telemetry['active_yellows'] == 2
    assert telemetry['active_reds'] == 0
    assert telemetry['active_ped_calls'] == 8

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
    carina_decision = {'action_type': 'force_off', 'stage': 2}
    
    # Base 2 arithmetic must bit-shift (1 << (stage - 1)) = (1 << 1) = 2
    expected_octet = 2

    # Execute translation and dispatch
    success = utmc_driver.send_action(carina_decision)
    
    # Validations
    assert success is True, "Driver must report success to AI"
    force_off_oid = utmc_driver.oids["stage_control"].get("force_off")
    # Ensure it hit exactly the industrial OID required by UTMC
    assert force_off_oid in mock_snmp_hardware
    # Ensure mathematics match
    assert mock_snmp_hardware[force_off_oid] == expected_octet

@pytest.mark.integration
def test_utmc_telemetry_fidelity(utmc_driver, mock_snmp_hardware):
    """
    Scenario 2 (UTMC2): Faithful Telemetry Ingestion.
    The real intersection memory sends us the street condition.
    """
    active_oid = utmc_driver.oids["telemetry"].get("status_active")
    leaving_oid = utmc_driver.oids["telemetry"].get("status_leaving")
    ped_demand_oid = utmc_driver.oids["telemetry"].get("status_ped_demand")

    # Simulate physical detectors reporting Stage 3 is green (bit 2 = 4)
    mock_snmp_hardware[active_oid] = 4
    mock_snmp_hardware[leaving_oid] = 2 # Stage 2 leaving
    mock_snmp_hardware[ped_demand_oid] = 1 # Ped demand on Stage 1
    
    # Driver should fetch data from our memory (SNMP via mock)
    telemetry = utmc_driver.get_telemetry()
    
    assert telemetry['protocol'] == "UTMC2"
    assert telemetry['status'] == "online"
    assert telemetry['active_greens'] == 4
    assert telemetry['active_yellows'] == 2
    assert telemetry['active_ped_calls'] == 1

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

@pytest.mark.integration
def test_ntcip_dynamic_hal_translation(ntcip_driver, mock_snmp_hardware):
    """
    Verifies that NtcipDriver dynamically translates stage indices and state strings
    into NTCIP 1202 phase bitmasks using the HAL logic.
    """
    stage_codes = {
        0: "GgOrrOGGO",  # Active indices: 0, 1, 6, 7 -> bits 0, 1, 6, 7 (mask 195)
        1: "yyyrrrGyy",  # Active indices: 0, 1, 2, 6, 7, 8 -> bits 0, 1, 2, 6, 7, 0 (mask 1+2+4+64+128 = 199)
        2: "rrrGGgGrr",  # Active indices: 3, 4, 5, 6 -> bits 3, 4, 5, 6 (mask 8+16+32+64 = 120)
        3: "rrrrrrrrr"   # All red -> mask 0
    }
    # Test dynamic translation for HOLD on Stage 0 ("GgOrrOGGO")
    # Using 5 stages/green_stages list (length not 4) to bypass hardcoded mapping
    success = ntcip_driver.apply_logical_action(action=1, current_stage_idx=0, green_stages=[0, 1, 2, 3, 4], stage_codes=stage_codes)
    assert success is True
    hold_oid = ntcip_driver.oids["phase_control"].get("hold")
    assert mock_snmp_hardware[hold_oid] == 195

    # Test dynamic translation for HOLD on Stage 2 ("rrrGGgGrr")
    success = ntcip_driver.apply_logical_action(action=1, current_stage_idx=2, green_stages=[0, 1, 2, 3, 4], stage_codes=stage_codes)
    assert success is True
    assert mock_snmp_hardware[hold_oid] == 120


@pytest.mark.integration
def test_utmc_dynamic_hal_translation(utmc_driver, mock_snmp_hardware):
    """
    Verifies that UtmcDriver dynamically translates stage indices and state strings
    into UTMC2 stage bitmasks using the HAL logic.
    """
    stage_codes = {
        0: "GgOrrOGGO",
        1: "yyyrrrGyy",
        2: "rrrGGgGrr"
    }
    green_stages = [0, 1, 2]

    # Test dynamic translation for HOLD on Stage 2
    success = utmc_driver.apply_logical_action(action=1, current_stage_idx=2, green_stages=green_stages, stage_codes=stage_codes)
    assert success is True
    hold_oid = utmc_driver.oids["stage_control"].get("hold")
    # Stage index 2 should map to bitmask 1 << 2 = 4
    assert mock_snmp_hardware[hold_oid] == 4

