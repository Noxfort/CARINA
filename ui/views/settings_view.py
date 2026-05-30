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

# File: ui/views/settings_view.py
# Author: Gabriel Moraes
# Date: 2026-02-22

import flet as ft
from typing import Callable, List

from ui.handlers.locale_manager import LocaleManager
from ui.handlers.settings_handler import SettingsHandler
from ui.clients.settings_client import SettingsClient
from ui.widgets.general_settings_card import GeneralSettingsCard
from ui.widgets.traffic_rules_card import TrafficRulesCard
from ui.widgets.dashboard_settings_card import DashboardSettingsCard
from ui.widgets.advanced_ppo_card import AdvancedPPOCard
from ui.widgets.advanced_dqn_card import AdvancedDQNCard
from ui.widgets.advanced_system_card import AdvancedSystemCard
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.widgets.piloting_school_card import PilotingSchoolCard
from ui.widgets.reward_weights_card import RewardWeightsCard
from ui.widgets.monitor_settings_card import MonitorSettingsCard
from ui.widgets.database_settings_card import DatabaseSettingsCard

# --- HARDWARE IMPORTS ---
from ui.widgets.hardware_connection_card import HardwareConnectionCard
from src.controller.connection_manager import HardwareConnectionManager

class SettingsView(ft.Container):
    def __init__(
        self,
        locale_manager: LocaleManager,
        settings_client: SettingsClient,
    ):
        super().__init__(expand=True, padding=10)

        self.locale_manager = locale_manager
        self.settings_client = settings_client
        
        self.handler = SettingsHandler()
        initial_settings = self.handler.get_current_settings()
        
        self.dialog_manager: ConfirmationDialogManager | None = None

        # Hardware Backend Initialization (Auto-discover intersections)
        self.connection_manager = HardwareConnectionManager()

        # File Pickers
        self.import_picker = ft.FilePicker(on_result=self._on_import_result)
        self.export_picker = ft.FilePicker(on_result=self._on_export_result)

        # Existing Cards
        self.general_card = GeneralSettingsCard(initial_settings)
        self.traffic_rules_card = TrafficRulesCard(initial_settings)
        self.dashboard_card = DashboardSettingsCard(initial_settings)
        self.advanced_ppo_card = AdvancedPPOCard(initial_settings)
        self.advanced_dqn_card = AdvancedDQNCard(initial_settings)
        self.advanced_system_card = AdvancedSystemCard(initial_settings)
        self.piloting_school_card = PilotingSchoolCard(initial_settings)
        self.reward_weights_card = RewardWeightsCard(initial_settings)
        self.monitor_card = MonitorSettingsCard(
            initial_values=initial_settings,
            on_toggle_connection=self._on_monitor_toggle
        )
        self.db_card = DatabaseSettingsCard(
            initial_values=initial_settings,
            on_toggle_connection=self._on_db_toggle
        )

        # Hardware Card
        self.hardware_card = HardwareConnectionCard(
            on_import_click=self._on_hardware_import_click,
            on_export_click=self._on_hardware_export_click,
            on_toggle_connection=self._on_hardware_toggle
        )

        self.card_widgets = [
            self.general_card, self.db_card, self.traffic_rules_card, self.dashboard_card,
            self.advanced_ppo_card, self.advanced_dqn_card, self.advanced_system_card,
            self.piloting_school_card, self.reward_weights_card, self.monitor_card
        ]

        self.title_text = ft.Text(size=24, weight=ft.FontWeight.BOLD)
        self.save_button = ft.ElevatedButton(icon=ft.Icons.SAVE_ROUNDED, on_click=self._save_click)
        self.restore_button = ft.TextButton(icon=ft.Icons.SETTINGS_BACKUP_RESTORE, on_click=self._restore_click)
        self.warning_text = ft.Text(size=12, expand=True, italic=True)

        # Tab Contents
        general_tab_content = ft.Column(
            controls=[self.general_card, self.db_card, self.traffic_rules_card, self.dashboard_card], 
            spacing=15, scroll=ft.ScrollMode.ADAPTIVE
        )

        advanced_tab_content = ft.Column(
            controls=[
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.AMBER), 
                    border=ft.border.all(1, ft.Colors.AMBER),
                    border_radius=10, padding=15,
                    content=ft.Row([
                        ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.AMBER),
                        self.warning_text
                    ])
                ),
                self.advanced_ppo_card, self.advanced_dqn_card,
                self.piloting_school_card, self.reward_weights_card,
                self.advanced_system_card,
            ], 
            spacing=15, scroll=ft.ScrollMode.ADAPTIVE
        )

        hardware_tab_content = ft.Column(
            controls=[self.hardware_card],
            spacing=15, scroll=ft.ScrollMode.ADAPTIVE
        )
        
        monitor_tab_content = ft.Column(
            controls=[self.monitor_card],
            spacing=15, scroll=ft.ScrollMode.ADAPTIVE
        )
        
        self.content = ft.Column(
            controls=[
                ft.Row([ft.Icon(ft.Icons.SETTINGS), self.title_text]),
                ft.Tabs(
                    selected_index=0, animation_duration=300, expand=True,
                    tabs=[
                        ft.Tab(content=general_tab_content, text="", icon=ft.Icons.TUNE_ROUNDED),
                        ft.Tab(content=advanced_tab_content, text="", icon=ft.Icons.HUB_ROUNDED),
                        ft.Tab(content=hardware_tab_content, text="", icon=ft.Icons.CABLE_ROUNDED),
                        ft.Tab(content=monitor_tab_content, text="", icon=ft.Icons.MONITOR_HEART_ROUNDED),
                    ],
                ),
                ft.Row([self.restore_button, self.save_button], alignment=ft.MainAxisAlignment.END, spacing=20)
            ],
            expand=True, spacing=15
        )

    def did_mount(self):
        if self.page:
            self.dialog_manager = ConfirmationDialogManager(self.page, self.locale_manager)
            
            # Add file pickers to the page overlay
            self.page.overlay.extend([self.import_picker, self.export_picker])
            
            # Initial hardware UI load from backend
            self._refresh_hardware_ui()
            
        self.update_translations(self.locale_manager)
        
    def update_translations(self, lm: LocaleManager):
        self.title_text.value = lm.get_string("settings_view.title")
        self.content.controls[1].tabs[0].text = lm.get_string("settings_view.tab_general")
        self.content.controls[1].tabs[1].text = lm.get_string("settings_view.tab_advanced")
        
        hardware_tab_text = lm.get_string("settings_view.tab_hardware")
        monitor_tab_text = lm.get_string("settings_view.tab_monitor")
        
        self.content.controls[1].tabs[2].text = hardware_tab_text if hardware_tab_text and "!" not in hardware_tab_text else "Hardware"
        self.content.controls[1].tabs[3].text = monitor_tab_text if monitor_tab_text and "!" not in monitor_tab_text else "Monitor"

        self.save_button.text = lm.get_string("settings_view.save_button")
        self.restore_button.text = lm.get_string("settings_view.restore_button")
        self.warning_text.value = lm.get_string("settings_view.warning_text")

        for card in self.card_widgets:
            if hasattr(card, 'update_translations'):
                card.update_translations(lm)
                
        if hasattr(self, 'hardware_card') and hasattr(self.hardware_card, 'update_translations'):
            self.hardware_card.update_translations(lm)
        
        if self.dialog_manager:
            self.dialog_manager.update_translations()
        
        if self.page: self.update()

    def _load_initial_settings(self, settings: dict = None):
        if settings is None:
            settings = self.handler.get_current_settings()
        for card in self.card_widgets:
            card.set_values(settings)
        if self.page: self.update()

    def _save_click(self, e):
        if not self.dialog_manager: return
        title = self.locale_manager.get_string("dialogs.confirm_action_title")
        content = self.locale_manager.get_string("dialogs.save_settings_content")
        self.dialog_manager.show(title=title, content=content, on_confirm=self._execute_save)

    def _execute_save(self):
        if not self.page or not self.settings_client: return
        
        new_settings_values = {}
        for card in self.card_widgets:
            new_settings_values.update(card.get_values())
        
        payload_to_send = self.handler.prepare_settings_for_save(new_settings_values)
        self.settings_client.save_settings(payload_to_send)
        
        info_title = self.locale_manager.get_string("settings_view.title") 
        info_content = "As configurações foram salvas. Por favor, reinicie a aplicação para que todas as alterações tenham efeito."
        
        self.dialog_manager.show_info(title=info_title, content=info_content)
        self.page.update()

    def _restore_click(self, e):
        if not self.page: return
        default_settings = self.handler.get_default_settings()
        self._load_initial_settings(default_settings)
        self.page.snack_bar = ft.SnackBar(content=ft.Text("Configurações restauradas para os valores padrão!"))
        self.page.snack_bar.open = True
        self.page.update()

    # --- MONITOR CONNECTION HANDLER ---
    def _on_monitor_toggle(self, enabled: bool, host: str):
        if self.settings_client and self.settings_client.live_data_provider:
            command = {
                "type": "set_monitor_connection",
                "payload": {"enabled": enabled, "host": host}
            }
            self.settings_client.live_data_provider.send_command_to_backend(command)

    def _on_db_toggle(self, is_connected: bool):
        """Silently auto-saves configuration when the database is successfully connected/disconnected."""
        if not self.settings_client: return
        new_settings_values = {}
        for card in self.card_widgets:
            new_settings_values.update(card.get_values())
        payload_to_send = self.handler.prepare_settings_for_save(new_settings_values)
        self.settings_client.save_settings(payload_to_send)

    # --- HARDWARE CONNECTION REAL HANDLERS ---
    
    def _refresh_hardware_ui(self):
        """Updates the Hardware Card using data from the Connection Manager."""
        ui_data = self.connection_manager.get_ui_status_list()
        self.hardware_card.load_agents_data(ui_data)

    def _on_hardware_import_click(self, e):
        self.import_picker.pick_files(
            dialog_title="Select Configuration CSV",
            allowed_extensions=["csv"]
        )

    def _on_import_result(self, e):
        if e.files and len(e.files) > 0:
            filepath = e.files[0].path
            # The manager now attempts to connect to all imported IPs automatically
            success_count, total = self.connection_manager.import_csv_config(filepath)
            self._refresh_hardware_ui()
            
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Importação concluída: {success_count} de {total} semáforos ligados com sucesso.")
                )
                self.page.snack_bar.open = True
                self.page.update()

    def _on_hardware_export_click(self, e):
        self.export_picker.save_file(
            dialog_title="Save Template CSV",
            file_name="carina_hardware_template.csv",
            allowed_extensions=["csv"]
        )

    def _on_export_result(self, e):
        if e.path:
            success = self.connection_manager.export_csv_template(e.path)
            if self.page:
                msg = "Template exportado com sucesso!" if success else "Erro ao exportar template."
                self.page.snack_bar = ft.SnackBar(content=ft.Text(msg))
                self.page.snack_bar.open = True
                self.page.update()

    def _on_hardware_toggle(self, intersection_id: str, ip_address: str):
        # Passes both the ID and the IP currently written in the text field
        self.connection_manager.toggle_connection(intersection_id, ip_address)
        self._refresh_hardware_ui()
