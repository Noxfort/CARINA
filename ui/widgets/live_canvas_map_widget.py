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

# File: ui/widgets/live_canvas_map_widget.py
# Author: Gabriel Moraes
# Date: October 1, 2025

"""
Defines the LiveCanvasMapWidget.

Responsive version: uses expand=True to fill available space,
but calculates concrete dimensions for the Canvas upon mounting.
Automatically recalculates upon window resize.
"""

import flet as ft
import flet.canvas as cv
import logging
from typing import Dict, List, Any, Callable, Tuple, TYPE_CHECKING

from ui.builders.map_element_factory import MapElementFactory
from ui.interfaces.map_protocols import (
    InteractionHandlerProtocol,
    StreetInteractionHandlerProtocol,
    EventRouterProtocol,
    MapDrawerProtocol,
    MapStateManagerProtocol,
    MapAnimatorProtocol,
    MapViewportManagerProtocol,
    MapControlsAssemblerProtocol
)
from ui.handlers.locale_manager import LocaleManager
from ui.builders.map_components_factory import MapComponentsFactory

class LiveCanvasMapWidget(ft.Container):
    """
    A widget that orchestrates specialists to draw and animate a map.
    Responsive: fills available space and recalculates on resize.
    """
    def __init__(
        self,
        locale_manager: LocaleManager,
        on_semaphore_click: Callable[[str | None], None] = None,
        on_street_click: Callable[[str | None], None] = None,
        get_panel_state_callback: Callable[[], Dict] = None,
        on_panel_update_callback: Callable[[str, Dict, str, str], None] = None
    ):
        super().__init__(
            expand=True, bgcolor="#F7F7F7", border_radius=10,
            alignment=ft.alignment.center,
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )
        
        self.locale_manager = locale_manager
        self.get_panel_state_callback = get_panel_state_callback
        self.on_panel_update_callback = on_panel_update_callback
        
        # Initialize Layout and Controls Assembler specialists via factory
        self.viewport_manager: MapViewportManagerProtocol = MapComponentsFactory.create_viewport_manager()
        self.controls_assembler: MapControlsAssemblerProtocol = MapComponentsFactory.create_controls_assembler()
        
        self.interaction_handler: InteractionHandlerProtocol = MapComponentsFactory.create_interaction_handler(
            viewport_width=self.viewport_manager.width,
            viewport_height=self.viewport_manager.height,
            on_update=self._safe_update
        )
        self.last_mouse_x = self.viewport_manager.width / 2
        self.last_mouse_y = self.viewport_manager.height / 2
        
        self.street_interaction_handler: StreetInteractionHandlerProtocol = MapComponentsFactory.create_street_interaction_handler()
        
        # Use the decoupled Event Router
        self.event_router: EventRouterProtocol = MapComponentsFactory.create_event_router(
            interaction_handler=self.interaction_handler,
            street_interaction_handler=self.street_interaction_handler,
            on_update=self._safe_update,
            on_semaphore_click=on_semaphore_click,
            on_street_click=on_street_click
        )
        
        # Bind the street handler's callback to the event router
        self.street_interaction_handler.on_street_selected = self.event_router.handle_street_click

        
        self.drawer: MapDrawerProtocol | None = None
        self.animator: MapAnimatorProtocol | None = None
        self.map_state_manager: MapStateManagerProtocol | None = None
        
        # Pending map data (stored if initialize_map is called before mount)
        self._pending_map_data: Tuple | None = None
        self._is_map_built = False
        
        self.canvas = cv.Canvas(shapes=[], width=self.viewport_manager.width, height=self.viewport_manager.height)
        self.map_stack = ft.Stack(
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
        )
        
        def _on_hover(e: ft.HoverEvent):
            self.last_mouse_x = e.local_x
            self.last_mouse_y = e.local_y
 
        self.gesture_detector = ft.GestureDetector(
            content=self.map_stack,
            on_hover=_on_hover,
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=lambda e: self.interaction_handler.handle_zoom(e, self.last_mouse_x, self.last_mouse_y),
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_tap_down=self.event_router.handle_map_tap
        )
        
        self.content = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text(self.locale_manager.get_string("live_map.waiting_scenario", default="Waiting for Scenario Connection..."))
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        self.did_mount = self._on_mount
        self.will_unmount = self.on_unmount

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _on_mount(self):
        """Called when the widget is attached to the page. Hooks resize and processes pending data."""
        if self.page:
            original_on_resized = self.page.on_resized
            def _handle_resized(e):
                if original_on_resized and callable(original_on_resized):
                    original_on_resized(e)
            self.page.on_resized = _handle_resized
        
        if self._pending_map_data and not self._is_map_built:
            self._calculate_dimensions()
            self._build_map(self._pending_map_data)
            self._pending_map_data = None

    def _calculate_dimensions(self):
        """Calculates canvas dimensions from the current page size."""
        if self.page:
            self.viewport_manager.calculate_dimensions(self.page.width, self.page.height)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_translations(self, locale_manager: LocaleManager):
        self.locale_manager = locale_manager
        if isinstance(self.content, ft.Column) and len(self.content.controls) > 1:
            if isinstance(self.content.controls[1], ft.Text):
                self.content.controls[1].value = self.locale_manager.get_string("live_map.waiting_scenario", default="Waiting for Scenario Connection...")
        elif isinstance(self.content, ft.Text):
            if "ERROR" in self.content.value or "ERRO" in self.content.value:
                self.content.value = self.locale_manager.get_string("live_map.error_geometry", default="ERROR: Map geometry data was not provided.")
        if self.page: self.update()

    def initialize_map(self, map_data: Tuple | None):
        """
        Receives map geometry. If the widget is already mounted, builds immediately.
        Otherwise, stores data and defers to did_mount.
        """
        if not map_data:
            self.content = ft.Text(self.locale_manager.get_string("live_map.error_geometry", default="ERROR: Map geometry data was not provided."), color=ft.Colors.RED)
            if self.page: self.update()
            return

        if self.page:
            self._calculate_dimensions()
            self._build_map(map_data)
        else:
            self._pending_map_data = map_data
            logging.info("[LiveCanvasMap] Map data received before mount. Deferred.")

    def clear_all_selections(self):
        if self.map_state_manager:
            self.map_state_manager.set_selection(item_type=None, item_id=None)
            self._safe_update()

    def update_data(self, data_packet: dict):
        if self.animator:
            self.animator.update_data(data_packet)
    
    def on_unmount(self):
        if self.animator: self.animator.stop()

    def set_semaphore_override_state(self, semaphore_id: str, state: str):
        self.event_router.set_semaphore_override_state(semaphore_id, state)

    def set_street_override_state(self, street_id: str, state: str):
        self.event_router.set_street_override_state(street_id, state)

    # ------------------------------------------------------------------
    # Internal: Build / Rebuild
    # ------------------------------------------------------------------
    def _build_map(self, map_data: Tuple):
        """Builds (or rebuilds) the entire map canvas with current dimensions."""
        nodes, edges, _ = map_data
        
        self._pending_map_data = map_data
        
        if self.animator:
            self.animator.stop()

        self.canvas = cv.Canvas(shapes=[], width=self.viewport_manager.width, height=self.viewport_manager.height)
        
        self.interaction_handler.base_width = self.viewport_manager.width
        self.interaction_handler.base_height = self.viewport_manager.height
        
        self.drawer = MapComponentsFactory.create_drawer(nodes, edges)
        self.drawer.calculate_transformations(self.viewport_manager.width, self.viewport_manager.height)
        
        edge_paths = self.drawer.draw_initial_map(self.canvas, stroke_width=7.0)
        self.street_interaction_handler.load_paths(edge_paths)
        
        # Assemble canvas and interactive element controls
        stack_controls, interactive_widgets_map = self.controls_assembler.assemble_map_controls(
            drawer=self.drawer,
            canvas=self.canvas
        )
        
        self.map_stack.controls = stack_controls
        
        self.map_state_manager = MapComponentsFactory.create_state_manager(
            canvas=self.canvas,
            stack=self.map_stack,
            edge_paths=edge_paths,
            interactive_widgets=interactive_widgets_map
        )

        self.animator = MapComponentsFactory.create_animator(
            widget_to_update=self,
            get_panel_state_callback=self.get_panel_state_callback,
            on_panel_update_callback=self.on_panel_update_callback,
            edge_paths=edge_paths,
            interactive_widgets=interactive_widgets_map,
            topology_edges=edges
        )
        
        # Pass the managers back to the router
        self.event_router.attach_managers(self.map_state_manager, self.animator)
        
        self.animator.start()
        self._is_map_built = True
        
        self.content = self.gesture_detector
        if self.page: self.update()
        logging.info(f"[LiveCanvasMap] Map initialized ({self.viewport_manager.width}x{self.viewport_manager.height}).")

    def _safe_update(self):
        """Wrapper to call update only when mounted."""
        if self.page:
            try:
                self.update()
            except Exception:
                pass