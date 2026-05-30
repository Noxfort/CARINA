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

# File: src/controller/phase_extractor.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Phase Extractor
---------------
Utility functions for extracting green phases from SUMO traffic light programs.
"""


def extract_green_phases(tls_id: str, original_phases: list, green_chars: frozenset) -> list:
    """
    From the full SUMO phase list, extract only the 'green' phases.
    
    SUMO TLS programs often include explicit yellow and all-red phases.
    We only need the green phases — we'll apply our own timing for
    yellow and all-red transitions.
    
    A phase is considered "green" if it has more green signals than
    yellow signals (to distinguish from transitional yellow phases).
    
    Args:
        tls_id: The ID of the traffic light system
        original_phases: List of original SUMO phases
        green_chars: Set of characters considered as green signals
        
    Returns:
        List of green phase state strings
    """
    green_phases = []
    for phase in original_phases:
        state = phase.state
        green_count = sum(1 for c in state if c in green_chars)
        yellow_count = sum(1 for c in state if c == 'y')

        # A genuine green phase has actual green movements
        if green_count > 0 and green_count >= yellow_count:
            green_phases.append(state)

    return green_phases