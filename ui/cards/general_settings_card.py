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

# File: ui/widgets/general_settings_card.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o GeneralSettingsCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager

class GeneralSettingsCard(ft.Card):
    """
    Um Card que encapsula as configurações de aparência e gerais.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.check_theme = ft.Checkbox(
            value=initial_values.get('theme_dark', True),
            on_change=self._theme_changed
        )
        self.dd_language = ft.Dropdown(
            options=[
                ft.dropdown.Option("pt_br", "Português (Brasil)"),
                ft.dropdown.Option("en_us", "English"),
                ft.dropdown.Option("es_es", "Español"),
                ft.dropdown.Option("fr_fr", "Français"),
                ft.dropdown.Option("ru_ru", "Русский"),
                ft.dropdown.Option("zh_cn", "中文"),
            ],
            value=initial_values.get('language', 'pt_br')
        )
        
        # --- System Info ---
        self.lbl_system_info = ft.Text(weight=ft.FontWeight.BOLD, size=14)
        self.txt_version = ft.Text(size=12)
        self.txt_codename = ft.Text(size=12)
        
        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text, # The text will be filled in via update_translations
                ft.Divider(),
                self.check_theme, # The label will be populated via update_translations
                self.dd_language,  # The label will be populated via update_translations
                ft.Divider(),
                self.lbl_system_info,
                ft.Row([
                    ft.Icon(ft.Icons.INFO_ROUNDED, color=ft.Colors.BLUE_400, size=20),
                    ft.Column([
                        self.txt_version,
                        self.txt_codename
                    ], spacing=2)
                ], alignment=ft.MainAxisAlignment.START, spacing=10)
            ])
        )

    def _theme_changed(self, e: ft.ControlEvent):
        """
        Chamado quando o checkbox do modo escuro é alterado.
        """
        if self.page:
            self.page.theme_mode = ft.ThemeMode.DARK if e.control.value else ft.ThemeMode.LIGHT
            self.page.update()

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'theme_dark': self.check_theme.value,
            'language': self.dd_language.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.check_theme.value = values.get('theme_dark', True)
        self.dd_language.value = values.get('language', 'pt_br')
        if self.page: self.update()
        
    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.general_card_title", default="Configurações Gerais")
        self.check_theme.label = lm.get_string("settings_view.dark_mode_label", default="Modo Escuro")
        self.dd_language.label = lm.get_string("settings_view.language_label", default="Idioma")
        
        self.lbl_system_info.value = lm.get_string("settings_view.system_info_title", default="Informações do Sistema")
        version_label = lm.get_string("settings_view.version_label", default="Versão")
        codename_label = lm.get_string("settings_view.codename_label", default="Codinome")
        
        self.txt_version.value = f"{version_label}: 1.0.1"
        self.txt_codename.value = f"{codename_label}: Itaquera"
        
        if self.page: self.update()