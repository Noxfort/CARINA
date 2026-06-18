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

# File: ui/widgets/reward_weights_card.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o RewardWeightsCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager

class RewardWeightsCard(ft.Card):
    """
    Um Card que encapsula as configurações de pesos de recompensa.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.description_text = ft.Text(italic=True, size=12, color=ft.Colors.WHITE70)
        
        self.tf_weight_waiting_time = ft.TextField(
            value=initial_values.get('weight_waiting_time', '-2.0'),
            input_filter=numeric_filter
        )
        self.tf_weight_flow = ft.TextField(
            value=initial_values.get('weight_flow', '2.0'),
            input_filter=numeric_filter
        )

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.description_text,
                self.tf_weight_waiting_time,
                self.tf_weight_flow
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'weight_waiting_time': self.tf_weight_waiting_time.value,
            'weight_flow': self.tf_weight_flow.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.tf_weight_waiting_time.value = values.get('weight_waiting_time', '-2.0')
        self.tf_weight_flow.value = values.get('weight_flow', '2.0')
        if self.page: self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.reward_weights_card.title")
        self.description_text.value = lm.get_string("settings_view.reward_weights_card.description")
        
        self.tf_weight_waiting_time.label = lm.get_string("settings_view.reward_weights_card.waiting_time_label")
        self.tf_weight_waiting_time.tooltip = lm.get_string("settings_view.reward_weights_card.waiting_time_tooltip")
        
        self.tf_weight_flow.label = lm.get_string("settings_view.reward_weights_card.flow_label")
        self.tf_weight_flow.tooltip = lm.get_string("settings_view.reward_weights_card.flow_tooltip")
        
        if self.page: self.update()