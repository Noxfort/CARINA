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

# File: src/controller/stage_derivator.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Stage Derivator
---------------
Utility functions for deriving yellow and all-red states from green states.
"""


def derive_yellow_state(green_state: str) -> str:
    """
    Derive the yellow transition state from a green state.
    Replace all G/g with 'y', keep 'r' as 'r'.
    
    Args:
        green_state: The green state string
        
    Returns:
        The derived yellow state string
    """
    return ''.join('y' if c in ('G', 'g') else 'r' for c in green_state)