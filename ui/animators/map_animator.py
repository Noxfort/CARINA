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

# File: ui/animators/map_animator.py
# Author: Gabriel Moraes
# Date: October 1, 2025

"""
Defines the MapAnimator class.

In this version, it is responsible for orchestrating the high-frequency visual
updates of all interactive elements (map and details panel) within its
controlled loop, to avoid overwhelming the UI thread.
"""

import flet as ft
import flet.canvas as cv
import logging
import threading
import time
import queue
from typing import Dict, Any, Callable, List

from ui.renderers.heatmap_color_resolver import HeatmapColorResolver
from ui.managers.override_state_manager import OverrideStateManager

class MapAnimator:
    """
    Manages a background thread to apply high-frequency visual updates.
    Now adheres strictly to SRP and OCP.
    """
    def __init__(
        self,
        widget_to_update: ft.Control,
        get_panel_state_callback: Callable[[], Dict] = None,
        on_panel_update_callback: Callable[[str, Dict, str, str], None] = None,
        edge_paths: Dict[str, cv.Path] = None,
        semaforo_widgets: Dict[str, Any] = None,
        interval: float = 0.5,
        topology_edges: List[Dict] = None
    ):
        self.widget = widget_to_update
        self.get_panel_state_callback = get_panel_state_callback
        self.on_panel_update_callback = on_panel_update_callback
        self.edge_paths = edge_paths or {}
        
        # OCP: We treat this as a generic list of interactive elements
        self.interactive_widgets = semaforo_widgets or {}
        
        self.interval = interval
        
        # Build topological groupings for streets that share the same intersections
        self.topology_edges = topology_edges or []
        self.edge_group_map = {}
        topology_groups = {}
        
        for edge_data in self.topology_edges:
            from_n = edge_data.get('from')
            to_n = edge_data.get('to')
            if from_n and to_n:
                group_key = tuple(sorted([from_n, to_n]))
                if group_key not in topology_groups:
                    topology_groups[group_key] = []
                topology_groups[group_key].append(edge_data['id'])
                
        for group, ids in topology_groups.items():
            for eid in ids:
                self.edge_group_map[eid] = ids
        
        self.thread = None
        self.is_running = False
        
        self.data_lock = threading.Lock()
        self.latest_congestion_data: Dict[str, Dict] = {}
        self.latest_panel_data: Dict[str, Dict] = {}

        self.override_manager = OverrideStateManager()
        # Proxy queue for backwards compatibility
        self.command_queue = self.override_manager.command_queue

        self.blink_toggle = False

        # Adding throttling for congestion updates
        self.last_update_time = 0
        self.throttle_interval = 0.1  # 100ms between updates

    def start(self):
        if not self.thread or not self.thread.is_alive():
            self.is_running = True
            self.thread = threading.Thread(target=self._updater_loop, daemon=True)
            self.thread.start()
            logging.info("[MapAnimator] Animation thread started.")

    def stop(self):
        self.is_running = False
        logging.info("[MapAnimator] Signal sent to stop the animation thread.")

    def update_data(self, data_packet: dict):
        with self.data_lock:
            packet_type = data_packet.get("type", "unknown")
            
            if packet_type == "initial_map_geometry":
                self.latest_congestion_data = data_packet.get("congestion_update", {})
            elif packet_type in ["congestion_update", "update_dashboard_data"]:
                self.latest_congestion_data = data_packet.get("payload", {})
            
            self.latest_panel_data = data_packet.get("panel_data", {})

    def _updater_loop(self):
        """The main loop that reads the latest telemetry and applies ALL visual updates."""
        while self.is_running:
            try:
                self.blink_toggle = not self.blink_toggle

                with self.data_lock:
                    congestion_to_render = self.latest_congestion_data.copy()
                    panel_data_to_render = self.latest_panel_data.copy()

                # Process command queue for overrides
                self.override_manager.process_queue()
                street_overrides = self.override_manager.get_street_overrides()
                semaphore_overrides = self.override_manager.get_semaphore_overrides()

                # Apply throttling for congestion heatmap rendering
                current_time = time.time()
                should_update_congestion = (current_time - self.last_update_time) >= self.throttle_interval
                
                if should_update_congestion and self.edge_paths and congestion_to_render:
                    for edge_id, path_object in self.edge_paths.items():
                        
                        is_blocked = False
                        
                        siblings = self.edge_group_map.get(edge_id, [edge_id])
                        max_congestion = None
                        
                        for sibling in siblings:
                            if street_overrides.get(sibling) == "BLOCKED":
                                is_blocked = True
                                
                            base_sibling = sibling[1:] if sibling.startswith('-') else sibling
                            reverse_sibling = '-' + base_sibling if not sibling.startswith('-') else base_sibling
                            
                            val = None
                            if sibling in congestion_to_render:
                                val = congestion_to_render[sibling]
                            elif base_sibling in congestion_to_render:
                                val = congestion_to_render[base_sibling]
                            elif reverse_sibling in congestion_to_render:
                                val = congestion_to_render[reverse_sibling]
                                
                            if val is not None:
                                if isinstance(val, dict):
                                    val = val.get('congestion', 0.0)
                                if max_congestion is None or val > max_congestion:
                                    max_congestion = val
                                    
                        if is_blocked:
                            new_color = "#000000" # Black for blocked streets
                        elif max_congestion is not None:
                            new_color = HeatmapColorResolver.get_color_for_congestion(max_congestion)
                        else:
                            new_color = "#3394a3b8" # Base map color for empty streets (Muted Slate)
                            
                        if path_object.paint.color != new_color:
                            path_object.paint = ft.Paint(
                                stroke_width=path_object.paint.stroke_width,
                                color=new_color,
                                style=path_object.paint.style,
                                stroke_cap=path_object.paint.stroke_cap
                            )
                    
                    # Update the time of the last execution
                    self.last_update_time = current_time

                # OCP: Delegate updates to the widget itself instead of using conditional statements
                if self.interactive_widgets and panel_data_to_render:
                    for widget_id, widget in self.interactive_widgets.items():
                        if hasattr(widget, 'apply_telemetry'):
                            widget.apply_telemetry(panel_data_to_render, semaphore_overrides, self.blink_toggle)

                # --- Update details pane via Callbacks ---
                if self.get_panel_state_callback and self.on_panel_update_callback:
                    panel_state = self.get_panel_state_callback()
                    selected_id = panel_state.get('selected_id')
                    is_panel_visible = panel_state.get('is_panel_visible', False)
                    
                    if selected_id and is_panel_visible:
                        semaphore_data = panel_data_to_render.get(selected_id, {})
                        
                        # Intercept data if the traffic light is manually overridden
                        override_state = semaphore_overrides.get(selected_id)
                        if override_state:
                            # Copy to avoid mutating original dictionary in memory
                            semaphore_data = semaphore_data.copy() if semaphore_data else {}
                            lanes_state = semaphore_data.get("lanes_state", {}).copy()
                            
                            if override_state == "ALERT":
                                blink_char = 'y' if self.blink_toggle else 'o'
                                for lane in lanes_state:
                                    lanes_state[lane] = blink_char
                                semaphore_data["display_state"] = "YELLOW"
                            elif override_state == "OFF":
                                for lane in lanes_state:
                                    lanes_state[lane] = 'o'
                                semaphore_data["display_state"] = "OFF"
                                
                            semaphore_data["lanes_state"] = lanes_state
                        
                        phase = panel_state.get('phase', "UNKNOWN")
                        mode = panel_state.get('mode', "UNKNOWN")
                        
                        # Command update of the details panel via callback
                        self.on_panel_update_callback(selected_id, semaphore_data, phase, mode)

                # Major map update still required
                if self.widget and getattr(self.widget, 'page', None):
                    try:
                        self.widget.update()
                    except AssertionError:
                        pass
                    try:
                        if hasattr(self.widget, 'canvas') and getattr(self.widget.canvas, 'page', None):
                            self.widget.canvas.update()
                    except AssertionError:
                        pass # Ignore if still not fully mounted
                
                time.sleep(self.interval)

            except RuntimeError as e:
                # Protection against "Event loop is closed"
                if "Event loop is closed" in str(e) or "shutdown" in str(e):
                    logging.info("[MapAnimator Thread] Flet Event Loop closed. Stopping animations.")
                    self.is_running = False
                    break
                else:
                    logging.error(f"[MapAnimator Thread] Unexpected Runtime error: {e}")
            except Exception as e:
                logging.error(f"[MapAnimator Thread] Error: {e}. Stopping thread.", exc_info=True)
                self.is_running = False
                break