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

# File: ui/widgets/security_overlay.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import flet as ft
from typing import Callable, Optional

class SecurityUI:
    """
    Manages the Security Authentication Dialog and the Global Lockdown Overlay.
    """
    def __init__(self, page: ft.Page, control_client, locale_manager):
        self.page = page
        self.control_client = control_client
        self.locale_manager = locale_manager
        
        self.pending_action: Optional[Callable] = None
        self.attempting_username: str = ""
        self.is_locked_down = False
        
        # --- Auth Dialog Components ---
        self.username_field = ft.TextField(label=self.locale_manager.get_string("security.username", "Nome de Usuário"), autofocus=True)
        self.password_field = ft.TextField(label=self.locale_manager.get_string("security.password", "Senha"), password=True, can_reveal_password=True, on_submit=self._submit_auth)
        self.auth_error_text = ft.Text(color=ft.Colors.RED_400, visible=False)
        self.auth_progress = ft.ProgressBar(visible=False)
        
        self.auth_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.SECURITY), ft.Text(self.locale_manager.get_string("security.auth_required", "Autenticação Necessária"))]),
            content=ft.Column([
                self.username_field,
                self.password_field,
                self.auth_error_text,
                self.auth_progress
            ], tight=True),
            actions=[
                ft.TextButton(self.locale_manager.get_string("security.cancel", "Cancelar"), on_click=self._cancel_auth),
                ft.ElevatedButton(self.locale_manager.get_string("security.authenticate", "Autenticar"), on_click=self._submit_auth)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # --- Lockdown Overlay Components ---
        self.lockdown_username = ft.TextField(label=self.locale_manager.get_string("security.superuser", "Super Usuário"), bgcolor=ft.Colors.WHITE12)
        self.lockdown_password = ft.TextField(label=self.locale_manager.get_string("security.password", "Senha"), password=True, can_reveal_password=True, on_submit=self._submit_unlock, bgcolor=ft.Colors.WHITE12)
        self.lockdown_error = ft.Text(color=ft.Colors.YELLOW_400, visible=False, size=16, weight=ft.FontWeight.BOLD)
        
        self.lockdown_container = ft.Container(
            visible=False,
            expand=True,
            bgcolor=ft.Colors.RED_900,
            alignment=ft.alignment.center,
            content=ft.Column([
                ft.Icon(ft.Icons.GPP_BAD, size=100, color=ft.Colors.WHITE),
                ft.Text(self.locale_manager.get_string("security.system_locked", "SISTEMA BLOQUEADO"), size=40, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text(self.locale_manager.get_string("security.system_locked_desc1", "Muitas tentativas falhas. A infraestrutura física foi isolada."), size=20, color=ft.Colors.WHITE),
                ft.Container(height=30),
                self.lockdown_username,
                self.lockdown_password,
                self.lockdown_error,
                ft.ElevatedButton(self.locale_manager.get_string("security.unlock_system", "DESBLOQUEAR SISTEMA"), on_click=self._submit_unlock, style=ft.ButtonStyle(color=ft.Colors.RED_900, bgcolor=ft.Colors.WHITE)),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, width=400)
        )
        
        self.page.overlay.append(self.auth_dialog)
        # We add the lockdown container directly to the page as an absolute overlay
        # but Flet doesn't have a direct 'absolute' container easily, so we can use a Stack at the root or just add it to overlay if it expands.
        # Actually, if we add it to page.overlay as a Container, it might not cover everything unless it's a dialog.
        # Let's use a full-screen Dialog without padding for the Lockdown.
        
        self.lockdown_dialog = ft.AlertDialog(
            modal=True,
            content_padding=0,
            title_padding=0,
            actions_padding=0,
            bgcolor=ft.Colors.RED_900,
            content=ft.Container(
                width=10000, height=10000, # Force full screen conceptually
                alignment=ft.alignment.center,
                content=ft.Column([
                    ft.Icon(ft.Icons.GPP_BAD, size=100, color=ft.Colors.WHITE),
                    ft.Text(self.locale_manager.get_string("security.system_locked_lockdown", "SISTEMA BLOQUEADO (LOCKDOWN)"), size=40, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text(self.locale_manager.get_string("security.system_locked_desc2", "Múltiplas tentativas de acesso inválidas. Controle autônomo e conexões de hardware desligadas."), size=20, color=ft.Colors.WHITE70),
                    ft.Text(self.locale_manager.get_string("security.system_locked_desc3", "Os semáforos estão operando em seus planos locais seguros."), size=16, color=ft.Colors.WHITE70),
                    ft.Container(height=40),
                    ft.Container(
                        width=350,
                        content=ft.Column([
                            self.lockdown_username,
                            self.lockdown_password,
                            self.lockdown_error,
                            ft.Container(height=10),
                            ft.ElevatedButton(self.locale_manager.get_string("security.auth_superuser", "AUTENTICAR COMO SUPER USUÁRIO"), on_click=self._submit_unlock, 
                                            style=ft.ButtonStyle(color=ft.Colors.RED_900, bgcolor=ft.Colors.WHITE, padding=20),
                                            width=350),
                        ])
                    )
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )
        self.page.overlay.append(self.lockdown_dialog)

    def request_auth(self, on_success: Callable):
        """Opens the auth dialog and stores the callback."""
        if self.is_locked_down:
            return # Can't do normal actions while locked down
            
        self.pending_action = on_success
        self.username_field.value = ""
        self.password_field.value = ""
        self.auth_error_text.visible = False
        self.auth_progress.visible = False
        self.auth_dialog.open = True
        self.page.update()

    def _cancel_auth(self, e):
        self.pending_action = None
        self.auth_dialog.open = False
        self.page.update()

    def _submit_auth(self, e):
        username = self.username_field.value
        password = self.password_field.value
        if not username or not password:
            self.auth_error_text.value = self.locale_manager.get_string("security.err_fill_fields", "Preencha ambos os campos.")
            self.auth_error_text.visible = True
            self.page.update()
            return
            
        self.attempting_username = username
        self.auth_error_text.visible = False
        self.auth_progress.visible = True
        self.username_field.disabled = True
        self.password_field.disabled = True
        self.page.update()
        
        # Send to backend
        if self.control_client.live_data_provider:
            self.control_client.live_data_provider.send_command_to_backend({
                "type": "authenticate",
                "payload": {"username": username, "password": password}
            })

    def _submit_unlock(self, e):
        username = self.lockdown_username.value
        password = self.lockdown_password.value
        if not username or not password:
            self.lockdown_error.value = self.locale_manager.get_string("security.err_fill_fields", "Preencha ambos os campos.")
            self.lockdown_error.visible = True
            self.page.update()
            return
            
        self.attempting_username = username
        self.lockdown_error.visible = False
        self.page.update()
        
        # We use the same endpoint; backend handles unlocking if it's a super user
        if self.control_client.live_data_provider:
            self.control_client.live_data_provider.send_command_to_backend({
                "type": "authenticate",
                "payload": {"username": username, "password": password}
            })

    def handle_auth_response(self, payload: dict):
        """Called by the main loop when backend responds."""
        success = payload.get("success", False)
        
        if self.is_locked_down:
            # We are trying to unlock
            if success:
                role = payload.get("role", "")
                if role in ["SUPERUSER", "MASTER"]:
                    self.page.session.set("current_user", self.attempting_username)
                    self.is_locked_down = False
                    self.lockdown_dialog.open = False
                    self.page.update()
                    # We might want to show a toast or something
                else:
                    self.lockdown_error.value = self.locale_manager.get_string("security.err_superuser_only", "Apenas Super Usuários podem desbloquear o sistema.")
                    self.lockdown_error.visible = True
                    self.page.update()
            else:
                self.lockdown_error.value = payload.get("message", "Credenciais Inválidas")
                self.lockdown_error.visible = True
                self.page.update()
        else:
            # Normal Auth
            if success:
                self.page.session.set("current_user", self.attempting_username)
                self.auth_dialog.open = False
                self.username_field.disabled = False
                self.password_field.disabled = False
                self.page.update()
                
                # Execute the pending action!
                if self.pending_action:
                    self.pending_action()
                    self.pending_action = None
            else:
                self.auth_progress.visible = False
                self.username_field.disabled = False
                self.password_field.disabled = False
                self.auth_error_text.value = payload.get("message", "Credenciais Inválidas")
                self.auth_error_text.visible = True
                self.page.update()

    def trigger_lockdown(self):
        """Called when backend says we are in lockdown."""
        self.is_locked_down = True
        self.auth_dialog.open = False
        self.pending_action = None
        self.lockdown_username.value = ""
        self.lockdown_password.value = ""
        self.lockdown_error.visible = False
        self.lockdown_dialog.open = True
        self.page.update()
