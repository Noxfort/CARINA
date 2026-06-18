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

# File: ui/builders/map_builder.py
# Author: Gabriel Moraes
# Date: June 17, 2026

"""
Defines the MapBuilder class.
Handles construction and setup of all map components (SRP & OCP compliant).
"""

import flet as ft
import flet.canvas as cv
from typing import Dict, Any, Tuple, Callable

from ui.renderers.map_drawer import MapDrawer
from ui.animators.map_animator import MapAnimator
from ui.managers.map_state_manager import MapStateManager
from ui.builders.map_element_factory import MapElementFactory

class MapBuilder:
    """
    Builder responsible for constructing the map canvas, drawing elements,
    instantiating widgets, managers, and the animator.
    """

    @staticmethod
    def build(
        map_data: Tuple,
        canvas_width: int,
        canvas_height: int,
        map_stack: ft.Stack,
        widget_to_update: ft.Container,
        get_panel_state_callback: Callable[[], Dict],
        on_panel_update_callback: Callable[[str, Dict, str, str], None]
    ) -> Tuple[cv.Canvas, MapDrawer, Dict[str, cv.Path], MapStateManager, MapAnimator]:
        nodes, edges, _ = map_data

        # 1. Fresh canvas with concrete dimensions
        canvas = cv.Canvas(shapes=[], width=canvas_width, height=canvas_height)

        # 2. Draw map paths
        drawer = MapDrawer(nodes, edges)
        drawer.calculate_transformations(canvas_width, canvas_height)
        
        edge_paths = drawer.draw_initial_map(canvas, stroke_width=7.0)

        # 3. Create interactive widgets from nodes
        interactive_widgets_map: Dict[str, Any] = {}
        widgets_list = []
        for node_id, node_data in drawer.nodes.items():
            node_type = node_data.get('type')
            if node_type:
                tx, ty = drawer.transform_point(node_data['x'], node_data['y'])
                widget = MapElementFactory.create_element(node_type, node_id, tx, ty)
                
                if widget:
                    widgets_list.append(widget)
                    if hasattr(widget, 'apply_telemetry'):
                        interactive_widgets_map[node_id] = widget

        # 3.5. Try to load and position the realistic background map
        bg_control = None
        try:
            import os
            import json
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            bg_path = os.path.join(project_root, "ui", "assets", "images", "osm_background.png")
            meta_path = bg_path + ".json"
            if os.path.exists(bg_path) and os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                tx_left, ty_top = drawer.transform_point(meta["x_min"], meta["y_max"])
                tx_right, ty_bottom = drawer.transform_point(meta["x_max"], meta["y_min"])
                width = tx_right - tx_left
                height = ty_bottom - ty_top
                bg_control = ft.Image(
                    src="images/osm_background.png",
                    left=tx_left,
                    top=ty_top,
                    width=width,
                    height=height,
                    fit=ft.ImageFit.FILL,
                    border_radius=ft.border_radius.all(12)
                )
        except Exception as e:
            import logging
            logging.error(f"[MapBuilder] Error loading background map: {e}")

        # 4. Update stack controls (with background image if available)
        if bg_control:
            map_stack.controls = [bg_control, canvas, *widgets_list]
        else:
            map_stack.controls = [canvas, *widgets_list]

        # 5. Instantiate managers
        map_state_manager = MapStateManager(
            canvas=canvas,
            stack=map_stack,
            edge_paths=edge_paths,
            interactive_widgets=interactive_widgets_map
        )

        animator = MapAnimator(
            widget_to_update=widget_to_update,
            get_panel_state_callback=get_panel_state_callback,
            on_panel_update_callback=on_panel_update_callback,
            edge_paths=edge_paths,
            semaforo_widgets=interactive_widgets_map,
            interval=0.5,
            topology_edges=edges
        )

        return canvas, drawer, edge_paths, map_state_manager, animator
