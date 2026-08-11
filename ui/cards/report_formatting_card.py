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

# File: ui/cards/report_formatting_card.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import flet as ft
from typing import Dict, Any
from ui.handlers.locale_manager import LocaleManager
from ui.section.typography_section import TypographySection
from ui.section.margins_section import MarginsSection
from ui.section.units_section import UnitsSection
from ui.section.official_info_section import OfficialInfoSection

class ReportFormattingCard(ft.Card):
    """
    Card to customize styling, layout, and metadata for generated reports.
    Orchestrates smaller sub-widgets for typography, margins, units, and official info.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()
        
        self.initial_values = initial_values
        self.lm = None
        
        # --- UI CONTROLS ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.desc_text = ft.Text(size=12, color=ft.Colors.GREY_400)
        
        # Sub-widgets
        self.typography = TypographySection(initial_values)
        self.margins = MarginsSection(initial_values)
        self.units_section = UnitsSection(initial_values)
        self.official_info = OfficialInfoSection(initial_values)
        
        # --- STRUCTURE ---
        self.content = ft.Container(
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, size=24), self.title_text]),
                    self.desc_text,
                    ft.Divider(),
                    
                    self.typography,
                    ft.Divider(),
                    
                    self.margins,
                    ft.Divider(),
                    
                    self.units_section,
                    ft.Divider(),
                    
                    self.official_info
                ],
                spacing=15
            )
        )

    @property
    def logo_file_picker(self):
        return self.official_info.logo_file_picker

    def did_mount(self):
        if self.page and self.logo_file_picker not in self.page.overlay:
            self.page.overlay.append(self.logo_file_picker)
            self.page.update()

    def validate_fields(self) -> bool:
        # Validate child sections
        return self.official_info.validate_fields()

    def get_values(self) -> Dict[str, Any]:
        values = {}
        values.update(self.typography.get_values())
        values.update(self.margins.get_values())
        values.update(self.units_section.get_values())
        values.update(self.official_info.get_values())
        return values

    def set_values(self, values: Dict[str, Any]):
        self.typography.set_values(values)
        self.margins.set_values(values)
        self.units_section.set_values(values)
        self.official_info.set_values(values)
        if self.page:
            self.update()

    def update_translations(self, lm: LocaleManager):
        self.lm = lm
        self.title_text.value = lm.get_string("settings_view.formatting_card_title", default="Formatação e Layout dos Laudos")
        self.desc_text.value = lm.get_string("settings_view.formatting_card_desc", default="Personalize as fontes, alinhamentos, margens e informações oficiais do documento exportado.")
        
        # Delegate translation to sub-widgets
        self.typography.update_translations(lm)
        self.margins.update_translations(lm)
        self.units_section.update_translations(lm)
        self.official_info.update_translations(lm)
        
        if self.page:
            self.update()
