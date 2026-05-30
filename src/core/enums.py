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

# File: src/core/enums.py (NEW FILE)
# Author: Gabriel Moraes
# Date: October 2, 2025

"""
Defines shared enumerations (Enums) for the system core.

This file was created to resolve a circular dependency, isolating
the 'Maturity' Enum definition in a simple, dependency-free module.
"""

from enum import Enum, auto

class Maturity(Enum):
    """Defines an agent's maturity phases."""
    CHILD = auto()
    TEEN = auto()
    ADULT = auto()