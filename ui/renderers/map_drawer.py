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

# File: ui/renderers/map_drawer.py
# Author: Gabriel Moraes
# Date: September 23, 2025

"""
Defines the MapDrawer class.

This specialist is responsible for parsing raw map geometry and transforming
it into drawable Flet Canvas shapes.
"""

import flet as ft
import flet.canvas as cv
from typing import Dict, Any, List

class MapDrawer:
    """
    An expert in transforming map geometry data into drawable shapes
    on the Flet Canvas.
    """
    def __init__(self, nodes: Dict, edges: List):
        """
        Initializes the Drawer with raw map data.

        Args:
            nodes (Dict): Dictionary with nodes (intersections) and their coordinates.
            edges (List): List of edges (streets) and their shapes.
        """
        self.nodes = nodes
        self.edges = edges

        # Attributes that will be calculated by the transformation
        self.scale = 1.0
        self.canvas_center_x = 0
        self.canvas_center_y = 0
        self.sumo_center_x = 0
        self.sumo_center_y = 0

    def calculate_transformations(self, view_width: int, view_height: int, fit_factor: float = 0.95):
        """
        Calculates all required values (scale, centers) for coordinate transformation.
        This method must be called before drawing.
        """
        all_x = [n['x'] for n in self.nodes.values()] + [p[0] for e in self.edges for p in e['shape']]
        all_y = [n['y'] for n in self.nodes.values()] + [p[1] for e in self.edges for p in e['shape']]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        map_width = max_x - min_x
        map_height = max_y - min_y
        
        base_scale = min(view_width / map_width, view_height / map_height) if map_width > 0 and map_height > 0 else 1
        self.scale = base_scale * fit_factor

        self.canvas_center_x = view_width / 2
        self.canvas_center_y = view_height / 2
        self.sumo_center_x = min_x + (map_width / 2)
        self.sumo_center_y = min_y + (map_height / 2)

    def transform_point(self, sumo_x: float, sumo_y: float) -> tuple[float, float]:
        """
        Applies the "Render from Center" transformation to a single point.
        """
        relative_x = sumo_x - self.sumo_center_x
        relative_y = sumo_y - self.sumo_center_y
        
        canvas_x = self.canvas_center_x + (relative_x * self.scale)
        canvas_y = self.canvas_center_y - (relative_y * self.scale)
        
        return canvas_x, canvas_y

    def draw_initial_map(self, canvas: cv.Canvas, stroke_width: float = 5.0) -> Dict[str, cv.Path]:
        """
        Draws the base map shapes (streets and nodes) onto the provided Canvas object.

        Args:
            canvas (cv.Canvas): The Flet Canvas object where the map will be drawn.
            stroke_width (float): The thickness of the streets to be drawn.

        Returns:
            Dict[str, cv.Path]: A dictionary mapping street ID to the created Path object.
        """
        edge_paths = {}
        processed_bases = set()
        processed_topology = set()
        
        # First, draw the streets
        for edge in self.edges:
            edge_id = edge.get('id')
            if not edge_id: continue

            from_n = edge.get('from')
            to_n = edge.get('to')
            
            # Topological deduplication: if two edges connect the same nodes (even with different geometry), draw only one.
            if from_n and to_n:
                topo_key = tuple(sorted([from_n, to_n]))
                if topo_key in processed_topology:
                    continue
                processed_topology.add(topo_key)
            else:
                # Fallback to string-based base_id deduplication if topology is missing
                base_id = edge_id[1:] if edge_id.startswith('-') else edge_id
                if base_id in processed_bases:
                    continue
                processed_bases.add(base_id)

            path_points = []
            for i, point in enumerate(edge['shape']):
                tx, ty = self.transform_point(point[0], point[1])
                if i == 0:
                    path_points.append(cv.Path.MoveTo(tx, ty))
                else:
                    path_points.append(cv.Path.LineTo(tx, ty))
            
            path_object = cv.Path(
                path_points,
                paint=ft.Paint(
                    stroke_width=stroke_width,
                    color="#3394a3b8", # Muted semi-transparent slate gray for base map
                    style=ft.PaintingStyle.STROKE,
                    stroke_cap=ft.StrokeCap.ROUND
                )
            )
            canvas.shapes.append(path_object)
            # Store the unique path using the actual edge_id
            edge_paths[edge_id] = path_object
        
        # Then, draw the nodes (intersections) above the streets
        for node_data in self.nodes.values():
            if node_data.get('type') != 'traffic_light':
                tx, ty = self.transform_point(node_data['x'], node_data['y'])
                
                node_circle = cv.Circle(
                    x=tx,
                    y=ty,
                    radius=4,
                    paint=ft.Paint(color=ft.Colors.BLACK)
                )
                canvas.shapes.append(node_circle)
        
        return edge_paths