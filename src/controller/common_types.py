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

# File: src/controller/common_types.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Common Types
------------
Shared type definitions for the controller modules to avoid circular imports.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List


class SignalState(Enum):
    """NEMA-compliant signal states for a phase transition."""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ALL_RED = "ALL_RED"


@dataclass
class StageDefinition:
    """
    A single signal phase extracted from the SUMO TLS program.
    
    Attributes:
        state_string: Raw SUMO state (e.g., "GGrrrrGGrrrr") defining which
                      signal links are green/red in this phase.
        yellow_string: Derived state where all G/g are replaced with 'y'.
        all_red_string: All characters set to 'r' for clearance interval.
    """
    state_string: str
    yellow_string: str
    all_red_string: str