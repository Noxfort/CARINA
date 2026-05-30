# File: ui/handlers/map_interaction_handler.py (FIXED IMPORT PATH)
# Author: Gabriel Moraes
# Date: September 24, 2025

"""
Define o MapInteractionHandler.

Esta versão foi corrigida para usar o caminho de importação correto para as
classes de transformação do Flet (ft.Offset, ft.Scale).
"""

import flet as ft

class MapInteractionHandler:
    """Gerencia o estado e a lógica das interações de pan e zoom do mapa."""

    def __init__(self, base_width: float, base_height: float, on_update_callback):
        """
        Inicializa o handler de interação.
        """
        self.base_width = base_width
        self.base_height = base_height
        # --- CORRECTION APPLIED HERE ---
        # Classes are called directly from 'ft'
        self.offset = ft.Offset(0, 0)
        self.scale = ft.Scale(scale=1.0, alignment=ft.alignment.center)

        # --- Behavior Settings ---
        self.max_zoom = 3.0
        self.min_zoom = 0.5
        
        self.on_update = on_update_callback

    def center_and_reset_zoom(self):
        """Reseta o estado para a visualização inicial."""
        self.scale.scale = 1.0
        self.offset.x = 0.0
        self.offset.y = 0.0
        self.on_update()

    def handle_pan_update(self, e: ft.DragUpdateEvent):
        """Calcula o novo deslocamento do mapa durante um evento de pan."""
        effective_scale = self.scale.scale if self.scale.scale > 0 else 1.0
        
        # Ancoragem exata do vetor Panning mantendo aderência absoluta de mouse sob qualquer zoom (1:1 Tracking)
        self.offset.x += e.delta_x / (self.base_width * effective_scale)
        self.offset.y += e.delta_y / (self.base_height * effective_scale)
        
        self.on_update()

    def handle_zoom(self, e: ft.ScrollEvent, mouse_x: float = None, mouse_y: float = None):
        """Calcula a nova escala do mapa e alinha o Vector Offset (Zoom to Pointer)."""
        old_scale = self.scale.scale
        
        if mouse_x is None: mouse_x = self.base_width / 2.0
        if mouse_y is None: mouse_y = self.base_height / 2.0
        
        if e.scroll_delta_y < 0:
            new_scale = min(self.max_zoom, old_scale * 1.1)
        else:
            new_scale = max(self.min_zoom, old_scale * 0.9)
            
        if new_scale == old_scale:
            return
            
        self.scale.scale = new_scale
        
        # Matemática de Zoom Fiel (Ancoragem no Ponteiro)
        # O Flet Scale com alignment=center cresce em ambas as direções a partir do centro
        # Translada o offset para compensar a magnitude direcional visual do mouse
        center_x = self.base_width / 2.0
        center_y = self.base_height / 2.0
        
        dx = mouse_x - center_x
        dy = mouse_y - center_y
        
        # The true offset logic compensates for the scale difference relative to the center
        self.offset.x -= (dx * (new_scale - old_scale)) / (self.base_width * new_scale)
        self.offset.y -= (dy * (new_scale - old_scale)) / (self.base_height * new_scale)

        self.on_update()