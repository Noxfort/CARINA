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

# File: src/drivers/utmc_driver.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
UTMC2 protocol implementation for traffic light controllers.
Translates CARINA commands into UTMC-compliant SNMP OID requests.
"""

import logging
from src.drivers.base_driver import BaseTrafficDriver

# --- PySNMP Data Types Compatibility Block ---
# Ensures Integer32 is loaded regardless of the PySNMP version (v6 or v7+)
try:
    # Core protocol definition (Works on PySNMP v7+ and older)
    from pysnmp.proto.rfc1902 import Integer32
except ImportError:
    try:
        # Fallback for specific Asyncio/LeXtudio modern branches
        from pysnmp.hlapi.v3arch.asyncio import Integer32
    except ImportError:
        # Legacy PySNMP fallback (v5/v6)
        from pysnmp.hlapi import Integer32

logger = logging.getLogger(__name__)

class UtmcDriver(BaseTrafficDriver):
    """
    Driver specifically built to handle the UTMC2 protocol.
    Uses Standard OIDs defined in the UTMC TS004 / TS005 specifications.
    Note: UTMC often refers to 'Stages' rather than 'Phases'.
    """

    # --- UTMC Standard OIDs (Examples based on TS004 Data Dictionary) ---
    # Stage Control Group (e.g., Hold, Force-Off)
    OID_STAGE_HOLD = "1.3.6.1.4.1.2825.4.2.1.1.4.1.2.1"
    OID_STAGE_FORCE_OFF = "1.3.6.1.4.1.2825.4.2.1.1.4.1.3.1"
    
    # Telemetry OIDs (Status of current running stages)
    OID_STAGE_STATUS_ACTIVE = "1.3.6.1.4.1.2825.4.2.1.1.4.1.4.1"
    OID_STAGE_STATUS_DEMAND = "1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1"
    
    # System Control/Heartbeat OID (Watchdog)
    OID_UTMC_WATCHDOG = "1.3.6.1.4.1.2825.4.2.1.1.2.1.21.1"

    def __init__(self, ip_address: str, port: int, community_string: str = 'public'):
        super().__init__(ip_address, port, community_string)
        logger.info(f"[{self.ip_address}:{self.port}] Initialized UTMC2 Driver.")

    def get_protocol_name(self) -> str:
        return "UTMC2"

    def send_action(self, action_data: dict) -> bool:
        """
        Translates CARINA's neural network action into UTMC2 stage commands.
        Expected action_data format: {'action_type': 'hold', 'phase': 2}
        (Note: 'phase' here is mapped to UTMC 'stage')
        """
        action_type = action_data.get('action_type')
        stage = action_data.get('phase', 0)

        if not action_type or stage == 0:
            logger.error(f"[{self.ip_address}] Invalid action data provided to UTMC2 Driver.")
            return False

        # Calculate bitmask for the specific stage
        stage_bitmask = 1 << (stage - 1)

        success = False
        result = None

        if action_type == 'hold':
            logger.debug(f"[{self.ip_address}] Sending UTMC HOLD for stage {stage}")
            success, result = self.snmp_set(self.OID_STAGE_HOLD, stage_bitmask, Integer32)
        elif action_type == 'force_off':
            logger.debug(f"[{self.ip_address}] Sending UTMC FORCE-OFF for stage {stage}")
            success, result = self.snmp_set(self.OID_STAGE_FORCE_OFF, stage_bitmask, Integer32)
        else:
            logger.warning(f"[{self.ip_address}] Unknown action type: {action_type}")
            return False

        if not success:
            logger.error(f"[{self.ip_address}] Failed to send UTMC action: {result}")
            
        return success

    def get_telemetry(self) -> dict:
        """
        Fetches the current status of the intersection using UTMC OIDs.
        """
        telemetry = {
            "protocol": self.get_protocol_name(),
            "status": "unknown",
            "active_greens": 0,
            "active_reds": 0  # Can be inferred or polled depending on the UTMC controller spec
        }

        # Fetch active stage (green)
        success_active, val_active = self.snmp_get(self.OID_STAGE_STATUS_ACTIVE)
        if success_active:
            telemetry["active_greens"] = int(val_active)
            telemetry["status"] = "online"

        if not success_active:
            telemetry["status"] = "offline"
            logger.warning(f"[{self.ip_address}] Failed to fetch UTMC telemetry.")

        return telemetry

    def send_heartbeat_pulse(self) -> bool:
        """
        Sends a heartbeat pulse to maintain remote control over the UTMC controller.
        Writes a pulse value to the UTMC watchdog OID.
        """
        pulse_value = 1 
        success, result = self.snmp_set(self.OID_UTMC_WATCHDOG, pulse_value, Integer32)
        
        if not success:
            logger.error(f"[{self.ip_address}] UTMC Heartbeat pulse failed: {result}")
            
        return success