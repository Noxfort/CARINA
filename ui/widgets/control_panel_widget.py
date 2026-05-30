# File: ui/widgets/control_panel_widget.py (FIXED TO USE ABSOLUTE IMPORTS)
# Author: Gabriel Moraes
# Date: September 29, 2025

"""
Define o widget do Painel de Controle.
"""

import flet as ft
from typing import Callable, Dict

# --- CHANGE APPLIED HERE: Using absolute imports from 'ui' ---
from ui.widgets.global_controls_widget import GlobalControlsWidget
from ui.widgets.specific_controls_widget import SpecificControlsWidget
from ui.widgets.street_info_widget import StreetInfoWidget
from ui.clients.control_client import ControlClient
from ui.handlers.locale_manager import LocaleManager
# --- END OF CHANGE ---

class ControlPanelWidget(ft.Container):
    """
    O widget que organiza os painéis de controle global e específico.
    """
    def __init__(
        self,
        control_client: ControlClient,
        locale_manager: LocaleManager,
        on_specific_command: Callable[[str, str], None] = None,
        on_details_close: Callable[[], None] = None,
        on_mode_change: Callable[[str], None] = None
    ):
        super().__init__(
            width=300,
            bgcolor=ft.Colors.BLUE_GREY_900,
            border_radius=10,
            padding=15
        )
        
        self.on_details_close = on_details_close

        self.global_controls = GlobalControlsWidget(
            control_client=control_client,
            locale_manager=locale_manager,
            on_mode_change=on_mode_change
        )
        
        self.specific_controls = SpecificControlsWidget(
            control_client=control_client,
            locale_manager=locale_manager,
            on_close=self.ocultar_todos_detalhes,
            on_specific_command=on_specific_command
        )
        
        self.street_info = StreetInfoWidget(
            locale_manager=locale_manager,
            on_close=self.ocultar_todos_detalhes
        )

        self.content = ft.Column(
            controls=[
                self.global_controls,
                self.specific_controls,
                self.street_info
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )

    def update_translations(self, lm: LocaleManager):
        """Comanda os widgets filhos a se atualizarem com o novo idioma."""
        self.global_controls.update_translations(lm)
        self.specific_controls.update_translations(lm)
        self.street_info.update_translations(lm)
        if self.page: self.update()

    def exibir_controles_semaforo(self, semaphore_id: str, semaphore_data: Dict, phase: str, mode: str):
        self.street_info.visible = False
        self.specific_controls.exibir_controles_semaforo(semaphore_id, semaphore_data, phase, mode)
        if self.page: self.update()

    def exibir_info_rua(self, street_id: str, street_data: dict):
        self.specific_controls.visible = False
        self.street_info.update_and_show(street_id, street_data)
        if self.page: self.update()

    def ocultar_todos_detalhes(self, e=None):
        self.specific_controls.visible = False
        self.street_info.visible = False
        if self.on_details_close:
            self.on_details_close()
        if self.page: self.update()