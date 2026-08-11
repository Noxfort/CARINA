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

# File: ui/builders/settings_dialog_builder.py
# Author: Gabriel Moraes
# Date: August 10, 2026

from typing import Tuple, Callable, Any
import flet as ft


class SettingsDialogBuilder:
    """
    Builder responsible for constructing the modal Settings AlertDialog and
    handling security authentication callbacks.
    """

    @staticmethod
    def build_settings_dialog(
        page: ft.Page,
        locale_manager: Any,
        security_ui: Any,
        settings_view: Any,
        settings_client: Any
    ) -> Tuple[ft.AlertDialog, Callable[[Any], None]]:
        """
        Constructs and mounts the settings modal AlertDialog on page.overlay.

        Args:
            page (ft.Page): Active Flet page instance.
            locale_manager (Any): LocaleManager instance for i18n strings.
            security_ui (Any): SecurityUI instance for requesting operator authentication.
            settings_view (Any): Settings view control component.
            settings_client (Any): SettingsClient instance for backend commands.

        Returns:
            Tuple[ft.AlertDialog, Callable]: (settings_dialog, open_settings_dialog_callback)
        """
        def close_settings_dialog(e=None):
            settings_dialog.open = False
            page.update()

        settings_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SETTINGS),
                ft.Text(locale_manager.get_string("settings_view.title", default="Configurações"))
            ]),
            content=settings_view,
            actions=[
                ft.TextButton(
                    locale_manager.get_string("dialogs.close_button", default="Fechar"),
                    on_click=close_settings_dialog
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(settings_dialog)

        def open_settings_dialog(e=None):
            def _open():
                settings_dialog.open = True
                if settings_client and hasattr(settings_client, "live_data_provider"):
                    settings_client.live_data_provider.send_command_to_backend({"type": "list_users"})
                page.update()

            if security_ui and hasattr(security_ui, "request_auth"):
                security_ui.request_auth(on_success=_open)
            else:
                _open()

        return settings_dialog, open_settings_dialog
