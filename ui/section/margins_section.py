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

# File: ui/formatting/margins_section.py
# Author: Gabriel Moraes
# Date: 2026-07-01

import flet as ft
from typing import Dict, Any
from ui.handlers.locale_manager import LocaleManager

class MarginsSection(ft.Column):
    """
    Sub-widget of ReportFormattingCard managing page margins in centimeters.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()
        self.spacing = 15
        
        self.lbl_margins_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_margin_top = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_margin_bottom = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_margin_left = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_margin_right = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        self.tf_margin_top = ft.TextField(
            value=str(initial_values.get("xai_margin_top", "3.0")),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        self.tf_margin_bottom = ft.TextField(
            value=str(initial_values.get("xai_margin_bottom", "2.0")),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        self.tf_margin_left = ft.TextField(
            value=str(initial_values.get("xai_margin_left", "3.0")),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        self.tf_margin_right = ft.TextField(
            value=str(initial_values.get("xai_margin_right", "2.0")),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.controls = [
            self.lbl_margins_title,
            ft.Row(
                controls=[
                    ft.Column([self.lbl_margin_top, self.tf_margin_top]),
                    ft.Column([self.lbl_margin_bottom, self.tf_margin_bottom]),
                    ft.Column([self.lbl_margin_left, self.tf_margin_left]),
                    ft.Column([self.lbl_margin_right, self.tf_margin_right]),
                ],
                spacing=20
            )
        ]

    def get_values(self) -> Dict[str, Any]:
        return {
            "xai_margin_top": float(self.tf_margin_top.value) if self.tf_margin_top.value else 3.0,
            "xai_margin_bottom": float(self.tf_margin_bottom.value) if self.tf_margin_bottom.value else 2.0,
            "xai_margin_left": float(self.tf_margin_left.value) if self.tf_margin_left.value else 3.0,
            "xai_margin_right": float(self.tf_margin_right.value) if self.tf_margin_right.value else 2.0,
        }

    def set_values(self, values: Dict[str, Any]):
        self.tf_margin_top.value = str(values.get("xai_margin_top", "3.0"))
        self.tf_margin_bottom.value = str(values.get("xai_margin_bottom", "2.0"))
        self.tf_margin_left.value = str(values.get("xai_margin_left", "3.0"))
        self.tf_margin_right.value = str(values.get("xai_margin_right", "2.0"))

    def update_translations(self, lm: LocaleManager):
        self.lbl_margins_title.value = lm.get_string("settings_view.formatting_card.margins_title", default="Margens da Página (centímetros)")
        self.lbl_margin_top.value = lm.get_string("settings_view.formatting_card.margin_top", default="Superior")
        self.lbl_margin_bottom.value = lm.get_string("settings_view.formatting_card.margin_bottom", default="Inferior")
        self.lbl_margin_left.value = lm.get_string("settings_view.formatting_card.margin_left", default="Esquerda")
        self.lbl_margin_right.value = lm.get_string("settings_view.formatting_card.margin_right", default="Direita")
