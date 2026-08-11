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

# File: ui/managers/navigation_manager.py
# Author: Gabriel Moraes
# Date: August 10, 2026

from typing import Any, Callable
import flet as ft


class NavigationManager:
    """
    Manages top-level application navigation, AppBar, Tab switching events,
    and centralized UI translation updates.
    """

    def __init__(
        self,
        page: ft.Page,
        locale_manager: Any,
        dashboard_view: Any,
        planning_view: Any,
        diagnostics_view: Any,
        settings_view: Any,
        settings_dialog: ft.AlertDialog,
        open_settings_callback: Callable[[Any], None]
    ):
        self.page = page
        self.locale_manager = locale_manager
        self.dashboard_view = dashboard_view
        self.planning_view = planning_view
        self.diagnostics_view = diagnostics_view
        self.settings_view = settings_view
        self.settings_dialog = settings_dialog
        self.open_settings_callback = open_settings_callback

        self.appbar = self._build_appbar()
        self.tabs = self._build_tabs()

    def _build_appbar(self) -> ft.AppBar:
        """Constructs the application top AppBar."""
        return ft.AppBar(
            leading=ft.Icon(ft.Icons.TRAFFIC_ROUNDED),
            title=ft.Text(self.locale_manager.get_string("main_ui.app_long_title", default="CARINA CORE")),
            center_title=False,
            bgcolor=ft.Colors.BLUE_GREY_800,
            actions=[
                ft.IconButton(
                    ft.Icons.SETTINGS_ROUNDED,
                    on_click=self.open_settings_callback,
                    tooltip=self.locale_manager.get_string("main_ui.settings_tooltip", default="Configurações")
                ),
            ],
        )

    def _build_tabs(self) -> ft.Tabs:
        """Constructs application navigation Tabs and binds tab selection events."""
        def on_tab_change(e):
            if e.control.selected_index == 2:
                if hasattr(self.diagnostics_view, "start_log_watcher"):
                    self.diagnostics_view.start_log_watcher()
            else:
                if hasattr(self.diagnostics_view, "stop_log_watcher"):
                    self.diagnostics_view.stop_log_watcher()

            if e.control.selected_index == 1:
                try:
                    if hasattr(self.planning_view, "load_map"):
                        self.planning_view.load_map()
                except Exception:
                    pass

        return ft.Tabs(
            selected_index=0,
            animation_duration=300,
            on_change=on_tab_change,
            tabs=[
                ft.Tab(
                    text=self.locale_manager.get_string("main_ui.tab_dashboard", default="Painel"),
                    icon=ft.Icons.SPACE_DASHBOARD_ROUNDED,
                    content=self.dashboard_view
                ),
                ft.Tab(
                    text=self.locale_manager.get_string("main_ui.tab_planning", default="Planejamento"),
                    icon=ft.Icons.EDIT_ROAD_ROUNDED,
                    content=self.planning_view
                ),
                ft.Tab(
                    text=self.locale_manager.get_string("main_ui.tab_diagnostics", default="Diagnósticos"),
                    icon=ft.Icons.BUILD_ROUNDED,
                    content=self.diagnostics_view
                ),
            ],
            expand=True,
        )

    def apply_translations(self) -> None:
        """Applies updated localized strings across AppBar, Page titles, Tabs, and Views."""
        self.page.title = self.locale_manager.get_string("main_ui.app_title", default="CARINA")
        self.appbar.title.value = self.locale_manager.get_string("main_ui.app_long_title", default="CARINA CORE")
        self.appbar.actions[0].tooltip = self.locale_manager.get_string("main_ui.settings_tooltip", default="Configurações")

        self.tabs.tabs[0].text = self.locale_manager.get_string("main_ui.tab_dashboard", default="Painel")
        self.tabs.tabs[1].text = self.locale_manager.get_string("main_ui.tab_planning", default="Planejamento")
        self.tabs.tabs[2].text = self.locale_manager.get_string("main_ui.tab_diagnostics", default="Diagnósticos")

        if hasattr(self.dashboard_view, "update_translations"):
            self.dashboard_view.update_translations(self.locale_manager)
        if hasattr(self.planning_view, "update_translations"):
            self.planning_view.update_translations(self.locale_manager)
        if hasattr(self.diagnostics_view, "update_translations"):
            self.diagnostics_view.update_translations(self.locale_manager)
        if hasattr(self.settings_view, "update_translations"):
            self.settings_view.update_translations(self.locale_manager)

        if self.settings_dialog and hasattr(self.settings_dialog, "title"):
            if len(self.settings_dialog.title.controls) > 1:
                self.settings_dialog.title.controls[1].value = self.locale_manager.get_string("settings_view.title", default="Configurações")
        if self.settings_dialog and hasattr(self.settings_dialog, "actions"):
            if len(self.settings_dialog.actions) > 0:
                self.settings_dialog.actions[0].text = self.locale_manager.get_string("dialogs.close_button", default="Fechar")

        self.page.update()
