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

# File: ui/widgets/street_info_widget.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o StreetInfoWidget.
"""

import flet as ft
from typing import Callable, Dict

# --- CHANGE 1: Import LocaleManager ---
from ui.handlers.locale_manager import LocaleManager
from ui.managers.alias_manager import AliasManager

class StreetInfoWidget(ft.Card):
    """
    Um Card que exibe os dados de uma rua e pode ser escondido.
    """
    def __init__(
        self,
        locale_manager: LocaleManager,
        control_client=None,
        security_ui=None,
        on_close: Callable[[], None] = None,
        on_street_override: Callable[[str, str], None] = None
    ):
        super().__init__(
            elevation=4,
            visible=False,
            animate_opacity=200
        )

        self.locale_manager = locale_manager
        self.control_client = control_client
        self.security_ui = security_ui
        self.on_close = on_close
        self.on_street_override = on_street_override
        
        self.alias_manager = AliasManager()
        self._current_street_id = None
        self.street_id_text_template = "" # Title template
        
        # Override state locally
        self._is_blocked = False

        # Text controls for labels (so they can be translated)
        self.street_id_text = ft.TextField(
            text_size=14,
            height=40,
            expand=True,
            on_submit=self._on_submit,
            on_blur=self._on_submit,
            tooltip="Pressione Enter para salvar"
        )
        self.congestion_label = ft.Text()
        self.flow_label = ft.Text()
        self.speed_label = ft.Text()
        self.vehicles_label = ft.Text()
        
        # Text controls for values
        self.congestion_text = ft.Text("--")
        self.flow_text = ft.Text("--")
        self.speed_text = ft.Text("--")
        self.vehicles_text = ft.Text("--")

        self.block_button = ft.ElevatedButton(
            text="Desativar Fluxo",
            icon=ft.Icons.BLOCK_ROUNDED,
            on_click=self._handle_block_request,
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_700)
        )
        
        self.content = ft.Container(
            padding=10,
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Icon(ft.Icons.EDIT_ROAD_ROUNDED), self.street_id_text],
                    ),
                    ft.Divider(height=10),
                    ft.Row([self.congestion_label, self.congestion_text]),
                    ft.Row([self.flow_label, self.flow_text]),
                    ft.Row([self.speed_label, self.speed_text]),
                    ft.Row([self.vehicles_label, self.vehicles_text]),
                    ft.Divider(height=10),
                    self.block_button,
                    ft.IconButton(
                        icon=ft.Icons.CLOSE_ROUNDED,
                        on_click=self.hide,
                        tooltip="Fechar painel" # This tooltip will be translated in the parent
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    def did_mount(self):
        """Chamado quando o widget é montado na página."""
        self.update_translations(self.locale_manager)
        if self.page: self.update()

    # --- CHANGE 3: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza todos os textos deste widget com base no LocaleManager."""
        self.street_id_text_template = lm.get_string("dashboard_view.street_info_title_prefix")
        self.street_id_text.label = self.street_id_text_template
        self.congestion_label.value = lm.get_string("dashboard_view.street_congestion")
        self.flow_label.value = lm.get_string("dashboard_view.street_flow")
        self.speed_label.value = lm.get_string("dashboard_view.street_speed")
        self.vehicles_label.value = lm.get_string("dashboard_view.street_vehicles")
        # The close button tooltip is translated by its parent widget (SpecificControlsWidget)
        
    def update_and_show(self, street_id: str, street_data: Dict):
        """
        Atualiza os campos de texto com novos dados e torna o widget visível.
        """
        # --- CHANGE 4: Use the translation template for dynamic text ---
        self._current_street_id = street_id
        self.street_id_text.value = self.alias_manager.get_alias(street_id)
        
        congestion = street_data.get('congestion', 0.0)
        flow = street_data.get('flow', '--')
        speed = street_data.get('speed', 0.0)
        vehicles = street_data.get('vehicles', '--')

        self.congestion_text.value = f"{congestion:.1f}" # The unit (%) will come from the label
        self.flow_text.value = str(flow)
        self.speed_text.value = f"{speed:.1f} km/h"
        self.vehicles_text.value = str(vehicles)
        
        self.visible = True

    def hide(self, e=None):
        """
        Torna o widget invisível e notifica o pai.
        """
        self.visible = False
        if self.on_close:
            self.on_close()

    def _on_submit(self, e):
        """Salva o novo nome (alias) para a rua."""
        if self._current_street_id:
            self.alias_manager.set_alias(self._current_street_id, self.street_id_text.value)
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text("Nome da rua salvo com sucesso!"), bgcolor="green700")
                self.page.snack_bar.open = True
                self.page.update()

    def _handle_block_request(self, e):
        if self.security_ui:
            self.security_ui.request_auth(on_success=self._toggle_block)
        else:
            self._toggle_block()

    def _toggle_block(self):
        self._is_blocked = not self._is_blocked
        new_state = "BLOCKED" if self._is_blocked else "NORMAL"
        
        if self._is_blocked:
            self.block_button.text = "Reativar Fluxo"
            self.block_button.icon = ft.Icons.CHECK_CIRCLE_ROUNDED
            self.block_button.style = ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700)
        else:
            self.block_button.text = "Desativar Fluxo"
            self.block_button.icon = ft.Icons.BLOCK_ROUNDED
            self.block_button.style = ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_700)
            
        if self.page:
            self.update()
            
        if self.control_client and self._current_street_id:
            self.control_client.set_street_override(self._current_street_id, new_state)
            
        if self.on_street_override and self._current_street_id:
            self.on_street_override(self._current_street_id, new_state)