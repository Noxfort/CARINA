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

# File: ui/router/map_event_router.py
# Author: Gabriel Moraes
# Date: June 13, 2026

"""
Defines the MapEventRouter.

This router handles all incoming user events (clicks, taps, overrides) and
delegates them to the appropriate managers (StateManager, Animator), 
resolving the SRP violation in the main widget.
"""

import flet as ft
from typing import Callable, Optional

class MapEventRouter:
    """
    Handles event routing for the map widget.
    It takes raw user interactions and routes them to the appropriate managers
    or external callbacks.
    """
    def __init__(
        self,
        interaction_handler,
        street_interaction_handler,
        safe_update_callback: Callable[[], None],
        on_semaphore_click: Callable[[Optional[str]], None] = None,
        on_street_click: Callable[[Optional[str]], None] = None
    ):
        self.interaction_handler = interaction_handler
        self.street_interaction_handler = street_interaction_handler
        self.safe_update_callback = safe_update_callback
        self.on_semaphore_click = on_semaphore_click
        self.on_street_click = on_street_click
        
        self.state_manager = None
        self.animator = None

    def attach_managers(self, state_manager, animator):
        """Attaches the dynamically built managers to the router."""
        self.state_manager = state_manager
        self.animator = animator

    def handle_map_tap(self, e: ft.TapEvent):
        """Converts tap coordinates and routes the click to elements."""
        map_x, map_y = self.interaction_handler.get_map_coordinates(e.local_x, e.local_y)

        # Delegate hit detection to the State Manager
        if self.state_manager:
            hit_id = self.state_manager.check_widget_hit(map_x, map_y)
            if hit_id:
                self.handle_interactive_click(hit_id)
                return

        # Try clicking a street
        scale = self.interaction_handler.scale.scale
        self.street_interaction_handler.handle_click(map_x, map_y, scale)

    def handle_interactive_click(self, widget_id: str):
        if not self.state_manager: return
        current_selection = self.state_manager.selected_interactive_id
        new_selection_id = widget_id if current_selection != widget_id else None
        
        self.state_manager.set_selection(item_type='interactive', item_id=new_selection_id)
        self.safe_update_callback()
        
        if self.on_semaphore_click: 
            self.on_semaphore_click(new_selection_id)

    def handle_street_click(self, edge_id: Optional[str]):
        if self.state_manager:
            self.state_manager.set_selection(item_type='street', item_id=edge_id)
            self.safe_update_callback()
        if self.on_street_click: 
            self.on_street_click(edge_id)

    def set_semaphore_override_state(self, semaphore_id: str, state: str):
        if self.state_manager and self.animator:
            widget = self.state_manager.interactive_widgets.get(semaphore_id)
            if widget:
                command = {"type": "semaphore", "id": semaphore_id, "state": state}
                self.animator.command_queue.put(command)

    def set_street_override_state(self, street_id: str, state: str):
        if self.animator:
            command = {"type": "street", "id": street_id, "state": state}
            self.animator.command_queue.put(command)
