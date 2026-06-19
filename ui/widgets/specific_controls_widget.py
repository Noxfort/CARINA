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

# File: ui/widgets/specific_controls_widget.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import flet as ft
from typing import Callable, Dict

from ui.handlers.locale_manager import LocaleManager
from ui.components.semaphore_info_display import SemaphoreInfoDisplayWidget
from ui.components.semaphore_actions import SemaphoreActionsWidget
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.clients.control_client import ControlClient
from ui.handlers.specific_controls_handler import SpecificControlsHandler

class SpecificControlsWidget(ft.Card):
    def __init__(
        self,
        control_client: ControlClient,
        locale_manager: LocaleManager,
        security_ui=None,
        on_close: Callable[[], None] = None,
        on_specific_command: Callable[[str, str], None] = None
    ):
        super().__init__(
            elevation=4, visible=False, animate_opacity=300
        )

        self.locale_manager = locale_manager
        self.security_ui = security_ui
        self.on_close = on_close
        self.on_specific_command = on_specific_command
        self.handler: SpecificControlsHandler | None = None
        self.control_client = control_client

        self.info_display = SemaphoreInfoDisplayWidget(locale_manager=self.locale_manager)
        self.actions = SemaphoreActionsWidget(
            locale_manager=self.locale_manager,
            on_action_requested=self._handle_action_request
        )

        # Save button removed as per request
        self.close_button = ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, on_click=self.ocultar_controles_semaforo)

        self.content = ft.Container(
            padding=10,
            content=ft.Column(
                [
                    self.info_display,
                    self.actions,
                    self.close_button,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    def did_mount(self):
        if self.page:
            dialog_manager = ConfirmationDialogManager(self.page, self.locale_manager)
            self.handler = SpecificControlsHandler(
                control_client=self.control_client,
                dialog_manager=dialog_manager,
                locale_manager=self.locale_manager,
                security_ui=self.security_ui,
                on_update_view=self.update,
                on_specific_command=self.on_specific_command
            )
        self.update_translations(self.locale_manager)
        if self.page: self.update()

    def update_translations(self, lm: LocaleManager):
        self.close_button.tooltip = lm.get_string("dashboard_view.close_panel_tooltip")
        self.info_display.update_translations(lm)
        self.actions.update_translations(lm)
        if self.page: self.update()

    def exibir_controles_semaforo(self, semaphore_id: str, semaphore_data: Dict, phase: str, mode: str):
        if not self.handler: return
        self.handler.open_for_semaphore(semaphore_id, semaphore_data)

        mode_manual_translated = self.locale_manager.get_string("dashboard_view.mode_manual")
        is_editable = True # Emergency overrides (ALERT/OFF) are always allowed

        override_state = self.handler.get_current_override_state()

        # --- MAIN CHANGE HERE ---
        # The call to update_info now includes the 'semaphore_data' argument
        self.info_display.update_info(semaphore_id, phase, semaphore_data)
        # --- END OF CHANGE ---

        self.actions.set_active_state(override_state)

        self.actions.alert_button.disabled = not is_editable
        self.actions.deactivate_button.disabled = not is_editable

        self.visible = True
        if self.page: self.update()

    def _handle_action_request(self, action: str):
        if not self.handler: return
        self.handler.request_confirmation(action)

    def _execute_and_refresh_ui(self, action: str):
        #...(internal logic remains the same)
        pass

    def ocultar_controles_semaforo(self, e=None):
        self.visible = False
        if self.page: self.update()
        if self.on_close: self.on_close()