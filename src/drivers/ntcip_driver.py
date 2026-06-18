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
import json
import os
from typing import Dict, Any
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

    def __init__(self, ip_address: str, port: int, intersection_id: str = "Desconhecido", community_string: str = 'public', green_stages: list = None) -> None:
        super().__init__(ip_address, port, intersection_id, community_string, green_stages=green_stages)
        self.stage_to_phase_map = {}
        self._load_oids()
        
        logger.info(f"[{self.ip_address}:{self.port}] Initialized NTCIP Driver with Dynamic Stage Mapping.")

    def _load_oids(self) -> None:
        """Loads OIDs and configurations from an external JSON file to satisfy Open-Closed Principle."""
        json_path = os.path.join(os.path.dirname(__file__), "configs", "ntcip_oids.json")
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.oids = json.load(f)
            # Parse stage_to_phase_map from configuration dynamically
            raw_map = self.oids.get("stage_to_phase_map", {})
            self.stage_to_phase_map = {int(k): int(v) for k, v in raw_map.items()}
        except Exception as e:
            logger.error(f"Failed to load NTCIP OIDs from {json_path}: {e}")
            self.oids = {"phase_control": {}, "telemetry": {}, "system": {}}
            self.stage_to_phase_map = {}

    def get_protocol_name(self) -> str:
        return "NTCIP 1202"

    def convert_stage_to_hardware_mask(self, stage_idx: int, green_stages: list, stage_codes: dict = None) -> int:
        """
        HAL Translation: Converts a SUMO stage index and its corresponding state string
        to an NTCIP 1202 phase bitmask.
        """
        # NTCIP expects a phase bitmask.
        # If the number of green stages is 4 and they are mapped in stage_to_phase_map,
        # we can use the hardcoded mapping for backward compatibility.
        # Otherwise, if we have the state string, we dynamically build the phase mask.
        stage_num = stage_idx + 1
        
        # Bypass hardcoded map if we have 5 stages (meaning transitional stages are included),
        # since the 4-stage map wouldn't map them correctly.
        use_hardcoded = len(green_stages) == 4 and stage_num in self.stage_to_phase_map
        
        if use_hardcoded:
            mask = self.stage_to_phase_map[stage_num]
            logger.debug(f"[HAL NTCIP 1202] Using hardcoded map for stage {stage_num} -> phase mask: {mask}")
            return mask
            
        if stage_codes and stage_idx in stage_codes:
            state_str = stage_codes[stage_idx]
            # Find active indices (only green 'g' or yellow 'y' characters)
            active_indices = [i for i, char in enumerate(state_str) if char.lower() in ('g', 'y')]
            if not active_indices:
                logger.debug(f"[HAL NTCIP 1202] All red state for stage index {stage_idx} -> phase mask: 0")
                return 0
                
            # Map each active index to NTCIP phase.
            # Since standard NTCIP has 8 phases, we map index `i` to bit `i % 8`.
            mask = 0
            for idx in active_indices:
                mask |= (1 << (idx % 8))
            logger.debug(f"[HAL NTCIP 1202] Dynamically mapped stage index {stage_idx} (state: '{state_str}') -> phase mask: {mask}")
            return mask
            
        # Fallback to direct bit shifting
        mask = 1 << stage_idx
        logger.debug(f"[HAL NTCIP 1202] Fallback mapping for stage index {stage_idx} -> phase mask: {mask}")
        return mask

    def send_action(self, action_data: Dict[str, Any]) -> bool:
        """
        Translates CARINA's neural network action into NTCIP commands.
        Expected action_data format: {'action_type': 'hold', 'phase': 2}
        """
        action_type = action_data.get('action_type')
        stage = action_data.get('stage', 0)

        if not action_type:
            logger.error(f"[{self.ip_address}] Invalid action data provided to NTCIP Driver.")
            return False

        # Convert Stage to NTCIP Phase Bitmask using the mapping (HAL support)
        if 'stage_mask' in action_data:
            phase_bitmask = action_data['stage_mask']
        elif stage > 0:
            phase_bitmask = self.stage_to_phase_map.get(stage, 1 << (stage - 1))
        else:
            phase_bitmask = 0

        success = False
        result = None

        if action_type == 'flash':
            logger.debug(f"[{self.ip_address}] Sending NTCIP FLASH MODE command")
            success, result = self.snmp_set(self.oids["system"].get("flash"), 1, Integer32)
        elif action_type == 'release_flash':
            logger.debug(f"[{self.ip_address}] Sending NTCIP RELEASE FLASH MODE command")
            success, result = self.snmp_set(self.oids["system"].get("flash"), 0, Integer32)
        elif action_type == 'dark':
            logger.debug(f"[{self.ip_address}] Sending NTCIP DARK MODE command")
            success, result = self.snmp_set(self.oids["system"].get("dark"), 1, Integer32)
        elif action_type == 'release_dark':
            logger.debug(f"[{self.ip_address}] Sending NTCIP RELEASE DARK MODE command")
            success, result = self.snmp_set(self.oids["system"].get("dark"), 0, Integer32)
        elif action_type == 'release_hold':
            logger.debug(f"[{self.ip_address}] Sending NTCIP RELEASE HOLD command")
            success, result = self.snmp_set(self.oids["phase_control"].get("hold"), 0, Integer32)
        elif stage == 0 and 'stage_mask' not in action_data:
            logger.error(f"[{self.ip_address}] Stage required for NTCIP action: {action_type}")
            return False
        elif action_type == 'hold':
            logger.debug(f"[{self.ip_address}] Sending NTCIP HOLD for stage {stage} (Mask {phase_bitmask})")
            success, result = self.snmp_set(self.oids["phase_control"].get("hold"), phase_bitmask, Integer32)
        elif action_type == 'force_off':
            logger.debug(f"[{self.ip_address}] Sending NTCIP FORCE-OFF for stage {stage} (Mask {phase_bitmask})")
            success, result = self.snmp_set(self.oids["phase_control"].get("force_off"), phase_bitmask, Integer32)
        elif action_type == 'omit':
            logger.debug(f"[{self.ip_address}] Sending NTCIP OMIT for stage {stage} (Mask {phase_bitmask})")
            success, result = self.snmp_set(self.oids["phase_control"].get("omit"), phase_bitmask, Integer32)
        elif action_type == 'veh_call':
            logger.debug(f"[{self.ip_address}] Sending NTCIP VEHICULAR CALL for stage {stage} (Mask {phase_bitmask})")
            success, result = self.snmp_set(self.oids["phase_control"].get("veh_call"), phase_bitmask, Integer32)
        elif action_type == 'ped_call':
            logger.debug(f"[{self.ip_address}] Sending NTCIP PEDESTRIAN CALL for stage {stage} (Mask {phase_bitmask})")
            success, result = self.snmp_set(self.oids["phase_control"].get("ped_call"), phase_bitmask, Integer32)
        elif action_type == 'ACTIVATE_LOCAL_FIXED_TIME':
            logger.critical(f"[{self.ip_address}] EXECUTING FAILSAFE: Forcing ALL RED for 2 seconds, then releasing to local plans.")
            import time
            # Compute all-red mask from stage_to_phase_map
            all_red_mask = 0
            for mask in self.stage_to_phase_map.values():
                all_red_mask |= mask
            if all_red_mask == 0:
                # Fallback based on green stages count
                num_stages = len(self.green_stages) if hasattr(self, 'green_stages') else 8
                all_red_mask = (1 << num_stages) - 1 if num_stages > 0 else 65535

            self.snmp_set(self.oids["phase_control"].get("force_off"), all_red_mask, Integer32)
            self.snmp_set(self.oids["phase_control"].get("omit"), all_red_mask, Integer32)
            time.sleep(2.0)
            # Release omit so local controller can resume its fixed-time cycle
            success, result = self.snmp_set(self.oids["phase_control"].get("omit"), 0, Integer32)
            # Stop the heartbeat so the controller fully reverts to local mode
            self.stop_heartbeat()
        else:
            logger.warning(f"[{self.ip_address}] Unknown action type: {action_type}")
            return False

        if not success:
            logger.error(f"[{self.ip_address}] Failed to send NTCIP action: {result}")
            
        return success

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Fetches the current status of the intersection using NTCIP OIDs.
        """
        telemetry: Dict[str, Any] = {
            "protocol": self.get_protocol_name(),
            "status": "unknown",
            "active_greens": 0,
            "active_yellows": 0,
            "active_reds": 0,
            "active_ped_calls": 0
        }

        # Fetch active greens
        success_green, val_green = self.snmp_get(self.oids["telemetry"].get("status_greens"))
        if success_green:
            telemetry["active_greens"] = int(val_green)
            telemetry["status"] = "online"

        # Fetch active yellows
        success_yellow, val_yellow = self.snmp_get(self.oids["telemetry"].get("status_yellows"))
        if success_yellow:
            telemetry["active_yellows"] = int(val_yellow)

        # Fetch active reds
        success_red, val_red = self.snmp_get(self.oids["telemetry"].get("status_reds"))
        if success_red:
            telemetry["active_reds"] = int(val_red)

        # Fetch active ped calls
        success_ped, val_ped = self.snmp_get(self.oids["telemetry"].get("status_ped_calls"))
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
        success, result = self.snmp_set(self.oids["system"].get("heartbeat"), pulse_value, Integer32)
        
        if not success:
            logger.error(f"[{self.ip_address}] NTCIP Heartbeat pulse failed: {result}")
            
        return success

    def apply_logical_action(self, action: int, current_stage_idx: int, green_stages: list, stage_codes: dict = None) -> bool:
        """
        Implements NTCIP-specific logical action sequence translation.
        Translates raw AI actions (0 = NEXT_STAGE, 1 = HOLD) using NTCIP phase commands.
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

                logger.info(f"[{self.ip_address}] NTCIP HAL translating NEXT_STAGE: stage {current_stage_idx} -> {target_stage_idx} (mask {current_stage_mask} -> {next_stage_mask})")
                
                # Protocol specific sequence translation:
                # 1. Release active hold
                self.send_action({'action_type': 'release_hold'})
                
                # 2. Send FORCE_OFF command for current stage
                self.send_action({'action_type': 'force_off', 'stage_mask': current_stage_mask})
                
                # 3. Call next stage to trigger transition
                self.send_action({'action_type': 'veh_call', 'stage_mask': next_stage_mask})
                return True

            else:  # HOLD
                logger.debug(f"[{self.ip_address}] NTCIP HAL translating HOLD for stage {current_stage_idx} (mask {stage_mask})")
                return self.send_action({'action_type': 'hold', 'stage_mask': stage_mask})

        except Exception as e:
            logger.error(f"[{self.ip_address}] Error in NTCIP apply_logical_action: {e}")
            return False