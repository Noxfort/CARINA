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

# File: ui/widgets/semaphore_actions.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o SemaphoreActionsWidget.
"""

import flet as ft
from typing import Callable

# --- CHANGE 1: Import LocaleManager ---
from ui.handlers.locale_manager import LocaleManager

class SemaphoreActionsWidget(ft.Row):
    """
    Um widget que contém os botões de ação para um semáforo.
    """
    def __init__(
        self,
        locale_manager: LocaleManager, # <-- Receives the manager
        on_action_requested: Callable[[str], None]
    ):
        super().__init__()

        # --- CHANGE 2: Store the LocaleManager ---
        self.locale_manager = locale_manager
        self.on_action_requested = on_action_requested
        
        self.active_button: ft.ElevatedButton | None = None
        self.style_active = ft.ButtonStyle(bgcolor=ft.Colors.RED_700, side=ft.BorderSide(2, ft.Colors.WHITE))
        self.style_inactive = ft.ButtonStyle()

        self.alert_button = ft.ElevatedButton(
            icon=ft.Icons.WARNING_ROUNDED, 
            expand=True, 
            on_click=self._handle_click,
            data="ALERT",
            style=self.style_inactive
        )
        self.deactivate_button = ft.ElevatedButton(
            icon=ft.Icons.POWER_OFF_ROUNDED, 
            expand=True, 
            on_click=self._handle_click,
            data="OFF",
            style=self.style_inactive
        )

        self.controls = [self.alert_button, self.deactivate_button]

    def did_mount(self):
        """Chamado quando o widget é montado na página."""
        self.update_translations(self.locale_manager)
        if self.page: self.update()

    def _handle_click(self, e: ft.ControlEvent):
        """
        Notifica o widget pai sobre a ação solicitada.
        """
        clicked_button = e.control
        action_to_request = clicked_button.data

        if clicked_button == self.active_button:
            action_to_request = "NORMAL"
        
        if self.on_action_requested:
            self.on_action_requested(action_to_request)

    def set_active_state(self, state: str):
        """
        Define o estado visual dos botões.
        """
        self.alert_button.style = self.style_inactive
        self.deactivate_button.style = self.style_inactive
        self.active_button = None

        if state == "ALERT":
            self.alert_button.style = self.style_active
            self.active_button = self.alert_button
        elif state == "OFF":
            self.deactivate_button.style = self.style_active
            self.active_button = self.deactivate_button
        
        if self.page:
            self.update()
            
    # --- CHANGE 3: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste widget com base no LocaleManager."""
        self.alert_button.text = lm.get_string("dashboard_view.action_alert")
        self.deactivate_button.text = lm.get_string("dashboard_view.action_deactivate")
        if self.page: self.update()