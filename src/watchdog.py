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

# File: src/watchdog.py
# Author: Gabriel Moraes
# Date: 2026-06-11

"""
Watchdog Orchestrator / Facade
------------------------------
This file acts as a facade, re-exporting the Watchdog components 
from the new `watchdog` package to maintain backward compatibility
with the rest of the CARINA codebase.
"""

from watchdog.watchdog_logic import Watchdog
from watchdog.watchdog_process import run_watchdog

__all__ = ["Watchdog", "run_watchdog"]