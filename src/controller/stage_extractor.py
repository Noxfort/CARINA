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

# File: src/controller/stage_extractor.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Stage Extractor
---------------
Utility functions for extracting green stages from SUMO traffic light programs.
"""


def extract_green_stages(tls_id: str, original_stages: list, green_chars: frozenset) -> list:
    """
    From the full SUMO stage list, extract all stages (no filtering).
    
    Args:
        tls_id: The ID of the traffic light system
        original_stages: List of original SUMO stages
        green_chars: Set of characters considered as green signals
        
    Returns:
        List of stage state strings
    """
    return [stage.state for stage in original_stages]