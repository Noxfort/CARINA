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

# File: src/engine/action_filter.py
# Author: Gabriel Moraes
# Date: April 15, 2026

from typing import Dict, Tuple

from core.system_reporter import SystemReporter
from core.enums import Maturity
from core.action_authorizer import ActionAuthorizer
from core.maturity_manager import MaturityManager
from utils.locale_manager_backend import LocaleManagerBackend

class ActionFilter:
    """
    Applies Authorization, UI Manual Overrides, and Decision Logging
    to the RAW actions computed by the Neural Network.
    """

    def __init__(self, action_authorizer: ActionAuthorizer, maturity_manager: MaturityManager, locale_manager: LocaleManagerBackend):
        self.action_authorizer = action_authorizer
        self.maturity_manager = maturity_manager
        self.locale_manager = locale_manager

    def filter_actions(self, raw_actions: Dict[str, int], override_states: Dict[str, str], current_sim_time: float) -> Dict[str, int]:
        lm = self.locale_manager
        authorized_actions = {}
        
        for tl_id, action_int in raw_actions.items():
            agent_maturity = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
            
            # 1. Authorization (Driving School rules)
            is_authorized, reason = self.action_authorizer.is_action_authorized(
                tl_id, agent_maturity, current_sim_time
            )
            
            # 2. UI Override verification
            override_state = override_states.get(tl_id, "NORMAL")
            
            if override_state != "NORMAL":
                is_authorized = False
                reason_key = f"reporter.override_suffix_{override_state.lower()}"
                reason = lm.get_string(reason_key, fallback=override_state)
            
            # Telemetry Formatting
            action_str = lm.get_string("actions.keep_stage")
            if action_int == 0:
                action_str = lm.get_string("actions.change_stage")
                
            maturity_str = agent_maturity.name
            
            # Publish Report
            SystemReporter.report_agent_decision(
                lm, tl_id, maturity_str, action_str, is_authorized, reason, override_state
            )

            if is_authorized:
                authorized_actions[tl_id] = action_int

        return authorized_actions
