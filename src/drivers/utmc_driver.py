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
import json
import os
from typing import Dict, Any
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

    def __init__(self, ip_address: str, port: int, intersection_id: str = "Desconhecido", community_string: str = 'public', green_stages: list = None) -> None:
        super().__init__(ip_address, port, intersection_id, community_string, green_stages=green_stages)
        self._load_oids()
        logger.info(f"[{self.ip_address}:{self.port}] Initialized UTMC2 Driver.")

    def _load_oids(self) -> None:
        """Loads OIDs from an external JSON file to satisfy Open-Closed Principle."""
        json_path = os.path.join(os.path.dirname(__file__), "configs", "utmc_oids.json")
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.oids = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load UTMC OIDs from {json_path}: {e}")
            self.oids = {"stage_control": {}, "telemetry": {}, "system": {}}

    def get_protocol_name(self) -> str:
        return "UTMC2"

    def convert_stage_to_hardware_mask(self, stage_idx: int, green_stages: list, stage_codes: dict = None) -> int:
        """
        HAL Translation: Converts a SUMO stage index and its corresponding state string
        to a UTMC2 stage bitmask.
        """
        # UTMC2 expects a stage bitmask where stage_idx corresponds to bit `stage_idx`.
        # This is agnostic to the number of stages.
        mask = 1 << stage_idx
        if stage_codes and stage_idx in stage_codes:
            state_str = stage_codes[stage_idx]
            logger.debug(f"[HAL UTMC2] Translating stage index {stage_idx} (state: '{state_str}') -> stage mask: {mask}")
        else:
            logger.debug(f"[HAL UTMC2] Translating stage index {stage_idx} (no state string) -> stage mask: {mask}")
        return mask

    def send_action(self, action_data: Dict[str, Any]) -> bool:
        """
        Translates CARINA's neural network action into UTMC2 stage commands.
        Expected action_data format: {'action_type': 'hold', 'phase': 2}
        (Note: 'phase' here is mapped to UTMC 'stage')
        """
        action_type = action_data.get('action_type')
        stage = action_data.get('stage', 0)

        if not action_type:
            logger.error(f"[{self.ip_address}] Invalid action data provided to UTMC2 Driver.")
            return False

        # Calculate bitmask for the specific stage (HAL support)
        if 'stage_mask' in action_data:
            stage_bitmask = action_data['stage_mask']
        else:
            stage_bitmask = 1 << (stage - 1) if stage > 0 else 0

        success = False
        result = None

        if action_type == 'flash':
            logger.debug(f"[{self.ip_address}] Sending UTMC FLASH MODE command")
            success, result = self.snmp_set(self.oids["system"].get("flash"), 1, Integer32)
        elif action_type == 'release_flash':
            logger.debug(f"[{self.ip_address}] Sending UTMC RELEASE FLASH MODE command")
            success, result = self.snmp_set(self.oids["system"].get("flash"), 0, Integer32)
        elif action_type == 'dark':
            logger.debug(f"[{self.ip_address}] Sending UTMC DARK MODE command")
            success, result = self.snmp_set(self.oids["system"].get("dark"), 1, Integer32)
        elif action_type == 'release_dark':
            logger.debug(f"[{self.ip_address}] Sending UTMC RELEASE DARK MODE command")
            success, result = self.snmp_set(self.oids["system"].get("dark"), 0, Integer32)
        elif action_type == 'release_hold':
            logger.debug(f"[{self.ip_address}] Sending UTMC RELEASE HOLD command")
            success, result = self.snmp_set(self.oids["stage_control"].get("hold"), 0, Integer32)
        elif stage == 0 and 'stage_mask' not in action_data:
            logger.error(f"[{self.ip_address}] Stage required for UTMC action: {action_type}")
            return False
        elif action_type == 'hold':
            logger.debug(f"[{self.ip_address}] Sending UTMC HOLD for stage {stage}")
            success, result = self.snmp_set(self.oids["stage_control"].get("hold"), stage_bitmask, Integer32)
        elif action_type == 'force_off':
            logger.debug(f"[{self.ip_address}] Sending UTMC FORCE-OFF for stage {stage}")
            success, result = self.snmp_set(self.oids["stage_control"].get("force_off"), stage_bitmask, Integer32)
        elif action_type == 'omit':
            logger.debug(f"[{self.ip_address}] Sending UTMC OMIT for stage {stage}")
            success, result = self.snmp_set(self.oids["stage_control"].get("omit"), stage_bitmask, Integer32)
        elif action_type in ('demand', 'veh_call'):
            logger.debug(f"[{self.ip_address}] Sending UTMC DEMAND (Call) for stage {stage}")
            success, result = self.snmp_set(self.oids["telemetry"].get("status_demand"), stage_bitmask, Integer32)
        elif action_type == 'extend':
            logger.debug(f"[{self.ip_address}] Sending UTMC EXTEND for stage {stage}")
            success, result = self.snmp_set(self.oids["stage_control"].get("extend"), stage_bitmask, Integer32)
        elif action_type == 'ACTIVATE_LOCAL_FIXED_TIME':
            logger.critical(f"[{self.ip_address}] EXECUTING FAILSAFE: Forcing ALL RED for 2 seconds, then releasing to local plans.")
            import time
            # Compute all-red mask based on green stages count
            num_stages = len(self.green_stages) if hasattr(self, 'green_stages') else 8
            all_red_mask = (1 << num_stages) - 1 if num_stages > 0 else 65535

            self.snmp_set(self.oids["stage_control"].get("force_off"), all_red_mask, Integer32)
            self.snmp_set(self.oids["stage_control"].get("omit"), all_red_mask, Integer32)
            time.sleep(2.0)
            # Release omit so local controller can resume its fixed-time cycle
            success, result = self.snmp_set(self.oids["stage_control"].get("omit"), 0, Integer32)
            # Stop the heartbeat so the controller fully reverts to local mode
            self.stop_heartbeat()
        else:
            logger.warning(f"[{self.ip_address}] Unknown action type: {action_type}")
            return False

        if not success:
            logger.error(f"[{self.ip_address}] Failed to send UTMC action: {result}")
            
        return success

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Fetches the current status of the intersection using UTMC OIDs.
        """
        telemetry: Dict[str, Any] = {
            "protocol": self.get_protocol_name(),
            "status": "unknown",
            "active_greens": 0,
            "active_yellows": 0,
            "active_reds": 0,  # Can be inferred or polled depending on the UTMC controller spec
            "active_ped_calls": 0
        }

        # Fetch active stage (green)
        success_active, val_active = self.snmp_get(self.oids["telemetry"].get("status_active"))
        if success_active:
            telemetry["active_greens"] = int(val_active)
            telemetry["status"] = "online"

        # Fetch leaving stage (yellow/amber)
        success_leaving, val_leaving = self.snmp_get(self.oids["telemetry"].get("status_leaving"))
        if success_leaving:
            telemetry["active_yellows"] = int(val_leaving)

        # Fetch active ped calls
        success_ped, val_ped = self.snmp_get(self.oids["telemetry"].get("status_ped_demand"))
        if success_ped:
            telemetry["active_ped_calls"] = int(val_ped)

        if not success_active and not success_leaving:
            telemetry["status"] = "offline"
            logger.warning(f"[{self.ip_address}] Failed to fetch UTMC telemetry.")

        return telemetry

    def send_heartbeat_pulse(self) -> bool:
        """
        Sends a heartbeat pulse to maintain remote control over the UTMC controller.
        Writes a pulse value to the UTMC watchdog OID.
        """
        pulse_value = 1 
        success, result = self.snmp_set(self.oids["system"].get("watchdog"), pulse_value, Integer32)
        
        if not success:
            logger.error(f"[{self.ip_address}] UTMC Heartbeat pulse failed: {result}")
            
        return success

    def apply_logical_action(self, action: int, current_stage_idx: int, green_stages: list, stage_codes: dict = None) -> bool:
        """
        Implements UTMC-specific logical action sequence translation.
        Translates raw AI actions (0 = NEXT_STAGE, 1 = HOLD) using UTMC stage commands.
        """
        if not green_stages or current_stage_idx not in green_stages:
            return False

        try:
            current_list_idx = green_stages.index(current_stage_idx)

            # Determine the target stage index for this action
            if action == 0:  # NEXT_STAGE
                next_list_idx = (current_list_idx + 1) % len(green_stages)
                target_stage_idx = green_stages[next_list_idx]
            else:  # HOLD
                target_stage_idx = current_stage_idx

            # HAL Translation: Convert target stage index to hardware mask
            stage_mask = self.convert_stage_to_hardware_mask(target_stage_idx, green_stages, stage_codes)

            if action == 0:  # NEXT_STAGE
                next_list_idx = (current_list_idx + 1) % len(green_stages)
                next_stage_mask = self.convert_stage_to_hardware_mask(target_stage_idx, green_stages, stage_codes)
                current_stage_mask = self.convert_stage_to_hardware_mask(current_stage_idx, green_stages, stage_codes)

                logger.info(f"[{self.ip_address}] UTMC HAL translating NEXT_STAGE: stage {current_stage_idx} -> {target_stage_idx} (mask {current_stage_mask} -> {next_stage_mask})")
                
                # Protocol specific sequence translation:
                # 1. Release active hold
                self.send_action({'action_type': 'release_hold'})
                
                # 2. Send FORCE_OFF command for current stage
                self.send_action({'action_type': 'force_off', 'stage_mask': current_stage_mask})
                
                # 3. Call next stage to trigger transition
                self.send_action({'action_type': 'veh_call', 'stage_mask': next_stage_mask})
                return True

            else:  # HOLD
                logger.debug(f"[{self.ip_address}] UTMC HAL translating HOLD for stage {current_stage_idx} (mask {stage_mask})")
                return self.send_action({'action_type': 'hold', 'stage_mask': stage_mask})

        except Exception as e:
            logger.error(f"[{self.ip_address}] Error in UTMC apply_logical_action: {e}")
            return False