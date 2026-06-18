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

# File: ui/widgets/traffic_rules_card.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o TrafficRulesCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager

class TrafficRulesCard(ft.Card):
    """
    Um Card que encapsula as configurações de regras de trânsito.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_min_green_time = ft.TextField(
            value=initial_values.get('min_green_time', '10'),
            input_filter=numeric_filter
        )
        self.tf_yellow_time = ft.TextField(
            value=initial_values.get('yellow_time', '3'),
            input_filter=numeric_filter
        )
        
        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.tf_min_green_time,
                self.tf_yellow_time
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'min_green_time': self.tf_min_green_time.value,
            'yellow_time': self.tf_yellow_time.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.tf_min_green_time.value = values.get('min_green_time', '10')
        self.tf_yellow_time.value = values.get('yellow_time', '3')
        if self.page: self.update()
        
    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        # Assuming corresponding keys exist in JSON files
        self.title_text.value = lm.get_string("settings_view.traffic_rules_card.title")
        self.tf_min_green_time.label = lm.get_string("settings_view.traffic_rules_card.min_green_time")
        self.tf_yellow_time.label = lm.get_string("settings_view.traffic_rules_card.yellow_time")
        if self.page: self.update()