# File: ui/handlers/street_interaction_handler.py (ACCEPTING TRANSLATED COORDINATES)
# Author: Gabriel Moraes
# Date: September 24, 2025

"""
Define o StreetInteractionHandler.

Esta versão foi atualizada para aceitar coordenadas x, y pré-traduzidas,
desacoplando-o da lógica de transformação de pan e zoom do widget pai.
"""

import flet as ft
import flet.canvas as cv
import math
from typing import Callable, Dict

class StreetInteractionHandler:
    """
    Gerencia a lógica de clique e seleção para as ruas no canvas.
    """
    def __init__(self, on_street_selected: Callable[[str | None], None]):
        self.on_street_selected = on_street_selected
        self.edge_paths: Dict[str, cv.Path] = {}
        self.base_hit_threshold = 15.0
        self.selected_edge_id: str | None = None

    def load_paths(self, edge_paths: Dict[str, cv.Path]):
        self.edge_paths = edge_paths

    def handle_click(self, click_x: float, click_y: float, current_scale: float):
        """
        Processa um clique no mapa usando coordenadas já traduzidas para o
        espaço do mapa.
        """
        effective_scale = current_scale if current_scale > 0 else 1.0
        dynamic_threshold = self.base_hit_threshold / effective_scale
        
        closest_edge_id, min_distance = self._find_closest_edge(click_x, click_y)

        newly_selected_id = None
        if closest_edge_id and min_distance <= dynamic_threshold:
            if self.selected_edge_id != closest_edge_id:
                newly_selected_id = closest_edge_id

        self.selected_edge_id = newly_selected_id
        self.on_street_selected(self.selected_edge_id)

    def _dist_sq(self, p1, p2):
        return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

    def _dist_to_segment_sq(self, p, v, w):
        l2 = self._dist_sq(v, w)
        if l2 == 0: return self._dist_sq(p, v)
        t = max(0, min(1, ((p[0] - v[0]) * (w[0] - v[0]) + (p[1] - v[1]) * (w[1] - v[1])) / l2))
        projection = (v[0] + t * (w[0] - v[0]), v[1] + t * (w[1] - v[1]))
        return self._dist_sq(p, projection)

    def _find_closest_edge(self, px: float, py: float) -> tuple[str | None, float]:
        min_dist_sq = float('inf')
        closest_edge_id = None
        click_point = (px, py)

        for edge_id, path_object in self.edge_paths.items():
            points = []
            for element in path_object.elements:
                points.append((element.x, element.y))

            for i in range(len(points) - 1):
                dist_sq = self._dist_to_segment_sq(click_point, points[i], points[i+1])
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_edge_id = edge_id
        
        return closest_edge_id, math.sqrt(min_dist_sq)