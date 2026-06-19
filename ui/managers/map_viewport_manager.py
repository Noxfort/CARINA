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

# File: ui/managers/map_viewport_manager.py
# Author: Gabriel Moraes
# Date: October 1, 2025

from typing import Tuple

class MapViewportManager:
    """
    Manages layout dimensions and chrome offsets for the Map Viewport.
    """
    def __init__(self, chrome_width_offset: int = 420, chrome_height_offset: int = 160):
        self.chrome_width_offset = chrome_width_offset
        self.chrome_height_offset = chrome_height_offset
        self.width: int = 1280
        self.height: int = 720

    def calculate_dimensions(self, page_width: float | None, page_height: float | None) -> Tuple[int, int]:
        """Calculates canvas dimensions from the current page size."""
        pw = page_width or 1280
        ph = page_height or 800
        self.width = max(int(pw - self.chrome_width_offset), 400)
        self.height = max(int(ph - self.chrome_height_offset), 300)
        return self.width, self.height
