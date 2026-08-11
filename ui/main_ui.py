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

# File: ui/main_ui.py (Refactored to Pure UI Orchestrator)
# Author: Gabriel Moraes
# Date: July 19, 2026

import sys
import os
import logging
import traceback

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
from ui.views.error_view import ErrorView
from ui.builders.settings_configurator import build_settings_view
from ui.builders.settings_dialog_builder import SettingsDialogBuilder
from ui.providers.live_data_provider import LiveDataProvider
from ui.clients.control_client import ControlClient
from ui.clients.settings_client import SettingsClient
from ui.handlers.locale_manager import LocaleManager
from ui.handlers.network_event_handler import NetworkEventHandler
from ui.managers.window_manager import WindowManager
from ui.managers.navigation_manager import NavigationManager
from ui.overlays.security_overlay import SecurityUI
from src.utils.logging_setup import setup_logging
from src.utils.paths import get_base_output_dir

sas_result_queue = None
mfd_result_queue = None
mfd_trigger_queue = None


def main(page: ft.Page):
    """Main function configuring and assembling the Flet application UI."""
    global active_page
    active_page = page

    try:
        # 1. Logging Initialization
        log_base_dir = get_base_output_dir()
        log_dir = os.path.join(log_base_dir, "logs", "ui_worker")
        os.makedirs(log_dir, exist_ok=True)
        setup_logging(log_dir=log_dir)

        logging.info("--- O PROGRAMA DA UI INICIOU COM SUCESSO ---")

        locale_manager = LocaleManager()

        # 2. Background Hardware & Monitor Client Initialization
        hw_manager = None
        try:
            from src.controller.connection_manager import HardwareConnectionManager
            hw_manager = HardwareConnectionManager.get_instance(locale_manager=locale_manager)
        except Exception as err:
            logging.warning(f"[main_ui] Non-critical warning initializing HardwareConnectionManager: {err}")

        try:
            from src.utils.settings_manager import SettingsManager
            from src.communication.monitor_client import MonitorClient
            MonitorClient.get_instance(SettingsManager())
        except Exception as err:
            logging.warning(f"[main_ui] Non-critical warning initializing MonitorClient: {err}")

        # 3. Window Manager Configuration
        current_module = sys.modules[__name__]
        restore_ev = getattr(current_module, 'restore_event', None)
        shutdown_ev = getattr(current_module, 'shutdown_event', None)

        window_manager = WindowManager(page, restore_event=restore_ev, shutdown_event=shutdown_ev)

        caminho_do_icone = os.path.join(project_root, "ui", "assets", "images", "logo.ico")
        if not os.path.exists(caminho_do_icone):
            caminho_do_icone = os.path.join(project_root, "ui", "assets", "images", "logo.png")

        window_manager.configure_window(
            app_title=locale_manager.get_string("main_ui.app_title", default="CARINA"),
            favicon_path=caminho_do_icone
        )

        # 4. Clients, Providers and Security Setup
        live_data_provider = LiveDataProvider(
            on_data_received=lambda data: net_event_handler.handle_sds_data(data),
            shutdown_event=shutdown_ev
        )
        control_client = ControlClient(live_data_provider=live_data_provider)
        settings_client = SettingsClient(live_data_provider=live_data_provider)
        security_ui = SecurityUI(page, control_client, locale_manager)

        # 5. Views Assembly
        dashboard_view = DashboardView(control_client=control_client, locale_manager=locale_manager, security_ui=security_ui)
        planning_view = PlanningView(locale_manager=locale_manager, control_client=control_client, sas_result_queue=sas_result_queue)
        diagnostics_view = DiagnosticsView(locale_manager=locale_manager, control_client=control_client)
        settings_view = build_settings_view(locale_manager, settings_client)

        # 6. Network Event Handler Setup
        net_event_handler = NetworkEventHandler(
            page=page,
            dashboard_view=dashboard_view,
            security_ui=security_ui,
            settings_view=settings_view,
            locale_manager=locale_manager
        )

        if hw_manager and hasattr(hw_manager, "event_listener") and hw_manager.event_listener:
            hw_manager.event_listener.on_event_callback = lambda evt: net_event_handler.handle_hardware_trap(evt)

        # 7. Modal Settings Dialog Setup
        settings_dialog, open_settings_dialog = SettingsDialogBuilder.build_settings_dialog(
            page=page,
            locale_manager=locale_manager,
            security_ui=security_ui,
            settings_view=settings_view,
            settings_client=settings_client
        )

        # 8. Navigation & Tab Manager Setup
        nav_manager = NavigationManager(
            page=page,
            locale_manager=locale_manager,
            dashboard_view=dashboard_view,
            planning_view=planning_view,
            diagnostics_view=diagnostics_view,
            settings_view=settings_view,
            settings_dialog=settings_dialog,
            open_settings_callback=open_settings_dialog
        )

        page.appbar = nav_manager.appbar

        def on_disconnect(e):
            logging.info("--- O PROGRAMA DA UI FOI ENCERRADO ---")
            if shutdown_ev:
                shutdown_ev.set()
            if live_data_provider:
                live_data_provider.stop()
            try:
                from src.communication.monitor_client import MonitorClient
                mon = MonitorClient.get_instance()
                if mon and mon.enabled and mon.client:
                    mon.stop(shutdown_message="Operador encerrou a interface da CARINA_CORE")
            except Exception as err:
                logging.error(f"[main_ui] Exception sending Monitor shutdown message: {err}")

        page.on_disconnect = on_disconnect
        live_data_provider.start()

        page.add(nav_manager.tabs)
        nav_manager.apply_translations()
        page.update()

    except Exception as err:
        error_msg = traceback.format_exc()
        logging.error(f"[main_ui] Erro crítico na inicialização da UI: {err}\n{error_msg}")
        ErrorView.render_error_card(page, error_msg, on_restart_callback=lambda e: main(page))


if __name__ == "__main__":
    ft.app(target=main)