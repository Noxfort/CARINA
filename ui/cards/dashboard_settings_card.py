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

# File: ui/widgets/dashboard_settings_card.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o DashboardSettingsCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager

class DashboardSettingsCard(ft.Card):
    """
    Um Card que encapsula as configurações de visualização e do dashboard.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.dd_heatmap_strategy = ft.Dropdown(
            options=[ft.dropdown.Option("max"), ft.dropdown.Option("average")],
            value=initial_values.get('heatmap_strategy', 'max'),
            width=270
        )
        self.tf_heatmap_saturation = ft.TextField(
            value=initial_values.get('heatmap_saturation', '100.0'),
            input_filter=numeric_filter
        )
        
        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                ft.Container(height=5),
                self.dd_heatmap_strategy,
                self.tf_heatmap_saturation,
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'heatmap_strategy': self.dd_heatmap_strategy.value,
            'heatmap_saturation': self.tf_heatmap_saturation.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.dd_heatmap_strategy.value = values.get('heatmap_strategy', 'max')
        self.tf_heatmap_saturation.value = values.get('heatmap_saturation', '100.0')
        if self.page: self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        # Assuming corresponding keys exist in JSON files
        self.title_text.value = lm.get_string("settings_view.dashboard_card.title")
        self.dd_heatmap_strategy.label = lm.get_string("settings_view.dashboard_card.heatmap_strategy")
        self.tf_heatmap_saturation.label = lm.get_string("settings_view.dashboard_card.heatmap_saturation")
        if self.page: self.update()