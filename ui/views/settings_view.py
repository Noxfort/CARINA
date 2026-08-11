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

# File: ui/views/settings_view.py
# Author: Gabriel Moraes
# Date: 2026-02-22

import flet as ft
from typing import Callable, List

from ui.handlers.locale_manager import LocaleManager
from ui.handlers.settings_handler import SettingsHandler
from ui.clients.settings_client import SettingsClient
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager

class SettingsView(ft.Container):
    def __init__(
        self,
        locale_manager: LocaleManager,
        settings_client: SettingsClient,
        tab_definitions: list,
        warning_text_ref: ft.Text
    ):
        super().__init__(expand=True, padding=10)

        self.locale_manager = locale_manager
        self.settings_client = settings_client
        self.tab_definitions = tab_definitions
        self.warning_text = warning_text_ref
        
        self.handler = SettingsHandler()
        self.dialog_manager: ConfirmationDialogManager | None = None
        
        # Injected properties
        self.hardware_handler = None
        self.hardware_card = None
        self.account_card = None

        # Gather all cards for polymorphic operations
        self.all_cards = []
        tab_controls = []
        for tab in self.tab_definitions:
            tab_column = ft.Column(controls=tab["cards"], spacing=15, scroll=ft.ScrollMode.ADAPTIVE)
            tab_controls.append(ft.Tab(content=tab_column, text="", icon=tab["icon"]))
            for item in tab["cards"]:
                if isinstance(item, ft.Card):
                    self.all_cards.append(item)
                    
        self.tabs = ft.Tabs(
            selected_index=0, animation_duration=300, expand=True,
            tabs=tab_controls
        )

        self.title_text = ft.Text(size=24, weight=ft.FontWeight.BOLD)
        self.save_button = ft.ElevatedButton(icon=ft.Icons.SAVE_ROUNDED, on_click=self._save_click)
        self.restore_button = ft.TextButton(icon=ft.Icons.SETTINGS_BACKUP_RESTORE, on_click=self._restore_click)

        self.content = ft.Column(
            controls=[
                ft.Row([ft.Icon(ft.Icons.SETTINGS), self.title_text]),
                self.tabs,
                ft.Row([self.restore_button, self.save_button], alignment=ft.MainAxisAlignment.END, spacing=20)
            ],
            expand=True, spacing=15
        )

    def did_mount(self):
        if self.page:
            self.dialog_manager = ConfirmationDialogManager(self.page, self.locale_manager)
            if self.hardware_handler and self.hardware_card:
                self.hardware_handler.mount(self.page, self.hardware_card)
            
            # Ensure any cards with file pickers are registered to the page overlay immediately on view mount
            for card in self.all_cards:
                if hasattr(card, "logo_file_picker") and card.logo_file_picker not in self.page.overlay:
                    self.page.overlay.append(card.logo_file_picker)
            
        self.update_translations(self.locale_manager)
        
    def update_translations(self, lm: LocaleManager):
        self.title_text.value = lm.get_string("settings_view.title")
        self.save_button.text = lm.get_string("settings_view.save_button")
        self.restore_button.text = lm.get_string("settings_view.restore_button")
        self.warning_text.value = lm.get_string("settings_view.warning_text")

        # Polymorphic update of Tabs (OCP)
        for idx, tab_spec in enumerate(self.tab_definitions):
            tab_text = lm.get_string(tab_spec["title_key"], tab_spec["default_title"])
            if tab_spec.get("is_dynamic_fallback"):
                self.tabs.tabs[idx].text = tab_text if tab_text and "!" not in tab_text else tab_spec["default_title"]
            else:
                self.tabs.tabs[idx].text = tab_text

        # Polymorphic update of Cards (OCP)
        for card in self.all_cards:
            if hasattr(card, 'update_translations'):
                card.update_translations(lm)
        
        if self.dialog_manager:
            self.dialog_manager.update_translations()
        
        if self.page: self.update()

    def _load_initial_settings(self, settings: dict = None):
        if settings is None:
            settings = self.handler.get_current_settings()
        for card in self.all_cards:
            if hasattr(card, 'set_values'):
                card.set_values(settings)
        if self.page: self.update()

    def _save_click(self, e):
        if not self.dialog_manager: return
        
        # Validation pass
        validation_failed = False
        for card in self.all_cards:
            if hasattr(card, 'validate_fields'):
                if not card.validate_fields():
                    validation_failed = True
                    if hasattr(card, 'update') and hasattr(card, 'page') and card.page:
                        card.update()
        
        if validation_failed:
            info_title = self.locale_manager.get_string("settings_view.title")
            info_content = "Erro de validação: Por favor, corrija os erros nos campos destacados antes de salvar."
            if self.locale_manager:
                info_content = self.locale_manager.get_string("settings_view.validation_error_message", default=info_content)
            self.dialog_manager.show_info(title=info_title, content=info_content)
            return

        title = self.locale_manager.get_string("dialogs.confirm_action_title")
        content = self.locale_manager.get_string("dialogs.save_settings_content")
        self.dialog_manager.show(title=title, content=content, on_confirm=self._execute_save)

    def _execute_save(self):
        if not self.page or not self.settings_client: return
        
        new_settings_values = {}
        for card in self.all_cards:
            if hasattr(card, 'get_values'):
                new_settings_values.update(card.get_values())
        
        payload_to_send = self.handler.prepare_settings_for_save(new_settings_values)
        self.settings_client.save_settings(payload_to_send)
        
        info_title = self.locale_manager.get_string("settings_view.title") 
        info_content = "As configurações foram salvas. Por favor, reinicie a aplicação para que todas as alterações tenham efeito."
        
        self.dialog_manager.show_info(title=info_title, content=info_content)
        self.page.update()

    def save_silently(self):
        if not self.settings_client: return
        new_settings_values = {}
        for card in self.all_cards:
            if hasattr(card, 'get_values'):
                new_settings_values.update(card.get_values())
        payload_to_send = self.handler.prepare_settings_for_save(new_settings_values)
        self.settings_client.save_settings(payload_to_send)

    def _restore_click(self, e):
        if not self.page: return
        default_settings = self.handler.get_default_settings()
        self._load_initial_settings(default_settings)
        self.page.snack_bar = ft.SnackBar(content=ft.Text("Configurações restauradas para os valores padrão!"))
        self.page.snack_bar.open = True
        self.page.update()
