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

# File: ui/managers/map_state_manager.py
# Author: Gabriel Moraes
# Date: September 24, 2025

"""
Defines the MapStateManager.

This expert class is responsible for managing all the visual state
of the map, including selection and highlighting of streets and traffic lights.
It directly manipulates canvas and stack objects to reflect the current state.
"""

import flet as ft
import flet.canvas as cv
from typing import Dict

class MapStateManager:
    """
    Manages the visual state (selection/highlights) of the map.
    """
    def __init__(
        self,
        canvas: cv.Canvas,
        stack: ft.Stack,
        edge_paths: Dict[str, cv.Path],
        interactive_widgets: Dict[str, ft.Container]
    ):
        """
        Initializes the state manager.

        Args:
            canvas: Reference to the map's Canvas object.
            stack: Reference to the map's main Stack object.
            edge_paths: Dictionary of street Path objects.
            interactive_widgets: Dictionary of interactive widgets (e.g., traffic lights).
        """
        self.canvas = canvas
        self.stack = stack
        self.edge_paths = edge_paths
        self.interactive_widgets = interactive_widgets

        # --- Internal state of selection ---
        self.selected_edge_id: str | None = None
        self.selected_interactive_id: str | None = None
        
        # --- References to featured widgets ---
        self.highlight_casing: cv.Path | None = None
        self.highlight_foreground: cv.Path | None = None
        self.highlight_aura: ft.Container | None = None

    def check_widget_hit(self, x: float, y: float) -> str | None:
        """
        Checks if a given coordinate hits any of the registered interactive widgets.
        Returns the ID of the widget if hit, otherwise None.
        """
        for widget_id, widget in self.interactive_widgets.items():
            left, top = widget.left, widget.top
            right, bottom = left + widget.width, top + widget.height
            if left <= x <= right and top <= y <= bottom:
                return widget_id
        return None

    def set_selection(self, item_type: str | None, item_id: str | None):
        """
        Main method to set the selected item on the map.
        """
        self._clear_all_highlights()

        if item_type == 'street' and item_id:
            self._highlight_street(item_id)
            self.selected_edge_id = item_id
        elif item_type == 'interactive' and item_id:
            self._highlight_interactive(item_id)
            self.selected_interactive_id = item_id
    
    def _clear_all_highlights(self):
        """Clears all visual highlights from the map."""
        self._unhighlight_street()
        self._unhighlight_interactive()

    def _unhighlight_street(self):
        if self.highlight_casing in self.canvas.shapes:
            self.canvas.shapes.remove(self.highlight_casing)
        if self.highlight_foreground in self.canvas.shapes:
            self.canvas.shapes.remove(self.highlight_foreground)
        self.highlight_casing = None
        self.highlight_foreground = None
        self.selected_edge_id = None

    def _highlight_street(self, edge_id: str):
        path_object = self.edge_paths.get(edge_id)
        if not path_object: return

        self.highlight_casing = cv.Path(
            elements=path_object.elements,
            paint=ft.Paint(stroke_width=path_object.paint.stroke_width + 5, color=ft.Colors.BLACK, style=ft.PaintingStyle.STROKE, stroke_cap=ft.StrokeCap.ROUND)
        )
        self.highlight_foreground = cv.Path(
            elements=path_object.elements,
            paint=ft.Paint(stroke_width=path_object.paint.stroke_width + 1, color=ft.Colors.YELLOW_ACCENT_400, style=ft.PaintingStyle.STROKE, stroke_cap=ft.StrokeCap.ROUND)
        )
        self.canvas.shapes.append(self.highlight_casing)
        self.canvas.shapes.append(self.highlight_foreground)

    def _unhighlight_interactive(self):
        if self.highlight_aura and self.highlight_aura in self.stack.controls:
            self.stack.controls.remove(self.highlight_aura)
        self.highlight_aura = None
        self.selected_interactive_id = None

    def _highlight_interactive(self, widget_id: str):
        widget = self.interactive_widgets.get(widget_id)
        if not widget: return

        self.highlight_aura = ft.Container(
            width=widget.width + 8, height=widget.height + 8,
            left=widget.left - 4, top=widget.top - 4,
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.YELLOW_ACCENT_400),
            border_radius=8, animate=ft.Animation(100, "easeOut"),
        )
        
        # Inserts the aura in the correct layer (behind the interactive widgets)
        self.stack.controls.insert(1, self.highlight_aura)