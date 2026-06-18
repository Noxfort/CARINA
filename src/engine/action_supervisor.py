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

# File: src/engine/action_supervisor.py
# Author: Gabriel Moraes
# Date: 2026-02-24

"""
Description:
The "Actuator" of the environment: expert in applying actions safely.
Delegates hardware communication directly to the ConnectionManager.
"""

import logging
import configparser
import sys
import os
from typing import TYPE_CHECKING, Dict, Any

# Ensure src path is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend
    from engine.state_extractor import StateExtractor
    from controller.connection_manager import HardwareConnectionManager

from utils.safety_rules import SafetyRules

class ActionSupervisor:
    """
    The "Actuator" of the environment: expert in applying actions safely.
    Delegates hardware communication directly to the ConnectionManager.
    """

    def __init__(self, connection_manager: 'HardwareConnectionManager', settings: configparser.ConfigParser,
                 state_extractor: 'StateExtractor', locale_manager: 'LocaleManagerBackend'):
        
        self.connection_manager = connection_manager
        self.state_extractor = state_extractor 
        self.locale_manager = locale_manager
        self.lm = self.locale_manager

        self._last_stage_change_time = {}
        self.vetoed_actions = {}
        self._last_sent_action = {}
        self.override_states = {}

        # Load minimum safety time rules
        self.green_time = SafetyRules.get_green()

        logging.info(self.lm.get_string("action_supervisor.init.actuator_created", fallback="ActionSupervisor initialized with ConnectionManager."))

    def update_vetos(self, vetos: dict):
        """Updates the list of actions vetoed by the Safety Layer (Guardian)."""
        if vetos:
            for tl_id, veto_signal in vetos.items():
                self.vetoed_actions[tl_id] = veto_signal.get('veto_action')

    def apply_actions(self, actions: Dict[str, int], current_sim_time: float, current_stages: Dict[str, Any]) -> None:
        """
        Executa as ações recomendadas pela IA nos respectivos drivers de hardware.
        """
        for tl_id, action in list(actions.items()):
            # 1. Check Guardian Veto
            if tl_id in self.vetoed_actions and self.vetoed_actions[tl_id] == action:
                logging.info(f"[{tl_id}] Action blocked by Guardian veto.")
                del self.vetoed_actions[tl_id]
                actions[tl_id] = 1  # Force to HOLD

    def send_stage_hold(self, tl_id: str, stage_idx: int) -> None:
        """
        Sends the hold command for the specified stage to the hardware driver.
        """
        if self.override_states.get(tl_id) in ("ALERT", "OFF"):
            logging.debug(f"[{tl_id}] Skipping send_stage_hold because of active override: {self.override_states[tl_id]}")
            return
            
        driver = self.connection_manager.active_connections.get(tl_id)
        if driver:
            # Pass 1-based stage to allow the driver to handle the hardware bitmask conversion
            driver.apply_action({'action_type': 'hold', 'stage': stage_idx + 1})

    def reset(self):
        """Clears metrics for a clean restart."""
        self._last_stage_change_time.clear()
        self.vetoed_actions.clear()
        self._last_sent_action.clear()
        self.override_states.clear()

    def apply_hardware_override(self, tl_id: str, state: str):
        """
        Interprets and sends manual UI override commands (e.g. FLASH, DARK) directly to the hardware connection.
        """
        if tl_id == "ALL" and state == "SHUTDOWN":
            for driver in self.connection_manager.active_connections.values():
                logging.critical(f"[ActionSupervisor] SHUTDOWN global: Stopping heartbeat for traffic light {driver.ip_address}")
                driver.shutdown()
            return
            
        if tl_id in self.connection_manager.active_connections:
            driver = self.connection_manager.active_connections[tl_id]
            if state == "ALERT":
                self.override_states[tl_id] = "ALERT"
                driver.apply_action({'action_type': 'flash'})
                driver.log_carina_override("ALERT")
                logging.info(f"[{tl_id}] FLASH (Alert) command sent to hardware via ActionSupervisor.")
            elif state == "OFF":
                self.override_states[tl_id] = "OFF"
                driver.apply_action({'action_type': 'dark'})
                driver.log_carina_override("OFF")
                logging.info(f"[{tl_id}] DARK (Off) command sent to hardware via ActionSupervisor.")
            elif state == "NORMAL":
                prev_state = self.override_states.pop(tl_id, None)
                if prev_state == "ALERT":
                    driver.apply_action({'action_type': 'release_flash'})
                elif prev_state == "OFF":
                    driver.apply_action({'action_type': 'release_dark'})
                logging.info(f"[{tl_id}] Traffic light returned to normal operation by operator.")