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

# File: src/mfd/mfd_zone_calculator.py
# Author: Gabriel Moraes
# Date: August 8, 2026

from typing import Dict, Any, List

class MFDZoneCalculator:
    """
    Responsibility: Calculate the distribution of time spent in MFD operational zones
    (Green: uncongested, Yellow: optimal capacity, Red: gridlock/congestion).
    """

    @staticmethod
    def calculate_zone_distribution(history: List[Dict[str, Any]], peak_accum: float) -> Dict[str, float]:
        """
        Compute percentage of simulation history spent in Green, Yellow, and Red MFD accumulation zones.

        :param history: List of historical network state dictionaries
        :param peak_accum: Critical accumulation threshold (N_crit)
        :return: Dict containing green_zone_pct, yellow_zone_pct, and red_zone_pct
        """
        if not history or peak_accum <= 0:
            return {
                "green_zone_pct": 33.3,
                "yellow_zone_pct": 33.3,
                "red_zone_pct": 33.4
            }

        green_count = 0
        yellow_count = 0
        red_count = 0
        total = len(history)

        ncrit = peak_accum if peak_accum > 0 else 500.0

        for pt in history:
            acc = pt.get("accumulation", 0.0)
            if acc < 0.7 * ncrit:
                green_count += 1
            elif acc <= 1.1 * ncrit:
                yellow_count += 1
            else:
                red_count += 1

        return {
            "green_zone_pct": round((green_count / total) * 100.0, 1),
            "yellow_zone_pct": round((yellow_count / total) * 100.0, 1),
            "red_zone_pct": round((red_count / total) * 100.0, 1)
        }
