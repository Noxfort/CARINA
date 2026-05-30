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

# File: ui/main_ui.py (ORIGINAL RESTORED)
# Author: Gabriel Moraes
# Date: October 1, 2025

import sys
import os
import logging

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import flet as ft
from ui.views.dashboard_view import DashboardView
from ui.views.diagnostics_view import DiagnosticsView
from ui.views.planning_view import PlanningView
from ui.views.settings_view import SettingsView 
from ui.handlers.live_data_provider import LiveDataProvider
from ui.clients.control_client import ControlClient
from src.utils.logging_setup import setup_logging
from ui.handlers.locale_manager import LocaleManager
from ui.clients.settings_client import SettingsClient
from src.utils.paths import get_base_output_dir

def main(page: ft.Page):
    """Função principal que constrói e configura a página da aplicação Flet."""
    log_base_dir = get_base_output_dir()
    log_dir = os.path.join(log_base_dir, "logs", "ui_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    logging.info("--- O PROGRAMA DA UI INICIOU COM SUCESSO ---")
    
    locale_manager = LocaleManager()
    
    page.title = locale_manager.get_string("main_ui.app_title")
    page.window_width = 1280
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    
    caminho_do_icone = os.path.join(project_root, "ui", "assets", "images", "logo.ico")
    if not os.path.exists(caminho_do_icone):
        caminho_do_icone = os.path.join(project_root, "ui", "assets", "images", "logo.png")

    if os.path.exists(caminho_do_icone):
        page.window_favicon_path = caminho_do_icone

    live_data_provider = LiveDataProvider(on_data_received=lambda data: dashboard_view.update_live_data(data))
    control_client = ControlClient(live_data_provider=live_data_provider)
    settings_client = SettingsClient(live_data_provider=live_data_provider)

    dashboard_view = DashboardView(control_client=control_client, locale_manager=locale_manager)
    planning_view = PlanningView(locale_manager=locale_manager)
    diagnostics_view = DiagnosticsView(locale_manager=locale_manager)
    
    def apply_translations_to_ui():
        page.title = locale_manager.get_string("main_ui.app_title")
        page.appbar.title.value = locale_manager.get_string("main_ui.app_long_title")
        page.appbar.actions[0].tooltip = locale_manager.get_string("main_ui.settings_tooltip")
        
        main_tabs.tabs[0].text = locale_manager.get_string("main_ui.tab_dashboard")
        main_tabs.tabs[1].text = locale_manager.get_string("main_ui.tab_planning")
        main_tabs.tabs[2].text = locale_manager.get_string("main_ui.tab_diagnostics")

        dashboard_view.update_translations(locale_manager)
        planning_view.update_translations(locale_manager)
        diagnostics_view.update_translations(locale_manager)
        settings_view.update_translations(locale_manager)

        page.update()

    settings_view = SettingsView(
        locale_manager=locale_manager,
        settings_client=settings_client
    )
    
    def close_settings_dialog(e=None):
        settings_dialog.open = False
        page.update()

    settings_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.Icons.SETTINGS), ft.Text("Configurações")]),
        content=settings_view,
        actions=[ft.TextButton("Fechar", on_click=close_settings_dialog)],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(settings_dialog)

    def open_settings_dialog(e):
        settings_dialog.open = True
        page.update()

    # page.on_resized is hooked by LiveCanvasMapWidget for responsive map
    def handle_keyboard(e: ft.KeyboardEvent):
        if e.key == "F11":
            if hasattr(page, 'window') and page.window is not None:
                page.window.full_screen = not page.window.full_screen
            else:
                page.window_full_screen = not getattr(page, "window_full_screen", False)
            page.update()
            
    page.on_keyboard_event = handle_keyboard

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.TRAFFIC_ROUNDED),
        title=ft.Text(),
        center_title=False,
        bgcolor=ft.Colors.BLUE_GREY_800,
        actions=[ft.IconButton(ft.Icons.SETTINGS_ROUNDED, on_click=open_settings_dialog)],
    )
    
    def window_event(e):
        if hasattr(e, 'data') and e.data == "close":
            if hasattr(page, 'window') and page.window is not None:
                page.window.visible = False
            else:
                page.window_visible = False
            page.update()
            
    if hasattr(page, 'window') and page.window is not None:
        page.window.prevent_close = True
        page.window.on_event = window_event
    else:
        try:
            page.window_prevent_close = True
            page.on_window_event = window_event
        except AttributeError:
            pass # Flet version weirdness
    
    def monitor_tray():
        import time
        current_module = sys.modules[__name__]
        while True:
            if hasattr(current_module, 'restore_event') and current_module.restore_event.is_set():
                current_module.restore_event.clear()
                if hasattr(page, 'window') and page.window is not None:
                    page.window.visible = True
                else:
                    page.window_visible = True
                page.update()
            if hasattr(current_module, 'shutdown_event') and current_module.shutdown_event.is_set():
                if hasattr(page, 'window') and page.window is not None:
                    page.window.destroy()
                else:
                    page.window_destroy()
                break
            time.sleep(0.1)
            
    page.run_thread(monitor_tray)
    
    def on_disconnect(e):
        logging.info("--- O PROGRAMA DA UI FOI ENCERRADO ---")
        if live_data_provider:
            live_data_provider.stop()

    page.on_disconnect = on_disconnect
    live_data_provider.start()
    
    def on_tab_change(e):
        if e.control.selected_index == 2:
            diagnostics_view.start_log_watcher()
        else:
            diagnostics_view.stop_log_watcher()
        
        # --- NEW: If you enter the Planning tab, it loads the interactive map ---
        if e.control.selected_index == 1:
            try: planning_view.load_map()
            except: pass

    main_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        on_change=on_tab_change,
        tabs=[
            ft.Tab(icon=ft.Icons.SPACE_DASHBOARD_ROUNDED, content=dashboard_view),
            ft.Tab(icon=ft.Icons.EDIT_ROAD_ROUNDED, content=planning_view),
            ft.Tab(icon=ft.Icons.BUILD_ROUNDED, content=diagnostics_view),
        ],
        expand=True,
    )
    
    apply_translations_to_ui()
    page.add(main_tabs)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)