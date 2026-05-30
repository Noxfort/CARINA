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

# File: src/drivers/ntcip_driver.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
NTCIP 1202 protocol implementation for traffic light controllers.
Translates CARINA commands into NTCIP-compliant SNMP OID requests.
"""

import logging
from src.drivers.base_driver import BaseTrafficDriver

# --- PySNMP Data Types Compatibility Block ---
# Ensures Integer32 and OctetString are loaded regardless of the PySNMP version (v6 or v7+)
try:
    # Core protocol definition (Works on PySNMP v7+ and older)
    from pysnmp.proto.rfc1902 import Integer32, OctetString
except ImportError:
    try:
        # Fallback for specific Asyncio/LeXtudio modern branches
        from pysnmp.hlapi.v3arch.asyncio import Integer32, OctetString
    except ImportError:
        # Legacy PySNMP fallback (v5/v6)
        from pysnmp.hlapi import Integer32, OctetString

logger = logging.getLogger(__name__)

class NtcipDriver(BaseTrafficDriver):
    """
    Driver specifically built to handle NTCIP v03 protocol.
    Uses Standard OIDs defined in NTCIP 1202 for Actuated Traffic Signal Controller Units.
    """

    # --- NTCIP 1202 Standard OIDs (Examples) ---
    # Phase Control Group (e.g., Hold, Force-Off, Omit)
    OID_PHASE_HOLD = "1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1"
    OID_PHASE_FORCE_OFF = "1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1"
    OID_PHASE_OMIT = "1.3.6.1.4.1.1206.4.2.1.1.4.1.7.1"
    OID_PHASE_VEH_CALL = "1.3.6.1.4.1.1206.4.2.1.1.4.1.6.1"
    OID_PHASE_PED_CALL = "1.3.6.1.4.1.1206.4.2.1.1.4.1.8.1"
    
    # Telemetry OIDs
    OID_PHASE_STATUS_GREENS = "1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1"
    OID_PHASE_STATUS_YELLOWS = "1.3.6.1.4.1.1206.4.2.1.1.4.1.5.1"
    OID_PHASE_STATUS_REDS = "1.3.6.1.4.1.1206.4.2.1.1.4.1.6.1"  # Corrected to standard REDs OID
    OID_PHASE_STATUS_PED_CALLS = "1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1"
    
    # System Control/Heartbeat OID
    # In NTCIP, remote control requires maintaining a valid value in the system control OID
    OID_SYSTEM_HEARTBEAT = "1.3.6.1.4.1.1206.4.2.1.1.2.1.21.1"

    def __init__(self, ip_address: str, port: int, community_string: str = 'public'):
        super().__init__(ip_address, port, community_string)
        logger.info(f"[{self.ip_address}:{self.port}] Initialized NTCIP Driver.")

    def get_protocol_name(self) -> str:
        return "NTCIP 1202"

    def send_action(self, action_data: dict) -> bool:
        """
        Translates CARINA's neural network action into NTCIP commands.
        Expected action_data format: {'action_type': 'hold', 'phase': 2}
        """
        action_type = action_data.get('action_type')
        phase = action_data.get('phase', 0)

        if not action_type or phase == 0:
            logger.error(f"[{self.ip_address}] Invalid action data provided to NTCIP Driver.")
            return False

        # Calculate bitmask for the specific phase (Phase 1 = bit 0, Phase 2 = bit 1, etc.)
        phase_bitmask = 1 << (phase - 1)

        success = False
        result = None

        if action_type == 'hold':
            logger.debug(f"[{self.ip_address}] Sending NTCIP HOLD for phase {phase}")
            success, result = self.snmp_set(self.OID_PHASE_HOLD, phase_bitmask, Integer32)
        elif action_type == 'force_off':
            logger.debug(f"[{self.ip_address}] Sending NTCIP FORCE-OFF for phase {phase}")
            success, result = self.snmp_set(self.OID_PHASE_FORCE_OFF, phase_bitmask, Integer32)
        elif action_type == 'omit':
            logger.debug(f"[{self.ip_address}] Sending NTCIP OMIT for phase {phase}")
            success, result = self.snmp_set(self.OID_PHASE_OMIT, phase_bitmask, Integer32)
        elif action_type == 'veh_call':
            logger.debug(f"[{self.ip_address}] Sending NTCIP VEHICULAR CALL for phase {phase}")
            success, result = self.snmp_set(self.OID_PHASE_VEH_CALL, phase_bitmask, Integer32)
        elif action_type == 'ped_call':
            logger.debug(f"[{self.ip_address}] Sending NTCIP PEDESTRIAN CALL for phase {phase}")
            success, result = self.snmp_set(self.OID_PHASE_PED_CALL, phase_bitmask, Integer32)
        else:
            logger.warning(f"[{self.ip_address}] Unknown action type: {action_type}")
            return False

        if not success:
            logger.error(f"[{self.ip_address}] Failed to send NTCIP action: {result}")
            
        return success

    def get_telemetry(self) -> dict:
        """
        Fetches the current status of the intersection using NTCIP OIDs.
        """
        telemetry = {
            "protocol": self.get_protocol_name(),
            "status": "unknown",
            "active_greens": 0,
            "active_yellows": 0,
            "active_reds": 0,
            "active_ped_calls": 0
        }

        # Fetch active greens
        success_green, val_green = self.snmp_get(self.OID_PHASE_STATUS_GREENS)
        if success_green:
            telemetry["active_greens"] = int(val_green)
            telemetry["status"] = "online"

        # Fetch active yellows
        success_yellow, val_yellow = self.snmp_get(self.OID_PHASE_STATUS_YELLOWS)
        if success_yellow:
            telemetry["active_yellows"] = int(val_yellow)

        # Fetch active reds
        success_red, val_red = self.snmp_get(self.OID_PHASE_STATUS_REDS)
        if success_red:
            telemetry["active_reds"] = int(val_red)

        # Fetch active ped calls
        success_ped, val_ped = self.snmp_get(self.OID_PHASE_STATUS_PED_CALLS)
        if success_ped:
            telemetry["active_ped_calls"] = int(val_ped)

        if not success_green and not success_yellow and not success_red:
            telemetry["status"] = "offline"
            logger.warning(f"[{self.ip_address}] Failed to fetch NTCIP telemetry.")

        return telemetry

    def send_heartbeat_pulse(self) -> bool:
        """
        Sends a heartbeat pulse to maintain remote control over the NTCIP controller.
        Writes a specific value (e.g., 1 for active) to the system control OID.
        """
        # Sending a pulse value, usually defined by the specific controller's MIB
        pulse_value = 1 
        success, result = self.snmp_set(self.OID_SYSTEM_HEARTBEAT, pulse_value, Integer32)
        
        if not success:
            logger.error(f"[{self.ip_address}] NTCIP Heartbeat pulse failed: {result}")
            
        return success