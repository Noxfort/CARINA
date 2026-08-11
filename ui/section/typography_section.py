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

# File: ui/formatting/typography_section.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import flet as ft
from typing import Dict, Any
from ui.handlers.locale_manager import LocaleManager

class TypographySection(ft.Column):
    """
    Sub-widget of ReportFormattingCard managing font selection, size, alignment, and line spacing.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()
        self.spacing = 15
        
        self.lbl_typography_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_font = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_size = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_alignment = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_spacing = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        self.dd_font_name = ft.Dropdown(
            options=[
                ft.dropdown.Option("Arial", "Arial"),
                ft.dropdown.Option("Calibri", "Calibri"),
                ft.dropdown.Option("Courier New", "Courier New"),
                ft.dropdown.Option("Times New Roman", "Times New Roman"),
                ft.dropdown.Option("Verdana", "Verdana"),
            ],
            value=initial_values.get("xai_font_name", "Arial"),
            width=200
        )
        
        self.dd_font_size = ft.Dropdown(
            options=[
                ft.dropdown.Option("9", "9 pt"),
                ft.dropdown.Option("10", "10 pt"),
                ft.dropdown.Option("11", "11 pt"),
                ft.dropdown.Option("12", "12 pt"),
                ft.dropdown.Option("14", "14 pt"),
                ft.dropdown.Option("16", "16 pt"),
            ],
            value=str(initial_values.get("xai_font_size", "11")),
            width=120
        )
        
        self.dd_alignment = ft.Dropdown(
            options=[
                ft.dropdown.Option("left", "À Esquerda"),
                ft.dropdown.Option("center", "Centralizado"),
                ft.dropdown.Option("right", "À Direita"),
                ft.dropdown.Option("justify", "Justificado"),
            ],
            value=initial_values.get("xai_alignment", "justify"),
            width=180
        )
        
        self.dd_line_spacing = ft.Dropdown(
            options=[
                ft.dropdown.Option("1.0", "Simples (1.0)"),
                ft.dropdown.Option("1.15", "1.15"),
                ft.dropdown.Option("1.5", "1.5"),
                ft.dropdown.Option("2.0", "Duplo (2.0)"),
            ],
            value=str(initial_values.get("xai_line_spacing", "1.15")),
            width=140
        )
        
        self.controls = [
            self.lbl_typography_title,
            ft.Row(
                controls=[
                    ft.Column([self.lbl_font, self.dd_font_name]),
                    ft.Column([self.lbl_size, self.dd_font_size]),
                    ft.Column([self.lbl_alignment, self.dd_alignment]),
                    ft.Column([self.lbl_spacing, self.dd_line_spacing]),
                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.START
            )
        ]

    def get_values(self) -> Dict[str, Any]:
        return {
            "xai_font_name": self.dd_font_name.value,
            "xai_font_size": int(self.dd_font_size.value) if self.dd_font_size.value else 11,
            "xai_alignment": self.dd_alignment.value,
            "xai_line_spacing": float(self.dd_line_spacing.value) if self.dd_line_spacing.value else 1.15,
        }

    def set_values(self, values: Dict[str, Any]):
        self.dd_font_name.value = values.get("xai_font_name", "Arial")
        self.dd_font_size.value = str(values.get("xai_font_size", "11"))
        self.dd_alignment.value = values.get("xai_alignment", "justify")
        self.dd_line_spacing.value = str(values.get("xai_line_spacing", "1.15"))

    def update_translations(self, lm: LocaleManager):
        self.lbl_typography_title.value = lm.get_string("settings_view.formatting_card.typography_title", default="Tipografia e Espaçamento")
        self.lbl_font.value = lm.get_string("settings_view.formatting_card.font_label", default="Fonte")
        self.lbl_size.value = lm.get_string("settings_view.formatting_card.size_label", default="Tamanho")
        self.lbl_alignment.value = lm.get_string("settings_view.formatting_card.alignment_label", default="Alinhamento")
        self.lbl_spacing.value = lm.get_string("settings_view.formatting_card.spacing_label", default="Espaçamento")
        
        if len(self.dd_alignment.options) >= 4:
            self.dd_alignment.options[0].text = lm.get_string("settings_view.formatting_card.alignment_left", default="À Esquerda")
            self.dd_alignment.options[1].text = lm.get_string("settings_view.formatting_card.alignment_center", default="Centralizado")
            self.dd_alignment.options[2].text = lm.get_string("settings_view.formatting_card.alignment_right", default="À Direita")
            self.dd_alignment.options[3].text = lm.get_string("settings_view.formatting_card.alignment_justify", default="Justificado")
            
        if len(self.dd_line_spacing.options) >= 4:
            self.dd_line_spacing.options[0].text = lm.get_string("settings_view.formatting_card.spacing_simple", default="Simples (1.0)")
            self.dd_line_spacing.options[1].text = "1.15"
            self.dd_line_spacing.options[2].text = "1.5"
            self.dd_line_spacing.options[3].text = lm.get_string("settings_view.formatting_card.spacing_double", default="Duplo (2.0)")
