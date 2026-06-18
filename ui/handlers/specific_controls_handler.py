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

# File: ui/handlers/specific_controls_handler.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o SpecificControlsHandler.
"""

import logging
from typing import Callable, Dict, Any

from ui.clients.control_client import ControlClient
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.handlers.locale_manager import LocaleManager

class SpecificControlsHandler:
    """
    O 'cérebro' não-visual que gerencia a lógica para o painel de
    controles específicos de um semáforo.
    """
    def __init__(
        self,
        control_client: ControlClient,
        dialog_manager: ConfirmationDialogManager,
        locale_manager: LocaleManager, # <-- CHANGE 1: Added the parameter
        security_ui=None,
        on_update_view: Callable[[], None] = None,
        on_specific_command: Callable[[str, str], None] = None
    ):
        self.control_client = control_client
        self.dialog_manager = dialog_manager
        self.locale_manager = locale_manager # <-- CHANGE 2: Stored
        self.security_ui = security_ui
        self.on_update_view = on_update_view
        self.on_specific_command = on_specific_command

        self.current_semaphore_id: str | None = None
        self.override_states: Dict[str, str] = {}

    def open_for_semaphore(self, semaphore_id: str, semaphore_data: Dict):
        self.current_semaphore_id = semaphore_id

    def get_current_override_state(self) -> str:
        return self.override_states.get(self.current_semaphore_id, "NORMAL")

    def execute_confirmed_action(self, action: str):
        if not self.current_semaphore_id: return
        
        def _execute():
            self.override_states[self.current_semaphore_id] = action
            self.control_client.set_semaphore_override(self.current_semaphore_id, action)
            if self.on_specific_command:
                self.on_specific_command(self.current_semaphore_id, action)
            if self.on_update_view:
                self.on_update_view()
                
        if action in ["ALERT", "OFF"] and self.security_ui:
            self.security_ui.request_auth(on_success=_execute)
        else:
            _execute()



    def request_confirmation(self, action: str):
        """Usa o locale_manager para criar e exibir um diálogo traduzido."""
        if not self.current_semaphore_id: return

        action_text_map = {
            "ALERT": self.locale_manager.get_string("dialogs.specific_action_alert").format(id=self.current_semaphore_id),
            "OFF": self.locale_manager.get_string("dialogs.specific_action_off").format(id=self.current_semaphore_id),
            "NORMAL": self.locale_manager.get_string("dialogs.specific_action_normal").format(id=self.current_semaphore_id)
        }
        
        template = self.locale_manager.get_string("dialogs.confirm_specific_action_content")
        content_text = template.format(action_text=action_text_map.get(action, "..."))

        title = self.locale_manager.get_string("dialogs.confirm_action_title")

        self.dialog_manager.show(
            title=title,
            content=content_text,
            on_confirm=lambda: self.execute_confirmed_action(action)
        )