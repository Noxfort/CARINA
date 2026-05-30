# File: ui/handlers/map_drawer.py (INITIAL STREETS COLOR CHANGED TO DARK BLUE)
# Author: Gabriel Moraes
# Date: September 23, 2025

"""
Define a classe MapDrawer.

Esta versão altera a cor inicial com que as ruas são desenhadas para um tom
de azul escuro, representando um estado de trânsito baixo ou nulo.
"""

import flet as ft
import flet.canvas as cv
from typing import Dict, Any, List

class MapDrawer:
    """
    Um especialista em transformar dados de geometria de mapa em formas
    desenháveis no Flet Canvas.
    """
    def __init__(self, nodes: Dict, edges: List):
        """
        Inicializa o Desenhista com os dados brutos do mapa.

        Args:
            nodes (Dict): Dicionário com os nós (cruzamentos) e suas coordenadas.
            edges (List): Lista com as arestas (ruas) e suas formas.
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
        Calcula todos os valores necessários (escala, centros) para a
        transformação de coordenadas. Este método deve ser chamado antes do desenho.
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

    def _transform_point(self, sumo_x: float, sumo_y: float) -> tuple[float, float]:
        """
        Aplica a transformação "Renderização a Partir do Centro" a um único ponto.
        """
        relative_x = sumo_x - self.sumo_center_x
        relative_y = sumo_y - self.sumo_center_y
        
        canvas_x = self.canvas_center_x + (relative_x * self.scale)
        canvas_y = self.canvas_center_y - (relative_y * self.scale)
        
        return canvas_x, canvas_y

    def draw_initial_map(self, canvas: cv.Canvas, stroke_width: float = 5.0) -> Dict[str, cv.Path]:
        """
        Desenha as formas do mapa base (ruas e nós) no objeto Canvas fornecido.

        Args:
            canvas (cv.Canvas): O objeto Canvas do Flet onde o mapa será desenhado.
            stroke_width (float): A espessura das ruas a serem desenhadas.

        Returns:
            Dict[str, cv.Path]: Um dicionário mapeando ID da rua para o objeto Path criado.
        """
        edge_paths = {}
        
        # First, draw the streets
        for edge in self.edges:
            edge_id = edge.get('id')
            if not edge_id: continue

            path_points = []
            for i, point in enumerate(edge['shape']):
                tx, ty = self._transform_point(point[0], point[1])
                if i == 0:
                    path_points.append(cv.Path.MoveTo(tx, ty))
                else:
                    path_points.append(cv.Path.LineTo(tx, ty))
            
            path_object = cv.Path(
                path_points,
                paint=ft.Paint(
                    stroke_width=stroke_width,
                    # --- CHANGE APPLIED HERE ---
                    color=ft.colors.BLUE_900, # Dark blue color for zero/initial transit
                    style=ft.PaintingStyle.STROKE,
                    stroke_cap=ft.StrokeCap.ROUND
                )
            )
            canvas.shapes.append(path_object)
            edge_paths[edge_id] = path_object
        
        # Then, draw the nodes (intersections) above the streets
        for node_data in self.nodes.values():
            if node_data.get('type') != 'traffic_light':
                tx, ty = self._transform_point(node_data['x'], node_data['y'])
                
                node_circle = cv.Circle(
                    x=tx,
                    y=ty,
                    radius=4,
                    paint=ft.Paint(color=ft.Colors.BLACK)
                )
                canvas.shapes.append(node_circle)
        
        return edge_paths