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
        context = {
            'current_phase_duration': extractor.get_phase_duration(tl_id),
            'next_phase_has_flow': extractor.check_flow_on_next_phase(tl_id)
        }
        
        # 1. Immediate Symbolic Audit
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
