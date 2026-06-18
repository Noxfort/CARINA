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

# File: ui/renderers/heatmap_color_resolver.py
# Author: Gabriel Moraes
# Date: June 13, 2026

class HeatmapColorResolver:
    """
    Responsible for converting numeric congestion values into colors (Heatmap Gradients).
    Isolated to maintain the Single Responsibility Principle (SRP).
    """

    @staticmethod
    def get_color_for_congestion(value: float, max_expected_value: float = 100.0) -> str:
        """
        Converts a congestion value into a color for the map's heatmap.
        Uses a smooth, multi-point gradient to avoid abrupt transitions.
        """
        # Normalize the value between 0 and 1
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        
        # Anchor colors for a very smooth and organic transition:
        # 0%   - Pure Green (Free-flowing traffic)
        # 33%  - Lime/Yellow-Green (Beginning of accumulation)
        # 66%  - Orange (Heavy/Slow traffic)
        # 100% - Dark Red Waze-style (Traffic Jam/Congestion)
        stops = [
            (0.00, (0, 255, 0)),      # Vibrant Green
            (0.25, (255, 255, 0)),    # Vibrant Yellow
            (0.50, (255, 140, 0)),    # Vibrant Orange
            (0.75, (255, 0, 0)),      # Vibrant Red
            (1.00, (139, 0, 0))       # Dark Red (Waze style)
        ]
        
        # If exactly 1.0 (or more due to margin of error)
        if normalized >= 1.0:
            return "#8b0000"
            
        # Smooth interpolation within segments
        for i in range(len(stops) - 1):
            t1, c1 = stops[i]
            t2, c2 = stops[i+1]
            if t1 <= normalized < t2:
                factor = (normalized - t1) / (t2 - t1)
                
                r = int(c1[0] + (c2[0] - c1[0]) * factor)
                g = int(c1[1] + (c2[1] - c1[1]) * factor)
                b = int(c1[2] + (c2[2] - c1[2]) * factor)
                return f"#{r:02x}{g:02x}{b:02x}"
                
        return "#8b0000" # Safety fallback
