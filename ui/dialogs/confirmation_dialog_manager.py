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

# File: ui/dialogs/confirmation_dialog_manager.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import flet as ft
from typing import Callable

from ..handlers.locale_manager import LocaleManager

class ConfirmationDialogManager:
    """
    Gerencia a exibição de diálogos de confirmação e informativos.
    """
    def __init__(self, page: ft.Page, locale_manager: LocaleManager):
        self.page = page
        self.locale_manager = locale_manager
        self._on_confirm_callback: Callable | None = None

        self._confirm_button = ft.ElevatedButton(on_click=self._handle_confirm)
        self._cancel_button = ft.TextButton(on_click=self._handle_cancel)
        
        # --- CHANGE 1: Add a new "Close" button for informational dialogs ---
        self._close_button = ft.TextButton(on_click=self._handle_cancel)
        
        self._dialog_title_text = ft.Text(weight=ft.FontWeight.BOLD, size=24)
        
        self._content_text = ft.Text(size=16)
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER, size=30),
                self._dialog_title_text,
            ]),
            content=self._content_text,
            actions=[], # Actions will be defined dynamically
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        if self._dialog not in self.page.overlay:
            self.page.overlay.append(self._dialog)
            
        self.update_translations()

    def update_translations(self):
        self._confirm_button.text = self.locale_manager.get_string("dialogs.confirm_button")
        self._cancel_button.text = self.locale_manager.get_string("dialogs.cancel_button")
        self._close_button.text = self.locale_manager.get_string("dialogs.close_button")

    def show(self, title: str, content: str, on_confirm: Callable):
        """
        Exibe um diálogo de confirmação com dois botões (Confirmar/Cancelar).
        """
        self._on_confirm_callback = on_confirm
        
        self._dialog_title_text.value = title
        self._content_text.value = content
        
        # --- CHANGE 2: Define the actions for a confirmation dialog ---
        self._dialog.actions = [self._cancel_button, self._confirm_button]
        self._dialog.actions_alignment = ft.MainAxisAlignment.SPACE_BETWEEN
        
        self._dialog.open = True
        if self.page: self.page.update()

    # --- CHANGE 3: New method for displaying an informational dialog ---
    def show_info(self, title: str, content: str):
        """
        Exibe um diálogo informativo com apenas um botão "Fechar".
        """
        self._on_confirm_callback = None # No confirmation action
        
        self._dialog_title_text.value = title
        self._content_text.value = content
        
        # Defines the actions for an informative dialog
        self._dialog.actions = [self._close_button]
        self._dialog.actions_alignment = ft.MainAxisAlignment.END

        self._dialog.open = True
        if self.page: self.page.update()

    def _close_dialog(self):
        self._dialog.open = False
        self._on_confirm_callback = None
        if self.page: self.page.update()

    def _handle_confirm(self, e):
        if self._on_confirm_callback:
            self._on_confirm_callback()
        self._close_dialog()

    def _handle_cancel(self, e):
        self._close_dialog()