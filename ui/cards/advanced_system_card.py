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

# File: ui/widgets/advanced_system_card.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o AdvancedSystemCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

from ui.handlers.locale_manager import LocaleManager

class AdvancedSystemCard(ft.Card):
    """
    Um Card que encapsula as configurações avançadas de Treinamento e Sistema.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9]")
        float_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_pbt_frequency = ft.TextField(
            value=initial_values.get('pbt_frequency', '10'),
            input_filter=float_filter
        )
        self.tf_pbt_exploitation = ft.TextField(
            value=initial_values.get('pbt_exploitation', '25'),
            input_filter=float_filter
        )
        self.tf_watchdog_grace = ft.TextField(
            value=initial_values.get('watchdog_grace', '30'),
            input_filter=float_filter
        )

        # --- Analysis Interval: Number + Unit Selector ---
        self.analysis_interval_label = ft.Text(size=14, weight=ft.FontWeight.W_500)

        self.tf_analysis_interval_value = ft.TextField(
            value=str(initial_values.get('analysis_interval_value', '7')),
            input_filter=numeric_filter,
            width=100,
            text_align=ft.TextAlign.CENTER,
        )

        self.dd_analysis_interval_unit = ft.Dropdown(
            value=initial_values.get('analysis_interval_unit', 'days'),
            width=160,
            options=[
                ft.dropdown.Option("days"),
                ft.dropdown.Option("weeks"),
                ft.dropdown.Option("months"),
                ft.dropdown.Option("years"),
            ],
        )

        self.analysis_interval_row = ft.Row(
            controls=[
                self.tf_analysis_interval_value,
                self.dd_analysis_interval_unit,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.tf_pbt_frequency,
                self.tf_pbt_exploitation,
                self.tf_watchdog_grace,
                ft.Divider(height=1, thickness=0.5),
                self.analysis_interval_label,
                self.analysis_interval_row,
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        return {
            'pbt_frequency': self.tf_pbt_frequency.value,
            'pbt_exploitation': self.tf_pbt_exploitation.value,
            'watchdog_grace': self.tf_watchdog_grace.value,
            'analysis_interval_value': self.tf_analysis_interval_value.value,
            'analysis_interval_unit': self.dd_analysis_interval_unit.value,
        }

    def set_values(self, values: Dict[str, Any]):
        self.tf_pbt_frequency.value = values.get('pbt_frequency', '10')
        self.tf_pbt_exploitation.value = values.get('pbt_exploitation', '25')
        self.tf_watchdog_grace.value = values.get('watchdog_grace', '30')
        self.tf_analysis_interval_value.value = str(values.get('analysis_interval_value', '7'))
        self.dd_analysis_interval_unit.value = values.get('analysis_interval_unit', 'days')
        if self.page: self.update()

    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.advanced_system_card.title")
        self.tf_pbt_frequency.label = lm.get_string("settings_view.advanced_system_card.pbt_frequency")
        self.tf_pbt_exploitation.label = lm.get_string("settings_view.advanced_system_card.pbt_exploitation")
        self.tf_watchdog_grace.label = lm.get_string("settings_view.advanced_system_card.watchdog_grace")
        self.analysis_interval_label.value = lm.get_string("settings_view.advanced_system_card.analysis_interval_label")

        # Translate dropdown options
        self.dd_analysis_interval_unit.options = [
            ft.dropdown.Option("days", lm.get_string("settings_view.advanced_system_card.unit_days")),
            ft.dropdown.Option("weeks", lm.get_string("settings_view.advanced_system_card.unit_weeks")),
            ft.dropdown.Option("months", lm.get_string("settings_view.advanced_system_card.unit_months")),
            ft.dropdown.Option("years", lm.get_string("settings_view.advanced_system_card.unit_years")),
        ]

        if self.page: self.update()