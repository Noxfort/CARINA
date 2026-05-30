# File: ui/widgets/specific_controls_widget.py (FIXED FUNCTION CALL)
# Author: Gabriel Moraes
# Date: September 29, 2025

import flet as ft
from typing import Callable, Dict

from ui.handlers.locale_manager import LocaleManager
from ui.widgets.semaphore_info_display import SemaphoreInfoDisplayWidget
from ui.widgets.semaphore_actions import SemaphoreActionsWidget
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.clients.control_client import ControlClient
from ui.handlers.specific_controls_handler import SpecificControlsHandler

class SpecificControlsWidget(ft.Card):
    def __init__(
        self,
        control_client: ControlClient,
        locale_manager: LocaleManager,
        on_close: Callable[[], None] = None,
        on_specific_command: Callable[[str, str], None] = None
    ):
        super().__init__(
            elevation=4, visible=False, animate_opacity=300
        )

        self.locale_manager = locale_manager
        self.on_close = on_close
        self.on_specific_command = on_specific_command
        self.handler: SpecificControlsHandler | None = None
        self.control_client = control_client

        self.info_display = SemaphoreInfoDisplayWidget(locale_manager=self.locale_manager)
        self.actions = SemaphoreActionsWidget(
            locale_manager=self.locale_manager,
            on_action_requested=self._handle_action_request
        )

        self.save_button = ft.ElevatedButton(icon=ft.Icons.SAVE_ROUNDED, on_click=self._save_timings, visible=False)
        self.close_button = ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, on_click=self.ocultar_controles_semaforo)

        self.content = ft.Container(
            padding=10,
            content=ft.Column(
                [
                    self.info_display,
                    self.actions,
                    self.save_button,
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
                on_update_view=self.update,
                on_specific_command=self.on_specific_command
            )
        self.update_translations(self.locale_manager)
        if self.page: self.update()

    def update_translations(self, lm: LocaleManager):
        self.save_button.text = lm.get_string("dashboard_view.save_timings_button")
        self.close_button.tooltip = lm.get_string("dashboard_view.close_panel_tooltip")
        self.info_display.update_translations(lm)
        self.actions.update_translations(lm)
        if self.page: self.update()

    def exibir_controles_semaforo(self, semaphore_id: str, semaphore_data: Dict, phase: str, mode: str):
        if not self.handler: return
        self.handler.open_for_semaphore(semaphore_id, semaphore_data)

        mode_manual_translated = self.locale_manager.get_string("dashboard_view.mode_manual")
        is_editable = (mode.lower() == mode_manual_translated.lower() and phase.upper() == 'ADULTO')

        display_timings = self.handler.get_current_timings()
        override_state = self.handler.get_current_override_state()

        # --- MAIN CHANGE HERE ---
        # The call to update_info now includes the 'semaphore_data' argument
        self.info_display.update_info(semaphore_id, phase, semaphore_data)
        # --- END OF CHANGE ---

        self.info_display.green_time_field.value = display_timings["green"]
        self.info_display.yellow_time_field.value = display_timings["yellow"]
        self.actions.set_active_state(override_state)

        self.info_display.green_time_field.read_only = not is_editable
        self.info_display.yellow_time_field.read_only = not is_editable

        border_color = ft.Colors.CYAN_400 if is_editable else None
        self.info_display.green_time_field.border_color = border_color
        self.info_display.yellow_time_field.border_color = border_color

        self.actions.alert_button.disabled = not is_editable
        self.actions.deactivate_button.disabled = not is_editable
        self.save_button.visible = is_editable

        self.visible = True
        if self.page: self.update()

    def _save_timings(self, e):
        #...(internal logic remains the same)
        pass

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