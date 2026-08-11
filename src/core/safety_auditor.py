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

# File: src/core/safety_auditor.py
# Author: Gabriel Moraes
# Date: April 15, 2026

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.guardian_agent import GuardianAgent
    from engine.environment import SumoEnvironment

class SafetyAuditor:
    """
    Applies Neuro-Symbolic vetoes via the Guardian Agent.
    """

    def __init__(self, guardian_agent: 'GuardianAgent'):
        self.guardian = guardian_agent

    def audit(self, suggested_action: int, tl_id: str, augmented_state: list, environment: 'SumoEnvironment', latest_veto_map: dict = None) -> tuple:
        """
        Audits a 'CHANGE PHASE' request using the Guardian logic.
        Returns: (final_action, was_vetoed)
        """
        if suggested_action != 0:
            return suggested_action, False

        extractor = environment.state_extractor
        
        sim_time = 0.0
        current_stage_idx = 0
        if environment.conn:
            try:
                sim_time = environment.conn.simulation.getTime()
                current_stage_idx = environment.conn.trafficlight.getPhase(tl_id)
            except Exception:
                pass
                
        current_stage_duration = 0.0
        if environment.action_supervisor:
            current_stage_duration = sim_time - environment.action_supervisor._last_stage_change_time.get(tl_id, 0.0)
            
        stage_codes = extractor.tl_stage_codes.get(tl_id, {})
        state_string = stage_codes.get(current_stage_idx, "G")
        
        # Improve context with more accurate information
        total_stages = len(stage_codes)
        prev_stage_idx = (current_stage_idx - 1) % total_stages if total_stages > 0 else 0
        prev_state_string = stage_codes.get(prev_stage_idx, "").upper()
        
        stage_durations = getattr(extractor, 'tl_stage_durations', {}).get(tl_id, {})
        default_duration = stage_durations.get(current_stage_idx, 0.0)
        from utils.safety_rules import SafetyRules
        all_red_time = SafetyRules.get_all_red()
        if default_duration > 0:
            is_clearance_red = ('Y' in prev_state_string) and (default_duration <= all_red_time)
        else:
            is_clearance_red = 'Y' in prev_state_string

        context = {
            'tl_id': tl_id,
            'current_stage_duration': current_stage_duration,
            'current_stage_state': state_string.upper(),
            'next_stage_has_flow': True,
            'is_clearance_red': is_clearance_red
        }
        
        # 1. Immediate Symbolic Audit
        if self.guardian:
            symbolic_action, reason = self.guardian.symbolic_audit(context)
            if symbolic_action == 0: # Vetoed by symbolic rules
                return 1, True

        # 2. Zero-Latency Neural Spillback Audit (from Background Veto Map)
        if latest_veto_map and tl_id in latest_veto_map:
            risk_score = latest_veto_map[tl_id]
            # If risk is extremely high, veto the change
            if risk_score > 0.8: # Threshold can be tuned
                return 1, True
            
        return suggested_action, False
