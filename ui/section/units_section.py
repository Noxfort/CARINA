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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: ui/formatting/units_section.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import flet as ft
from typing import Dict, Any
from ui.handlers.locale_manager import LocaleManager

class UnitsSection(ft.Column):
    """
    Sub-widget of ReportFormattingCard managing report measurement units, such as speed.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()
        self.spacing = 15
        
        self.lbl_units_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_speed_unit = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_decimal_separator = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        self.dd_speed_unit = ft.Dropdown(
            options=[
                ft.dropdown.Option("m/s", "m/s"),
                ft.dropdown.Option("km/h", "km/h"),
                ft.dropdown.Option("imperial", "mph (Imperial)"),
            ],
            value=initial_values.get("xai_speed_unit", "m/s"),
            width=200
        )

        self.dd_decimal_separator = ft.Dropdown(
            options=[
                ft.dropdown.Option(",", "Vírgula Decimal (1,23)"),
                ft.dropdown.Option(".", "Ponto Decimal (1.23)"),
            ],
            value=initial_values.get("decimal_separator", ","),
            width=220
        )
        
        self.controls = [
            self.lbl_units_title,
            ft.Row(
                controls=[
                    ft.Column([self.lbl_speed_unit, self.dd_speed_unit]),
                    ft.Column([self.lbl_decimal_separator, self.dd_decimal_separator]),
                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.START
            )
        ]

    def get_values(self) -> Dict[str, Any]:
        return {
            "xai_speed_unit": self.dd_speed_unit.value,
            "decimal_separator": self.dd_decimal_separator.value,
        }

    def set_values(self, values: Dict[str, Any]):
        self.dd_speed_unit.value = values.get("xai_speed_unit", "m/s")
        self.dd_decimal_separator.value = values.get("decimal_separator", ",")

    def update_translations(self, lm: LocaleManager):
        self.lbl_units_title.value = lm.get_string("settings_view.formatting_card.units_title", default="Unidades de Medida do Relatório")
        self.lbl_speed_unit.value = lm.get_string("settings_view.formatting_card.speed_unit_label", default="Unidade de Velocidade")
        self.lbl_decimal_separator.value = lm.get_string("settings_view.formatting_card.decimal_separator_label", default="Separador Decimal")
        
        if len(self.dd_speed_unit.options) >= 3:
            self.dd_speed_unit.options[2].text = lm.get_string("settings_view.formatting_card.speed_unit_imperial", default="mph (Imperial)")

        if len(self.dd_decimal_separator.options) >= 2:
            self.dd_decimal_separator.options[0].text = lm.get_string("settings_view.formatting_card.decimal_separator_comma", default="Vírgula Decimal (1,23)")
            self.dd_decimal_separator.options[1].text = lm.get_string("settings_view.formatting_card.decimal_separator_dot", default="Ponto Decimal (1.23)")

