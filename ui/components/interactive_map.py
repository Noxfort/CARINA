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

# File: ui/components/interactive_map.py
# Author: Gabriel Moraes
# Date: December 16, 2025

import flet as ft
import flet.canvas as cv
import math

from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.loader.map_asset_loader import MapAssetLoader
from ui.renderers.planning_map_renderer import PlanningMapRenderer

class InteractiveMap(ft.Container):
    """
    Interactive Vector Map Orchestrator Component.
    Delegates geographic file reading to MapAssetLoader and maps
    matrix rendering to PlanningMapRenderer. (SOLID SRP/DIP compliance).
    """

    def __init__(self, project_root: str, on_node_click=None):
        super().__init__(expand=True)
        
        self.project_root = project_root
        self.on_node_click = on_node_click 
        
        self.topology = None
        self.drawn_nodes_cache = [] 
        self.recommendations = {}
        
        self.base_width = 1200
        self.base_height = 800
        
        # Specialized Core Modules (Composition)
        self.asset_loader = MapAssetLoader()
        self.renderer = PlanningMapRenderer(self.base_width, self.base_height)
        self.interaction_handler = MapInteractionHandler(
             base_width=self.base_width, 
             base_height=self.base_height, 
             on_update_callback=self.update
        )

        self.canvas_static = cv.Canvas(shapes=[], expand=True) 
        self.canvas_dynamic = cv.Canvas(shapes=[], expand=True) 

        self.last_mouse_x = self.base_width / 2
        self.last_mouse_y = self.base_height / 2

        self.map_stack = ft.Stack(
            controls=[self.canvas_static, self.canvas_dynamic],
            width=self.base_width,
            height=self.base_height,
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
        )

        def _on_hover(e: ft.HoverEvent):
             self.last_mouse_x = e.local_x
             self.last_mouse_y = e.local_y

        self.gesture_detector = ft.GestureDetector(
            content=ft.Container(
                content=self.map_stack, 
                bgcolor="#F7F7F7",
                alignment=ft.alignment.center
            ),
            on_hover=_on_hover,
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=lambda e: self.interaction_handler.handle_zoom(e, self.last_mouse_x, self.last_mouse_y),
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_tap_down=self._handle_tap,
            drag_interval=10
        )

        self.content = self.gesture_detector
        self.bgcolor = "#F7F7F7"
        self.clip_behavior = ft.ClipBehavior.NONE 
        self.border_radius = 10

    def load_map(self):
        """Orchestrates loading of topology JSON and delegates to the external Renderer."""
        map_data = self.asset_loader.load_map_data()
        
        if map_data:
            nodes, edges, bounds = map_data
            self.topology = {"nodes": nodes, "edges": edges, "bounds": bounds}
            
            print(f"[InteractiveMap Orchestrator] Topology loaded into memory. Initiating delegation...")
            self.renderer.calculate_initial_fit(self.topology)
            self._draw()
            
            self.interaction_handler.center_and_reset_zoom()
            self.update()
        else:
            print(f"[InteractiveMap Orchestrator] Map Asset Loader failed to find topology.")

    def set_recommendations(self, recs: dict):
        """Atualiza as recomendações e re-renderiza o mapa com as novas cores."""
        self.recommendations = recs
        if self.topology:
            self._draw()
            self.update()

    def _draw(self):
        """Requests PlanningMapRenderer to flush pixels onto the Stack Canvas."""
        self.renderer.draw_topology(
            topology=self.topology,
            canvas_static=self.canvas_static,
            canvas_dynamic=self.canvas_dynamic,
            drawn_nodes_cache=self.drawn_nodes_cache,
            recommendations=self.recommendations
        )

    def _handle_tap(self, e: ft.TapEvent):
        """Calculates hitbox detection for absolute Flet Mouse events."""
        scale = self.interaction_handler.scale.scale
        offset = self.interaction_handler.offset
        
        center_x = self.base_width / 2 
        center_y = self.base_height / 2
        
        click_x, click_y = e.local_x, e.local_y
        
        clicked_node_id = None
        min_dist = float('inf')
        
        effective_scale = scale
        # Hardcoded offset multiplier fixed via absolute tracking widths
        off_x = offset.x * self.base_width 
        off_y = offset.y * self.base_height
        
        for node in self.drawn_nodes_cache:
            screen_x = (node['cx'] - center_x) * effective_scale + center_x + off_x
            screen_y = (node['cy'] - center_y) * effective_scale + center_y + off_y
            
            dx = click_x - screen_x
            dy = click_y - screen_y
            dist = math.sqrt(dx*dx + dy*dy)
            
            hit = self.renderer.hit_radius * effective_scale 
            
            if dist < hit and dist < min_dist:
                min_dist = dist
                clicked_node_id = node['id']

        if clicked_node_id:
            print(f"[InteractiveMap Orchestrator] Intersection Hit detected: {clicked_node_id}")
            if self.on_node_click:
                self.on_node_click(clicked_node_id)