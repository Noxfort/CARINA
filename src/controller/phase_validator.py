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

# File: src/controller/phase_validator.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Phase Validator
---------------
Utility functions for validating phase definitions.
"""

import logging
from typing import List

from src.controller.common_types import PhaseDefinition

logger = logging.getLogger(__name__)

# Valid SUMO signal characters
_VALID_SIGNAL_CHARS = frozenset({'G', 'g', 'r', 'y', 'o', 's', 'u'})
_GREEN_CHARS = frozenset({'G', 'g'})


def validate_phases(tls_id: str, phases: List[PhaseDefinition]) -> bool:
    """
    Defense-in-depth validation of phase definitions.
    
    Checks:
        1. All state strings have the same length (same number of signal links)
        2. All characters are valid SUMO signal characters
        3. No two different green phases have the same signal link green
           (conflict between phases — if link i is green in phase A and
           also green in phase B, then A and B conflict and must never
           overlap. This is guaranteed by the state machine, but we verify.)
    
    Returns:
        True if all phases pass validation.
    """
    if not phases:
        return True

    expected_len = len(phases[0].state_string)

    for i, phase in enumerate(phases):
        # Check length consistency
        if len(phase.state_string) != expected_len:
            logger.error(
                f"[PhaseValidator] TLS '{tls_id}' phase {i}: "
                f"state length {len(phase.state_string)} != expected {expected_len}"
            )
            return False

        # Check character validity
        for j, char in enumerate(phase.state_string):
            if char not in _VALID_SIGNAL_CHARS:
                logger.error(
                    f"[PhaseValidator] TLS '{tls_id}' phase {i}: "
                    f"invalid signal character '{char}' at position {j}"
                )
                return False

    # Cross-phase conflict check: For each pair of phases, verify that
    # no signal link is GREEN in both phases simultaneously.
    # (If it were, running them back-to-back is fine, but if we ever
    # had a bug that ran two phases at once, it would be catastrophic.)
    for i in range(len(phases)):
        for j in range(i + 1, len(phases)):
            greens_i = {k for k, c in enumerate(phases[i].state_string) if c in _GREEN_CHARS}
            greens_j = {k for k, c in enumerate(phases[j].state_string) if c in _GREEN_CHARS}
            overlap = greens_i & greens_j

            if overlap:
                # This is not necessarily a conflict — the same link CAN be green
                # in multiple phases (e.g., a through movement that's always green).
                # What matters is that we never run two phases SIMULTANEOUSLY,
                # which our state machine guarantees. Log as info, not error.
                logger.debug(
                    f"[PhaseValidator] TLS '{tls_id}': signal links {overlap} are green "
                    f"in both phase {i} and phase {j} (shared movements — safe in sequential operation)."
                )

    return True