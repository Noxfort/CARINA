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

# File: ui/handlers/network_event_handler.py
# Author: Gabriel Moraes
# Date: July 19, 2026

import flet as ft

class NetworkEventHandler:
    """
    Orchestrator and router responsible for receiving raw real-time data from SDS
    and routing it to the appropriate UI components and views.
    """
    def __init__(self, page: ft.Page, dashboard_view, security_ui, settings_view, locale_manager):
        self.page = page
        self.dashboard_view = dashboard_view
        self.security_ui = security_ui
        self.settings_view = settings_view
        self.locale_manager = locale_manager

    def handle_sds_data(self, data: dict):
        msg_type = data.get("type")
        if msg_type == "auth_response":
            self.security_ui.handle_auth_response(data.get("payload", {}))
        elif msg_type == "lockdown_event":
            if data.get("payload", {}).get("active", False):
                self.security_ui.trigger_lockdown()
        elif msg_type == "users_list":
            if hasattr(self.settings_view, 'account_card') and self.settings_view.account_card:
                self.settings_view.account_card.update_user_list(data.get("payload", {}).get("users", []))
        elif msg_type == "account_response":
            payload = data.get("payload", {})
            action_type = payload.get("action", "")
            success = payload.get("success", False)
            if success:
                msg = self.locale_manager.get_string("accounts.success_action", "Action ({action_type}) completed successfully!").replace("{action_type}", action_type)
            else:
                msg = self.locale_manager.get_string("accounts.fail_action", "Action ({action_type}) failed. Check credentials or if the user already exists.").replace("{action_type}", action_type)
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg), 
                bgcolor=ft.Colors.GREEN_700 if success else ft.Colors.RED_700
            )
            self.page.snack_bar.open = True
            self.page.update()
        else:
            self.dashboard_view.update_live_data(data)

    def handle_hardware_trap(self, event_data: dict):
        """Displays a prominent visual toast notification in Flet when a hardware/software trap arrives."""
        try:
            intersection_id = event_data.get("intersection_id", "DESCONHECIDO")
            level = event_data.get("level", "CRITICAL")
            details = event_data.get("details") or event_data.get("message") or event_data.get("raw_message") or "Alerta do controlador"
            
            if details.startswith("[") and "]" in details:
                clean_display = str(details)
            elif intersection_id and intersection_id != "DESCONHECIDO":
                clean_display = f"[Cruzamento {intersection_id}] {details}"
            else:
                clean_display = str(details)

            bg = ft.Colors.RED_800 if str(level).upper() == "CRITICAL" else ft.Colors.ORANGE_800
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.WHITE, size=24),
                        ft.Text(clean_display, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                    ],
                    spacing=10
                ),
                bgcolor=bg,
                duration=5000
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as e:
            pass
