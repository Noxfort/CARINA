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
        Enforces a 2-stage transition (Yellow followed by All-Red) when a phase change occurs.
        """
        lanes_state_dict = {}
        
        if not incoming_edges:
            lanes_state_dict["Unknown_Edge"] = "r"
            return {"lanes_state": lanes_state_dict, "display_state": "RED"}

        current_time = time.time()
        
        # Load rules from central location
        cls._yellow_duration_seconds = SafetyRules.get_yellow()
        cls._all_red_duration_seconds = SafetyRules.get_all_red()

        # Initialize the baseline phase if it's the first time seeing this traffic light
        if tl_id not in cls._current_display_phases:
            cls._current_display_phases[tl_id] = phase_idx

        last_phase = cls._current_display_phases[tl_id]

        # Phase jump detected from telemetry! Start the 2-stage visual transition.
        if phase_idx != last_phase and tl_id not in cls._transition_timers:
            cls._transition_timers[tl_id] = {
                'target_phase': phase_idx,
                'yellow_until': current_time + cls._yellow_duration_seconds,
                'all_red_until': current_time + cls._yellow_duration_seconds + cls._all_red_duration_seconds,
                'old_phase': last_phase
            }

        extracted_colors = {}

        # Handle Visual Transition Window
        if tl_id in cls._transition_timers:
            timer = cls._transition_timers[tl_id]
            
            old_colors = TlsMapExtractor.get_edge_colors_for_phase(tl_id, timer['old_phase'])
            new_colors = TlsMapExtractor.get_edge_colors_for_phase(tl_id, timer['target_phase'])

            if current_time < timer['yellow_until']:
                # --- STAGE 1: YELLOW WARNING ---
                for edge in incoming_edges:
                    old_c = old_colors.get(edge, 'r')
                    new_c = new_colors.get(edge, 'r')
                    
                    if old_c == 'G' and new_c == 'r':
                        extracted_colors[edge] = 'y' # Closing movement gets Yellow
                    elif old_c == 'G' and new_c == 'G':
                        extracted_colors[edge] = 'G' # Continuing movement stays Green
                    else:
                        extracted_colors[edge] = 'r' # Opening movement waits in Red

            elif current_time < timer['all_red_until']:
                # --- STAGE 2: ALL-RED CLEARANCE ---
                for edge in incoming_edges:
                    old_c = old_colors.get(edge, 'r')
                    new_c = new_colors.get(edge, 'r')
                    
                    if old_c == 'G' and new_c == 'G':
                        extracted_colors[edge] = 'G' # Only pure continuous movements stay Green
                    else:
                        extracted_colors[edge] = 'r' # Everything else is strictly Red for safety

            else:
                # --- TRANSITION COMPLETED ---
                cls._current_display_phases[tl_id] = timer['target_phase']
                del cls._transition_timers[tl_id]
                extracted_colors = TlsMapExtractor.get_edge_colors_for_phase(tl_id, cls._current_display_phases[tl_id])
        else:
            # Normal steady state (No active transition)
            extracted_colors = TlsMapExtractor.get_edge_colors_for_phase(tl_id, phase_idx)

        # Map the resolved colors to the incoming edges
        for edge_id in incoming_edges:
            lanes_state_dict[edge_id] = extracted_colors.get(edge_id, 'r')
            
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