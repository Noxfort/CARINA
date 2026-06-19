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

# File: src/sds/tls_state_provider.py
# Author: Gabriel Moraes
# Date: 2026-02-24

"""
Description:
Specialist class responsible for providing the current operational state 
(colors/phases and global display state) of traffic lights.
Features a 2-Stage Visual Transition Engine that renders realistic Yellow phases 
followed by All-Red clearance phases during telemetry phase jumps.
"""

import time
import configparser
from sds.tls_map_extractor import TlsMapExtractor
from utils.settings_manager import SettingsManager
from utils.safety_rules import SafetyRules

class TlsStateProvider:
    """
    Acts as the definitive source of truth for the UI dashboard.
    Converts the phase telemetry from the Formatter into realistic colored states,
    enforcing a strict physical flow: Green -> Yellow -> All-Red -> Next Green.
    """

    _current_display_phases = {}
    _transition_timers = {}
    
    _yellow_duration_seconds = None
    _all_red_duration_seconds = None


    @classmethod
    def get_live_states_for_junction(cls, incoming_edges: list, tl_id: str, phase_idx: int) -> dict:
        """
        Calculates the realistic traffic light state for a given set of approaching streets.
        Directly queries the current active phase without artificial transition delays,
        ensuring perfect correspondence between the UI dashboard and the controller telemetry.
        """
        lanes_state_dict = {}
        
        focal_groups = TlsMapExtractor.get_all_focal_groups_for_tl(tl_id)
        
        if not focal_groups:
            lanes_state_dict["Unknown_Group"] = "r"
            return {"lanes_state": lanes_state_dict, "display_state": "RED"}

        extracted_colors = TlsMapExtractor.get_edge_colors_for_phase(tl_id, phase_idx)

        # Map the resolved colors to the focal groups
        for fg in focal_groups:
            lanes_state_dict[fg] = extracted_colors.get(fg, 'r')
            
        # --- GLOBAL DISPLAY STATE LOGIC ---
        all_states_str = "".join(str(v) for v in lanes_state_dict.values()).lower()
        if not all_states_str:
            all_states_str = "r"

        if any(c in all_states_str for c in ['y', 's']): 
            display_state = "YELLOW"
        elif any(c in all_states_str for c in ['g']): 
            display_state = "GREEN"
        else: 
            display_state = "RED"
            
        return {
            "lanes_state": lanes_state_dict,
            "display_state": display_state
        }