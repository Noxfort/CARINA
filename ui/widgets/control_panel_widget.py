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

# File: ui/widgets/control_panel_widget.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o widget do Painel de Controle.
"""

import flet as ft
from typing import Callable, Dict

# --- CHANGE APPLIED HERE: Using absolute imports from 'ui' ---
from ui.widgets.global_controls_widget import GlobalControlsWidget
from ui.widgets.specific_controls_widget import SpecificControlsWidget
from ui.widgets.street_info_widget import StreetInfoWidget
from ui.clients.control_client import ControlClient
from ui.handlers.locale_manager import LocaleManager
# --- END OF CHANGE ---

class ControlPanelWidget(ft.Container):
    """
    O widget que organiza os painéis de controle global e específico.
    """
    def __init__(
        self,
        control_client: ControlClient,
        locale_manager: LocaleManager,
        security_ui=None,
        on_specific_command: Callable[[str, str], None] = None,
        on_street_override: Callable[[str, str], None] = None,
        on_details_close: Callable[[], None] = None,
        on_mode_change: Callable[[str], None] = None
    ):
        super().__init__(
            width=320,
            bgcolor=ft.Colors.with_opacity(0.85, "#1E293B"),
            border_radius=16,
            border=ft.border.all(1, "#334155"),
            padding=15,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.3, "#000000"),
                offset=ft.Offset(0, 5)
            )
        )
        
        self.on_details_close = on_details_close

        self.on_street_override = on_street_override

        self.global_controls = GlobalControlsWidget(
            control_client=control_client,
            locale_manager=locale_manager,
            on_mode_change=on_mode_change
        )
        
        self.specific_controls = SpecificControlsWidget(
            control_client=control_client,
            locale_manager=locale_manager,
            security_ui=security_ui,
            on_close=self.ocultar_todos_detalhes,
            on_specific_command=on_specific_command
        )
        
        self.street_info = StreetInfoWidget(
            locale_manager=locale_manager,
            control_client=control_client,
            security_ui=security_ui,
            on_close=self.ocultar_todos_detalhes,
            on_street_override=self._handle_street_override
        )

        self.content = ft.Column(
            controls=[
                self.global_controls,
                self.specific_controls,
                self.street_info
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )

    def update_translations(self, lm: LocaleManager):
        """Comanda os widgets filhos a se atualizarem com o novo idioma."""
        self.global_controls.update_translations(lm)
        self.specific_controls.update_translations(lm)
        self.street_info.update_translations(lm)
        if self.page: self.update()

    def exibir_controles_semaforo(self, semaphore_id: str, semaphore_data: Dict, phase: str, mode: str):
        self.street_info.visible = False
        self.specific_controls.exibir_controles_semaforo(semaphore_id, semaphore_data, phase, mode)
        if self.page: self.update()

    def _handle_street_override(self, street_id: str, state: str):
        if self.on_street_override:
            self.on_street_override(street_id, state)

    def exibir_info_rua(self, street_id: str, street_data: dict):
        self.specific_controls.visible = False
        self.street_info.update_and_show(street_id, street_data)
        if self.page: self.update()

    def ocultar_todos_detalhes(self, e=None):
        self.specific_controls.visible = False
        self.street_info.visible = False
        if self.on_details_close:
            self.on_details_close()
        if self.page: self.update()