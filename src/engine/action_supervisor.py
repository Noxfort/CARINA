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
from typing import TYPE_CHECKING

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

        self._last_phase_change_time = {}
        self.vetoed_actions = {}

        # Load minimum safety time rules
        self.min_green_time = SafetyRules.get_min_green()

        logging.info(self.lm.get_string("action_supervisor.init.actuator_created", fallback="ActionSupervisor initialized with ConnectionManager."))

    def update_vetos(self, vetos: dict):
        """Updates the list of actions vetoed by the Safety Layer (Guardian)."""
        if vetos:
            for tl_id, veto_signal in vetos.items():
                self.vetoed_actions[tl_id] = veto_signal.get('veto_action')

    def apply_actions(self, actions: dict, current_sim_time: float, current_phases: dict):
        """
        Receives neural network decisions and forwards them to the hardware if not vetoed.
        """
        for tl_id, action in actions.items():
            # 1. Check Guardian Veto
            if tl_id in self.vetoed_actions and self.vetoed_actions[tl_id] == action:
                logging.info(f"[{tl_id}] Action blocked by Guardian veto.")
                del self.vetoed_actions[tl_id]
                continue

            # 2. Execute Action
            if action == 0: 
                # NEXT_PHASE (Neural network wants to change the light)
                self._try_change_phase(tl_id, current_sim_time, current_phases.get(tl_id, 0))
            else: 
                # HOLD (Neural network wants to maintain current green)
                self._try_hold_phase(tl_id, current_sim_time, current_phases.get(tl_id, 0))

    def _try_change_phase(self, tl_id: str, current_time: float, current_phase_idx: int):
        """Attempts to advance to the next phase while respecting minimum times."""
        time_since_last = current_time - self._last_phase_change_time.get(tl_id, 0)
        if time_since_last < self.min_green_time:
            return

        green_phases = self.state_extractor.tl_green_phases.get(tl_id, [])
        if not green_phases or current_phase_idx not in green_phases:
            return

        try:
            # Discover the next phase in the sequence
            current_list_idx = green_phases.index(current_phase_idx)
            next_list_idx = (current_list_idx + 1) % len(green_phases)
            next_phase_idx = green_phases[next_list_idx]

            action_data = {'action_type': 'force_off', 'phase': current_phase_idx}

            # Direct Hardware Communication via SNMP (NTCIP/UTMC)
            if tl_id in self.connection_manager.active_connections:
                driver = self.connection_manager.active_connections[tl_id]
                driver.apply_action(action_data)
            
            # Register the time of the change
            self._last_phase_change_time[tl_id] = current_time
            
        except ValueError:
            pass

    def _try_hold_phase(self, tl_id: str, current_time: float, current_phase_idx: int):
        """Sends the HOLD command to actively extend the green time."""
        action_data = {'action_type': 'hold', 'phase': current_phase_idx}

        if tl_id in self.connection_manager.active_connections:
            driver = self.connection_manager.active_connections[tl_id]
            driver.apply_action(action_data)

    def reset(self):
        """Clears metrics for a clean restart."""
        self._last_phase_change_time.clear()
        self.vetoed_actions.clear()