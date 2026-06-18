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

# File: ui/handlers/map_interaction_handler.py
# Author: Gabriel Moraes
# Date: September 24, 2025

"""
Defines the MapInteractionHandler.

This handler manages the state and logic of pan and zoom interactions on the map.
It calculates scale and offsets based on user inputs.
"""

import flet as ft

class MapInteractionHandler:
    """Manages the state and logic of map pan and zoom interactions."""

    def __init__(self, base_width: float, base_height: float, on_update_callback):
        """
        Initializes the interaction handler.
        """
        self.base_width = base_width
        self.base_height = base_height
        
        # Classes are called directly from 'ft'
        self.offset = ft.Offset(0, 0)
        self.scale = ft.Scale(scale=1.0, alignment=ft.alignment.center)

        # --- Behavior Settings ---
        self.max_zoom = 3.0
        self.min_zoom = 0.5
        
        self.on_update = on_update_callback

    def center_and_reset_zoom(self):
        """Resets the state to the initial view."""
        self.scale.scale = 1.0
        self.offset.x = 0.0
        self.offset.y = 0.0
        self.on_update()

    def handle_pan_update(self, e: ft.DragUpdateEvent):
        """Calculates the new map offset during a pan event."""
        effective_scale = self.scale.scale if self.scale.scale > 0 else 1.0
        
        # Exact vector anchoring maintaining absolute mouse grip under any zoom (1:1 Tracking)
        self.offset.x += e.delta_x / (self.base_width * effective_scale)
        self.offset.y += e.delta_y / (self.base_height * effective_scale)
        
        self.on_update()

    def handle_zoom(self, e: ft.ScrollEvent, mouse_x: float = None, mouse_y: float = None):
        """Calculates the new map scale and aligns the Vector Offset (Zoom to Pointer)."""
        old_scale = self.scale.scale
        
        if mouse_x is None: mouse_x = self.base_width / 2.0
        if mouse_y is None: mouse_y = self.base_height / 2.0
        
        if e.scroll_delta_y < 0:
            new_scale = min(self.max_zoom, old_scale * 1.1)
        else:
            new_scale = max(self.min_zoom, old_scale * 0.9)
            
        if new_scale == old_scale:
            return
            
        self.scale.scale = new_scale
        
        # True Zoom Math (Pointer Anchoring)
        # Flet Scale with alignment=center grows in both directions from the center.
        # Translates the offset to compensate for the visual directional magnitude of the mouse.
        center_x = self.base_width / 2.0
        center_y = self.base_height / 2.0
        
        dx = mouse_x - center_x
        dy = mouse_y - center_y
        
        # The true offset logic compensates for the scale difference relative to the center
        self.offset.x -= (dx * (new_scale - old_scale)) / (self.base_width * new_scale)
        self.offset.y -= (dy * (new_scale - old_scale)) / (self.base_height * new_scale)

        self.on_update()

    def get_map_coordinates(self, local_x: float, local_y: float) -> tuple[float, float]:
        """
        Converts raw screen pixel coordinates into map-space coordinates 
        based on current zoom and pan.
        """
        scale = self.scale.scale
        offset = self.offset
        center_x, center_y = self.base_width / 2, self.base_height / 2
        
        offset_x_px = offset.x * self.base_width
        offset_y_px = offset.y * self.base_height
        
        unpanned_x = local_x - offset_x_px
        unpanned_y = local_y - offset_y_px
        
        map_space_x = ((unpanned_x - center_x) / scale) + center_x
        map_space_y = ((unpanned_y - center_y) / scale) + center_y
        
        return map_space_x, map_space_y