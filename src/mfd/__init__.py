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

# File: src/engine/mfd/__init__.py

"""
MFD (Macroscopic Fundamental Diagram) Package.

Network-level traffic performance evaluation based on
Geroliminis & Daganzo (2008) theory.
"""

from mfd.mfd import MacroscopicFundamentalDiagram
from mfd.snapshot import MFDSnapshot

__all__ = ['MacroscopicFundamentalDiagram', 'MFDSnapshot']
