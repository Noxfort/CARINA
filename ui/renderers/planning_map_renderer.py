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

# File: ui/handlers/planning_map_renderer.py
# Author: Gabriel Moraes
# Date: April 16, 2026

import flet as ft
import flet.canvas as cv

class PlanningMapRenderer:
    """
    Exclusive specialist responsible for Geometry, Parsing, and Drawing 
    of static/dynamic vector maps. Extracted from original God Class.
    """
    def __init__(self, base_width: int, base_height: int):
        self.base_width = base_width
        self.base_height = base_height
        
        self.fit_scale = 1.0
        self.fit_offset_x = 0
        self.fit_offset_y = 0
        
        # Domain Aesthetics
        self.street_color = ft.Colors.BLACK
        self.street_width = 4.5
        
        self.tl_box_color = ft.Colors.BLUE_800 
        self.tl_light_colors = [ft.Colors.RED, ft.Colors.AMBER, ft.Colors.GREEN]
        self.hit_radius = 25.0 
        
        self.junction_color = ft.Colors.ORANGE_600
        self.junction_radius = 6.0 

    def calculate_initial_fit(self, topology: dict):
        if not topology: return
        try:
            bounds = topology.get('bounds')
            if not bounds:
                print("[PlanningMapRenderer] Warning: 'bounds' not found in JSON.")
                return

            min_x, min_y = bounds['min_x'], bounds['min_y']
            max_x, max_y = bounds['max_x'], bounds['max_y']
            
            map_w = max_x - min_x
            map_h = max_y - min_y
            if map_w == 0: map_w = 1
            if map_h == 0: map_h = 1

            scale_x = self.base_width / map_w
            scale_y = self.base_height / map_h
            self.fit_scale = min(scale_x, scale_y) * 0.95 
            
            pixel_map_w = map_w * self.fit_scale
            pixel_map_h = map_h * self.fit_scale
            
            self.fit_offset_x = (self.base_width - pixel_map_w) / 2
            self.fit_offset_y = (self.base_height - pixel_map_h) / 2
        except Exception as e:
            print(f"[PlanningMapRenderer] Error calculating fit scale: {e}")

    def map_to_canvas(self, topology: dict, mx: float, my: float) -> tuple[float, float]:
        try:
            bounds = topology['bounds']
            rel_x = mx - bounds['min_x']
            rel_y_flipped = bounds['max_y'] - my
            cx = self.fit_offset_x + (rel_x * self.fit_scale)
            cy = self.fit_offset_y + (rel_y_flipped * self.fit_scale)
            return cx, cy
        except:
            return 0, 0

    def create_traffic_light_icon(self, sx: float, sy: float, rec_type: str = "existing"):
        shapes = []
        box_w, box_h = 16, 42 
        light_radius = 5 
        spacing = 11 
        
        if rec_type == "add":
            box_color = ft.Colors.GREEN_700
        elif rec_type == "remove":
            box_color = ft.Colors.RED_700
        else:
            box_color = self.tl_box_color
            
        shapes.append(cv.Rect(
            x=sx - box_w/2, y=sy - box_h/2,
            width=box_w, height=box_h,
            border_radius=4,
            paint=ft.Paint(color=box_color, style=ft.PaintingStyle.FILL)
        ))
        
        y_offsets = [-spacing, 0, spacing]
        for i in range(3):
             shapes.append(cv.Circle(
                x=sx, y=sy + y_offsets[i],
                radius=light_radius,
                paint=ft.Paint(color=self.tl_light_colors[i], style=ft.PaintingStyle.FILL)
            ))
        return shapes

    def draw_topology(self, topology: dict, canvas_static: cv.Canvas, canvas_dynamic: cv.Canvas, drawn_nodes_cache: list, recommendations: dict = None):
        if not topology: return
        recommendations = recommendations or {}
        
        # Clears ONLY Nodes/Semaphores on loop (60 FPS isolation)
        canvas_dynamic.shapes.clear()
        drawn_nodes_cache.clear()
        
        draw_streets = len(canvas_static.shapes) == 0

        # Paints Geographic Routes
        if draw_streets:
            edges_data = topology.get('edges', [])
            if isinstance(edges_data, dict): edges_iter = edges_data.values()
            elif isinstance(edges_data, list): edges_iter = edges_data
            else: edges_iter = []

            for edge_item in edges_iter:
                if not edge_item: continue
                try:
                    shape_points = edge_item.get('shape') if isinstance(edge_item, dict) else edge_item
                    if not shape_points or len(shape_points) < 2: continue
                    
                    points = []
                    start_x, start_y = self.map_to_canvas(topology, shape_points[0][0], shape_points[0][1])
                    points.append(cv.Path.MoveTo(start_x, start_y))
                    
                    for coord in shape_points[1:]:
                        cx, cy = self.map_to_canvas(topology, coord[0], coord[1])
                        points.append(cv.Path.LineTo(cx, cy))
                        
                    canvas_static.shapes.append(
                        cv.Path(
                            elements=points,
                            paint=ft.Paint(
                                color=self.street_color,
                                stroke_width=self.street_width,
                                stroke_cap=ft.StrokeCap.ROUND, 
                                style=ft.PaintingStyle.STROKE
                            )
                        )
                    )
                except Exception as e:
                    print(f"[PlanningMapRenderer] Error drawing specific edge: {e}")
                    continue

        # Paints Traffic Lights and Junctions
        nodes_data = topology.get('nodes', [])
        if isinstance(nodes_data, dict): nodes_iter = nodes_data.values()
        elif isinstance(nodes_data, list): nodes_iter = nodes_data
        else: nodes_iter = []

        for node in nodes_iter:
            try:
                if 'x' not in node or 'y' not in node: continue

                cx, cy = self.map_to_canvas(topology, node['x'], node['y'])
                node_type = node.get('type', '')
                node_id = node.get('id', 'unknown')
                
                # Check recommendation first to see if we should upgrade this junction to show an icon
                rec_string = recommendations.get(node_id, {}).get("recommendation", "")
                rec_type = "existing"
                if "adicionar" in rec_string.lower() or "add" in rec_string.lower():
                    rec_type = "add"
                elif "remover" in rec_string.lower() or "remove" in rec_string.lower():
                    rec_type = "remove"

                is_traffic_light = False
                if node_type is None: is_traffic_light = True 
                elif "traffic_light" in str(node_type): is_traffic_light = True
                
                # Draw as traffic light if it is one OR if we recommend adding one!
                if is_traffic_light or rec_type == "add":
                    drawn_nodes_cache.append({"id": node_id, "cx": cx, "cy": cy})
                    icon_shapes = self.create_traffic_light_icon(cx, cy, rec_type)
                    canvas_dynamic.shapes.extend(icon_shapes)
                else:
                    canvas_dynamic.shapes.append(
                        cv.Circle(
                            x=cx, y=cy, radius=self.junction_radius,
                            paint=ft.Paint(color=self.junction_color, style=ft.PaintingStyle.FILL)
                        )
                    )
            except Exception as e:
                print(f"[PlanningMapRenderer] Error drawing specific node: {e}")
                continue
