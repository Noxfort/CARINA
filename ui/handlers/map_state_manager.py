# File: ui/handlers/map_state_manager.py (NEW FILE)
# Author: Gabriel Moraes
# Date: September 24, 2025

"""
Define o MapStateManager.

Esta classe especialista é responsável por gerenciar todo o estado visual
do mapa, incluindo a seleção e o destaque de ruas e semáforos. Ela
manipula diretamente os objetos do canvas e do stack para refletir o
estado atual.
"""

import flet as ft
import flet.canvas as cv
from typing import Dict

class MapStateManager:
    """
    Gerencia o estado visual (seleção/destaque) do mapa.
    """
    def __init__(
        self,
        canvas: cv.Canvas,
        stack: ft.Stack,
        edge_paths: Dict[str, cv.Path],
        traffic_light_widgets: Dict[str, ft.Container]
    ):
        """
        Inicializa o gerenciador de estado.

        Args:
            canvas: A referência ao objeto Canvas do mapa.
            stack: A referência ao objeto Stack principal do mapa.
            edge_paths: O dicionário de objetos Path das ruas.
            traffic_light_widgets: O dicionário de widgets de semáforo.
        """
        self.canvas = canvas
        self.stack = stack
        self.edge_paths = edge_paths
        self.traffic_light_widgets = traffic_light_widgets

        # --- Internal state of selection ---
        self.selected_edge_id: str | None = None
        self.selected_semaphore_id: str | None = None
        
        # --- References to featured widgets ---
        self.highlight_casing: cv.Path | None = None
        self.highlight_foreground: cv.Path | None = None
        self.highlight_aura: ft.Container | None = None

    def set_selection(self, item_type: str | None, item_id: str | None):
        """
        Método principal para definir o item selecionado no mapa.
        """
        self._clear_all_highlights()

        if item_type == 'street' and item_id:
            self._highlight_street(item_id)
            self.selected_edge_id = item_id
        elif item_type == 'semaphore' and item_id:
            self._highlight_semaphore(item_id)
            self.selected_semaphore_id = item_id
    
    def _clear_all_highlights(self):
        """Limpa todos os destaques visuais do mapa."""
        self._unhighlight_street()
        self._unhighlight_semaphore()

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

    def _unhighlight_semaphore(self):
        if self.highlight_aura and self.highlight_aura in self.stack.controls:
            self.stack.controls.remove(self.highlight_aura)
        self.highlight_aura = None
        self.selected_semaphore_id = None

    def _highlight_semaphore(self, semaphore_id: str):
        widget = self.traffic_light_widgets.get(semaphore_id)
        if not widget: return

        self.highlight_aura = ft.Container(
            width=widget.width + 8, height=widget.height + 8,
            left=widget.left - 4, top=widget.top - 4,
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.YELLOW_ACCENT_400),
            border_radius=8, animate=ft.Animation(100, "easeOut"),
        )
        
        # Inserts the aura in the correct layer (behind the traffic lights)
        self.stack.controls.insert(1, self.highlight_aura)