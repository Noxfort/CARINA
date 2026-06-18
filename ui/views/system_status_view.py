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

# File: ui/views/system_status_view.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define a SystemStatusView.

Nesta versão, a lógica de carregamento de dados foi movida para um cliente
assíncrono (SystemStatusClient) para evitar o bloqueio da UI.
"""

import flet as ft
from typing import Dict, Any

from ui.handlers.locale_manager import LocaleManager
from ui.clients.system_status_client import SystemStatusClient

class SystemStatusView(ft.Container):
    """
    Um widget que carrega e exibe o sumário do sistema de forma assíncrona.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(expand=True, padding=10)
        
        self.locale_manager = locale_manager
        # --- CHANGE 1: Instantiate the client with a callback method ---
        self.client = SystemStatusClient(on_complete_callback=self._on_status_loaded)

        self.title_text = ft.Text(size=20, weight=ft.FontWeight.BOLD)
        
        self.hardware_card_title = ft.Text(size=16, weight=ft.FontWeight.BOLD)
        self.gpu_label = ft.Text()
        self.gpu_text = ft.Text("---", weight=ft.FontWeight.BOLD)

        self.topology_card_title = ft.Text(size=16, weight=ft.FontWeight.BOLD)
        self.nodes_label = ft.Text()
        self.nodes_text = ft.Text("---", weight=ft.FontWeight.BOLD)
        self.edges_label = ft.Text()
        self.edges_text = ft.Text("---", weight=ft.FontWeight.BOLD)

        self.ai_card_title = ft.Text(size=16, weight=ft.FontWeight.BOLD)
        self.local_agents_label = ft.Text()
        self.local_agents_text = ft.Text("---", weight=ft.FontWeight.BOLD)
        self.guardian_agents_label = ft.Text()
        self.guardian_agents_text = ft.Text("---", weight=ft.FontWeight.BOLD)
        
        self.last_updated_label = ft.Text()
        self.last_updated_text = ft.Text(self.locale_manager.get_string("system_status_view.loading", default="A carregar..."), italic=True)

        # --- CHANGE 2: The view now starts with a progress ring ---
        self.progress_ring = ft.ProgressRing()
        self.cards_column = ft.Column(
            controls=[
                ft.Card(
                    elevation=4,
                    content=ft.Container(padding=15, content=ft.Column([
                        self.hardware_card_title, ft.Divider(height=5),
                        ft.Row([self.gpu_label, self.gpu_text]),
                    ]))
                ),
                ft.Card(
                    elevation=4,
                    content=ft.Container(padding=15, content=ft.Column([
                        self.topology_card_title, ft.Divider(height=5),
                        ft.Row([self.nodes_label, self.nodes_text]),
                        ft.Row([self.edges_label, self.edges_text]),
                    ]))
                ),
                ft.Card(
                    elevation=4,
                    content=ft.Container(padding=15, content=ft.Column([
                        self.ai_card_title, ft.Divider(height=5),
                        ft.Row([self.local_agents_label, self.local_agents_text]),
                        ft.Row([self.guardian_agents_label, self.guardian_agents_text]),
                    ]))
                ),
                ft.Row([self.last_updated_label, self.last_updated_text], alignment=ft.MainAxisAlignment.END)
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            visible=False # Starts invisible
        )

        self.content = ft.Column(
            controls=[
                ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED), self.title_text], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(
                    content=ft.Stack([
                        ft.Container(self.progress_ring, alignment=ft.alignment.center),
                        self.cards_column
                    ]),
                    expand=True
                )
            ],
            expand=True, spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
        # --- END OF CHANGE 2 ---

    def did_mount(self):
        """Chamado quando o widget é montado na página."""
        self.update_translations(self.locale_manager)
        # --- CHANGE 3: Starts data fetching asynchronously ---
        self.client.start_fetching_status()

    # --- CHANGE 4: New callback methods to process results ---
    def _on_status_loaded(self, response: Dict[str, Any]):
        """Callback executado pelo cliente quando os dados são carregados."""
        self._update_ui_with_data(response)

    def _update_ui_with_data(self, response: Dict[str, Any]):
        """Atualiza a UI na thread principal com os dados recebidos."""
        if not self.page: return

        self.progress_ring.visible = False
        
        if response.get("status") == "complete":
            data = response.get("data", {})
            self.gpu_text.value = data.get("gpu_info", self.locale_manager.get_string("system_status_view.gpu_not_detected", default="Não detectada"))
            self.nodes_text.value = str(data.get("network_topology", {}).get("nodes", "N/A"))
            self.edges_text.value = str(data.get("network_topology", {}).get("edges", "N/A"))
            self.local_agents_text.value = str(data.get("agent_count", {}).get("local_agents", "N/A"))
            self.guardian_agents_text.value = str(data.get("agent_count", {}).get("guardian_agents", "N/A"))
            self.last_updated_text.value = data.get("last_updated_formatted", "N/A")
            self.last_updated_text.color = None
            self.last_updated_text.italic = True
        else:
            message_key = response.get("message_key", "system_status_view.status_file_error")
            error_details = response.get("error_details", "")
            template = self.locale_manager.get_string(message_key)
            self.last_updated_text.value = template.format(error=error_details)
            self.last_updated_text.color = ft.Colors.ORANGE
            self.last_updated_text.italic = False
        
        self.cards_column.visible = True
        self.update()
    # --- END OF CHANGE 4 ---

    def update_translations(self, lm: LocaleManager):
        """Atualiza todos os textos deste widget."""
        self.title_text.value = lm.get_string("diagnostics_view.nav_system")
        self.hardware_card_title.value = lm.get_string("system_status_view.hardware_title")
        self.gpu_label.value = lm.get_string("system_status_view.gpu_label")
        self.topology_card_title.value = lm.get_string("system_status_view.topology_title")
        self.nodes_label.value = lm.get_string("system_status_view.nodes_label")
        self.edges_label.value = lm.get_string("system_status_view.edges_label")
        self.ai_card_title.value = lm.get_string("system_status_view.ai_title")
        self.local_agents_label.value = lm.get_string("system_status_view.local_agents_label")
        self.guardian_agents_label.value = lm.get_string("system_status_view.guardian_agents_label")
        self.last_updated_label.value = lm.get_string("system_status_view.last_updated_label")
        if self.page: self.update()