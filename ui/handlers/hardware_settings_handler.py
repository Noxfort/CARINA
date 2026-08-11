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

# File: ui/handlers/hardware_settings_handler.py
# Author: Gabriel Moraes
# Date: 2026-06-10

import flet as ft
from src.controller.connection_manager import HardwareConnectionManager

class HardwareSettingsHandler:
    """
    SRP: Manages all business logic related to Hardware configuration,
    including CSV spreadsheet import/export and connection toggles.
    """
    def __init__(self, connection_manager: HardwareConnectionManager, settings_client=None):
        self.connection_manager = connection_manager
        self.settings_client = settings_client
        self.page = None
        self.hardware_card = None

        self.import_picker = ft.FilePicker(on_result=self._on_import_result)
        self.export_picker = ft.FilePicker(on_result=self._on_export_result)

    def mount(self, page: ft.Page, hardware_card):
        self.page = page
        self.hardware_card = hardware_card
        self.page.overlay.extend([self.import_picker, self.export_picker])
        self.refresh_ui()

    def refresh_ui(self):
        """Updates the visual component (Hardware Card) using data from the Connection Manager."""
        if self.hardware_card:
            ui_data = self.connection_manager.get_ui_status_list()
            self.hardware_card.load_agents_data(ui_data)

    def on_import_click(self, e):
        self.import_picker.pick_files(
            dialog_title="Select Configuration CSV",
            allowed_extensions=["csv"]
        )

    def _on_import_result(self, e):
        if e.files and len(e.files) > 0:
            filepath = e.files[0].path
            success_count, total = self.connection_manager.import_csv_config(filepath)
            self.refresh_ui()
            
            if self.settings_client:
                for tl_id, ip in self.connection_manager.saved_ips.items():
                    if tl_id in self.connection_manager.active_connections:
                        self.settings_client.send_command("set_hardware_connection", {"intersection_id": tl_id, "ip_address": ip})
            
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Import complete: {success_count} out of {total} traffic lights connected successfully.")
                )
                self.page.snack_bar.open = True
                self.page.update()

    def on_export_click(self, e):
        self.export_picker.save_file(
            dialog_title="Save Template CSV",
            file_name="carina_hardware_template.csv",
            allowed_extensions=["csv"]
        )

    def _on_export_result(self, e):
        if e.path:
            success = self.connection_manager.export_csv_template(e.path)
            if self.page:
                msg = "Template exported successfully!" if success else "Error exporting template."
                self.page.snack_bar = ft.SnackBar(content=ft.Text(msg))
                self.page.snack_bar.open = True
                self.page.update()

    def on_toggle_connection(self, intersection_id: str, ip_address: str, action: str = "toggle"):
        self.connection_manager.toggle_connection(intersection_id, ip_address, action=action)
        self.refresh_ui()
        if self.settings_client:
            self.settings_client.send_command("set_hardware_connection", {"intersection_id": intersection_id, "ip_address": ip_address, "action": action})
