# File: ui/widgets/global_controls_widget.py (FIXED IMPORT)
# Author: Gabriel Moraes
# Date: September 29, 2025

"""
Define o GlobalControlsWidget.
"""

import flet as ft
from typing import Callable

# --- CHANGE APPLIED HERE: Corrected the class name on import ---
from clients.control_client import ControlClient
from handlers.locale_manager import LocaleManager

class GlobalControlsWidget(ft.Card):
    """
    Um Card que contém os botões de modo global e sua lógica de interação.
    """
    def __init__(
        self, 
        control_client: ControlClient,
        locale_manager: LocaleManager,
        on_mode_change: Callable[[str], None] = None
    ):
        super().__init__(elevation=4)

        self.control_client = control_client
        self.locale_manager = locale_manager
        self.on_mode_change = on_mode_change
        
        self.active_mode_button: ft.ElevatedButton | None = None
        self.pending_button: ft.ElevatedButton | None = None
        self.style_active = ft.ButtonStyle(bgcolor=ft.Colors.INDIGO, side=ft.BorderSide(2, ft.Colors.WHITE))
        self.style_inactive = ft.ButtonStyle()

        self.dialog_title_text = ft.Text(size=30, weight=ft.FontWeight.BOLD)
        self.dialog_confirm_button = ft.ElevatedButton(on_click=self._confirm_action)
        self.dialog_cancel_button = ft.TextButton(on_click=self._cancel_action)
        
        self.confirmation_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER, size=30),
                self.dialog_title_text,
            ]),
            content=ft.Text(size=16),
            actions=[self.dialog_confirm_button, self.dialog_cancel_button],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        
        self.auto_button = ft.ElevatedButton(
            icon=ft.Icons.SMART_TOY_ROUNDED, width=270,
            on_click=self.set_active_mode, bgcolor=ft.Colors.TEAL_700,
            color=ft.Colors.WHITE, style=self.style_inactive,
            data="auto"
        )
        self.semiauto_button = ft.ElevatedButton(
            icon=ft.Icons.AUTO_MODE_ROUNDED, width=270,
            on_click=self.set_active_mode, bgcolor=ft.Colors.AMBER_700,
            color=ft.Colors.WHITE, style=self.style_inactive,
            data="semiauto"
        )
        self.manual_button = ft.ElevatedButton(
            icon=ft.Icons.EDIT_NOTE_ROUNDED, width=270,
            on_click=self.set_active_mode, bgcolor=ft.Colors.ORANGE_800,
            color=ft.Colors.WHITE, style=self.style_inactive,
            data="manual"
        )
        
        self.content = ft.Container(
            padding=10,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.GAMEPAD_ROUNDED),
                    self.title_text,
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=10),
                self.auto_button,
                self.semiauto_button,
                self.manual_button,
            ])
        )
    
    def did_mount(self):
        if self.page and self.confirmation_dialog not in self.page.overlay:
            self.page.overlay.append(self.confirmation_dialog)
        self.update_translations(self.locale_manager)
        if self.page: self.page.update()

    def set_active_mode(self, e: ft.ControlEvent):
        clicked_button = e.control
        if self.active_mode_button == clicked_button: return
        
        self.pending_button = clicked_button
        
        translated_mode_name = clicked_button.text
        template = self.locale_manager.get_string("dialogs.change_mode_content")
        self.confirmation_dialog.content.value = template.format(mode_name=translated_mode_name)
        
        self.confirmation_dialog.open = True
        if self.page: self.page.update()

    def _confirm_action(self, e: ft.ControlEvent):
        self.confirmation_dialog.open = False
        
        if self.active_mode_button:
            self.active_mode_button.style = self.style_inactive
        
        self.active_mode_button = self.pending_button
        if self.active_mode_button:
            self.active_mode_button.style = self.style_active
            
            if self.control_client:
                self.control_client.set_global_mode(self.active_mode_button.data)
            
            if self.on_mode_change:
                self.on_mode_change(self.active_mode_button.text)
        
        self.pending_button = None
        if self.page: self.page.update()

    def _cancel_action(self, e: ft.ControlEvent):
        self.confirmation_dialog.open = False
        self.pending_button = None
        if self.page: self.page.update()

    def update_translations(self, lm: LocaleManager):
        self.title_text.value = lm.get_string("dashboard_view.global_controls_title")
        self.auto_button.text = lm.get_string("dashboard_view.mode_auto")
        self.semiauto_button.text = lm.get_string("dashboard_view.mode_semiauto")
        self.manual_button.text = lm.get_string("dashboard_view.mode_manual")
        
        self.dialog_title_text.value = lm.get_string("dialogs.attention_title")
        self.dialog_confirm_button.text = lm.get_string("dialogs.confirm_button")
        self.dialog_cancel_button.text = lm.get_string("dialogs.cancel_button")

        if self.active_mode_button and self.on_mode_change:
             self.on_mode_change(self.active_mode_button.text)

        if self.page: self.page.update()

    def set_locked_state(self, is_locked: bool):
        """
        Trava ou destrava os botões de controle global baseado na maturidade da rede.
        Se travado, os botões ficam desativados e um aviso é mostrado.
        Ignora atualizações redundantes vindas do fluxo de alta frequência do WebSocket.
        """
        if getattr(self, '_last_locked_state', None) == is_locked:
            return
        self._last_locked_state = is_locked

        self.auto_button.disabled = is_locked
        self.semiauto_button.disabled = is_locked
        self.manual_button.disabled = is_locked
        
        self.title_text.value = self.locale_manager.get_string("dashboard_view.global_controls_title")
        self.title_text.color = ft.Colors.WHITE
            
        if self.page: self.page.update()