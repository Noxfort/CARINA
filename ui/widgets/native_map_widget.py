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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: ui/widgets/native_map_widget.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o NativeMapWidget.

Nesta versão, a lógica de busca de arquivos foi extraída para o
PlanningMapLoader, e o método de update foi corrigido para refletir a
ligação direta dos objetos de transformação.
"""

import flet as ft
import logging
import os
import base64
import threading
import time

from ui.handlers.locale_manager import LocaleManager
from ui.widgets.map_legend_widget import MapLegendWidget
from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.loader.planning_map_loader import PlanningMapLoader


class NativeMapWidget(ft.Container):
    """
    Widget de mapa interativo que exibe a imagem de rede e uma legenda flutuante.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(
            expand=True,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLACK12,
            border_radius=10,
        )
        
        self.locale_manager = locale_manager
        self.interaction_handler = MapInteractionHandler(
            base_width=1280, 
            base_height=720, 
            on_update_callback=self.update
        )
        self.loader = PlanningMapLoader(on_complete_callback=self._on_map_path_found)

        self.image_widget = ft.Image(
            fit=ft.ImageFit.CONTAIN,
            # The handler's scale and offset objects are passed directly
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
            animate_scale=50,
            animate_offset=50
        )

        image_container = ft.Container(
            content=self.image_widget,
            expand=True,
            alignment=ft.alignment.center
        )
        
        self._last_right_click_time = 0
        def _on_secondary_tap_down(e):
            current_time = time.time()
            if current_time - self._last_right_click_time < 0.3:
                self.interaction_handler.center_and_reset_zoom()
            self._last_right_click_time = current_time

        self.interactive_map = ft.GestureDetector(
            content=image_container,
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=self.interaction_handler.handle_zoom,
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_secondary_tap_down=_on_secondary_tap_down,
            drag_interval=5,
        )
        
        self.legend_widget = MapLegendWidget(locale_manager=self.locale_manager)
        
        self.error_title = ft.Text(size=16)
        self.error_subtitle = ft.Text(italic=True, text_align=ft.TextAlign.CENTER)
        self.error_message_column = ft.Column(
            controls=[
                ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, color=ft.Colors.AMBER, size=50),
                self.error_title,
                self.error_subtitle,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True, spacing=10,
        )

        self.loading_indicator = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text("A carregar mapa de planeamento...")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        )
        
        self.content = ft.Stack(
            controls=[
                ft.Container(self.loading_indicator, alignment=ft.alignment.center, expand=True)
            ]
        )
        
        self.did_mount = self.on_mount

    def on_mount(self):
        """Chamado quando o widget é montado."""
        self.update_translations(self.locale_manager)
        self.loader.start_loading()

    def _on_map_path_found(self, map_path: str | None):
        """
        Callback chamado pelo PlanningMapLoader quando a busca termina.
        Chama o método de atualização da UI.
        """
        self._update_map_display(map_path)

    def _update_map_display(self, map_path: str | None):
        """Atualiza a UI com a imagem do mapa ou com uma mensagem de erro."""
        image_loaded = False
        if map_path and os.path.exists(map_path):
            try:
                with open(map_path, "rb") as image_file:
                    b64_string = base64.b64encode(image_file.read()).decode("utf-8")
                self.image_widget.src_base64 = b64_string
                self.content.controls = [self.interactive_map, self.legend_widget]
                image_loaded = True
            except Exception as e:
                logging.error(f"[NativeMapWidget] Falhou ao ler/codificar a imagem do mapa: {e}")
        
        if not image_loaded:
            self.content.controls = [self.error_message_column]
        
        if self.page: self.update()

    def refresh_map_image(self):
        """Reinicia o processo de carregamento do mapa."""
        self.content.controls = [ft.Container(self.loading_indicator, alignment=ft.alignment.center, expand=True)]
        if self.page: self.update()
        self.loader.start_loading()

    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste widget e de seus filhos."""
        self.error_title.value = lm.get_string("planning_view.map_error_title")
        self.error_subtitle.value = lm.get_string("planning_view.map_error_subtitle")
        self.legend_widget.update_translations(lm)
        if self.page: self.update()

    # --- MAIN CHANGE HERE ---
    def update(self):
        """
        Aciona uma atualização visual do widget.
        Este método é chamado como callback pelo MapInteractionHandler quando o utilizador
        faz pan ou zoom. Como os objetos de scale/offset já estão ligados diretamente,
        só precisamos de chamar o update() da superclasse.
        """
        super().update()
    # --- END OF CHANGE ---