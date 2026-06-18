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
import time
from typing import Dict, Any, Callable, Tuple, TYPE_CHECKING

from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.handlers.street_interaction_handler import StreetInteractionHandler
from ui.handlers.map_event_router import MapEventRouter
from ui.builders.map_builder import MapBuilder
from ui.managers.ui_config_manager import ui_config

# Prevents circular import by allowing type annotations
if TYPE_CHECKING:
    from ui.renderers.map_drawer import MapDrawer
    from ui.animators.map_animator import MapAnimator
    from ui.managers.map_state_manager import MapStateManager

_CONFIG = ui_config.get_section("live_map")

# Estimated pixels consumed by UI chrome (AppBar, Tabs, padding, ControlPanel)
_CHROME_WIDTH_OFFSET = _CONFIG["chrome_width_offset"]
_CHROME_HEIGHT_OFFSET = _CONFIG["chrome_height_offset"]

class LiveCanvasMapWidget(ft.Container):
    """
    A widget that orchestrates specialists to draw and animate a map.
    Responsive: fills available space and recalculates on resize.
    """
    def __init__(
        self,
        on_semaphore_click: Callable[[str | None], None] = None,
        on_street_click: Callable[[str | None], None] = None,
        get_panel_state_callback: Callable[[], Dict] = None,
        on_panel_update_callback: Callable[[str, Dict, str, str], None] = None
    ):
        super().__init__(
            expand=True, bgcolor=_CONFIG["bgcolor"], border_radius=_CONFIG["border_radius"],
            alignment=ft.alignment.center,
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )
        
        self.get_panel_state_callback = get_panel_state_callback
        self.on_panel_update_callback = on_panel_update_callback
        
        # Current effective dimensions (calculated on mount / resize)
        self._canvas_width: int = _CONFIG["initial_canvas_width"]
        self._canvas_height: int = _CONFIG["initial_canvas_height"]
        
        self.interaction_handler = MapInteractionHandler(
            base_width=self._canvas_width, 
            base_height=self._canvas_height, 
            on_update_callback=self._safe_update
        )
        self.last_mouse_x = self._canvas_width / 2
        self.last_mouse_y = self._canvas_height / 2
        
        self.street_interaction_handler = StreetInteractionHandler(on_street_selected=None)
        
        # Use the newly decoupled Event Router
        self.event_router = MapEventRouter(
            interaction_handler=self.interaction_handler,
            street_interaction_handler=self.street_interaction_handler,
            safe_update_callback=self._safe_update,
            on_semaphore_click=on_semaphore_click,
            on_street_click=on_street_click
        )
        # Bind the street handler's callback to the event router
        self.street_interaction_handler.on_street_selected = self.event_router.handle_street_click
        
        self.drawer: MapDrawer | None = None
        self.animator: MapAnimator | None = None
        self.map_state_manager: MapStateManager | None = None
        
        # Pending map data (stored if initialize_map is called before mount)
        self._pending_map_data: Tuple | None = None
        self._is_map_built = False
        
        self.canvas = cv.Canvas(shapes=[], width=self._canvas_width, height=self._canvas_height)
        self.map_stack = ft.Stack(
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
        )
        
        def _on_hover(e: ft.HoverEvent):
            self.last_mouse_x = e.local_x
            self.last_mouse_y = e.local_y
 
        self._last_right_click_time = 0.0
        threshold = _CONFIG.get("double_click_time_threshold", 0.3)
        def _on_secondary_tap_down(e):
            current_time = time.time()
            if current_time - self._last_right_click_time < threshold:
                self.interaction_handler.center_and_reset_zoom()
            self._last_right_click_time = current_time

        self.gesture_detector = ft.GestureDetector(
            content=self.map_stack,
            on_hover=_on_hover,
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=lambda e: self.interaction_handler.handle_zoom(e, self.last_mouse_x, self.last_mouse_y),
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_secondary_tap_down=_on_secondary_tap_down,
            on_tap_down=self.event_router.handle_map_tap
        )
        
        self.content = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text("Waiting for Scenario Connection...")
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
            pw = self.page.width or 1280
            ph = self.page.height or 800
            self._canvas_width = max(int(pw - _CHROME_WIDTH_OFFSET), 400)
            self._canvas_height = max(int(ph - _CHROME_HEIGHT_OFFSET), 300)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def initialize_map(self, map_data: Tuple | None, net_file_path: str | None = None):
        """
        Receives map geometry. If the widget is already mounted, builds immediately.
        Otherwise, stores data and defers to did_mount.
        """
        if not map_data:
            self.content = ft.Text("ERROR: Map geometry data was not provided.", color=ft.Colors.RED)
            if self.page: self.update()
            return

        # Start background check/download for realistic background map
        if net_file_path:
            import threading
            threading.Thread(
                target=self._check_and_generate_background,
                args=(net_file_path, map_data),
                daemon=True
            ).start()

        if self.page:
            self._calculate_dimensions()
            self._build_map(map_data)
        else:
            self._pending_map_data = map_data
            logging.info("[LiveCanvasMap] Map data received before mount. Deferred.")

    def _check_and_generate_background(self, net_file_path: str, map_data: Tuple):
        try:
            import os
            import json
            from ui.loader.map_tile_downloader import generate_background_map
            
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            bg_path = os.path.join(project_root, "ui", "assets", "images", "osm_background.png")
            meta_path = bg_path + ".json"
            
            # Check if bounds match map_data bounds
            nodes, edges, bounds = map_data
            
            # Get current map bounds
            if isinstance(bounds, dict) and "min_x" in bounds:
                curr_min_x = bounds["min_x"]
                curr_max_x = bounds["max_x"]
                curr_min_y = bounds["min_y"]
                curr_max_y = bounds["max_y"]
            elif isinstance(bounds, dict) and "x_min" in bounds:
                curr_min_x = bounds["x_min"]
                curr_max_x = bounds["x_max"]
                curr_min_y = bounds["y_min"]
                curr_max_y = bounds["y_max"]
            else:
                # bounds is lane_to_edge_map, we compute bounds from nodes
                xs = [n["x"] for n in nodes.values()]
                ys = [n["y"] for n in nodes.values()]
                curr_min_x = min(xs) if xs else 0.0
                curr_max_x = max(xs) if xs else 1000.0
                curr_min_y = min(ys) if ys else 0.0
                curr_max_y = max(ys) if ys else 1000.0

            need_download = True
            if os.path.exists(bg_path) and os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    # Allow 10.0 units threshold
                    if (abs(meta["x_min"] - curr_min_x) < 10.0 and
                        abs(meta["x_max"] - curr_max_x) < 10.0 and
                        abs(meta["y_min"] - curr_min_y) < 10.0 and
                        abs(meta["y_max"] - curr_max_y) < 10.0):
                        need_download = False
                        logging.info("[LiveCanvasMap] Background map cache matches current scenario bounds. Reusing.")
                except Exception as e:
                    logging.warning(f"[LiveCanvasMap] Error reading cached background metadata: {e}")
            
            if need_download:
                logging.info(f"[LiveCanvasMap] Generating new background map for net: {net_file_path}")
                meta = generate_background_map(net_file_path, bg_path)
                if meta:
                    logging.info("[LiveCanvasMap] Background map generated successfully.")
                    if self.page:
                        self._build_map(map_data)
                else:
                    logging.warning("[LiveCanvasMap] Failed to generate background map.")
        except Exception as e:
            logging.error(f"[LiveCanvasMap] Error in background map check/generation thread: {e}", exc_info=True)

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
        """Builds (or rebuilds) the entire map canvas with current dimensions using MapBuilder."""
        if self.animator:
            self.animator.stop()
        
        self._pending_map_data = map_data
        self.interaction_handler.base_width = self._canvas_width
        self.interaction_handler.base_height = self._canvas_height

        canvas, drawer, edge_paths, map_state_manager, animator = MapBuilder.build(
            map_data=map_data,
            canvas_width=self._canvas_width,
            canvas_height=self._canvas_height,
            map_stack=self.map_stack,
            widget_to_update=self,
            get_panel_state_callback=self.get_panel_state_callback,
            on_panel_update_callback=self.on_panel_update_callback
        )

        self.canvas = canvas
        self.drawer = drawer
        self.street_interaction_handler.load_paths(edge_paths)
        self.map_state_manager = map_state_manager
        self.animator = animator
        
        # Pass the managers back to the router
        self.event_router.attach_managers(self.map_state_manager, self.animator)
        
        self.animator.start()
        self._is_map_built = True
        
        self.content = self.gesture_detector
        if self.page: self.update()
        logging.info(f"[LiveCanvasMap] Map initialized ({self._canvas_width}x{self._canvas_height}).")

    def _safe_update(self):
        """Wrapper to call update only when mounted."""
        if self.page:
            try:
                self.update()
            except Exception:
                pass