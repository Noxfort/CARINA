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

# File: ui/widgets/hardware_connection_card.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
Hardware Connection UI Widget.
Provides a tabular interface for linking CARINA agents directly to their 
physical controller (NTCIP/UTMC2) using inline IP Address inputs.
"""

import logging
import flet as ft
from typing import List, Dict

logger = logging.getLogger(__name__)

class HardwareConnectionCard(ft.Card):
    def __init__(self, on_import_click=None, on_export_click=None, on_toggle_connection=None):
        super().__init__()
        self.elevation = 2
        self.expand = True  
        
        # Callbacks to the backend/controller
        self.on_import_click = on_import_click
        self.on_export_click = on_export_click
        self.on_toggle_connection = on_toggle_connection

        self.lm = None
        self.last_agents_list = []

        # Dictionary to keep track of the IP text fields for each intersection row
        self.ip_fields: Dict[str, ft.TextField] = {}
        
        # Translatable explicit widgets
        self.col_id_text = ft.Text("Intersection ID", weight=ft.FontWeight.BOLD)
        self.col_ip_text = ft.Text("IP Address", weight=ft.FontWeight.BOLD)
        self.col_status_text = ft.Text("Status", weight=ft.FontWeight.BOLD)
        self.col_action_text = ft.Text("Action", weight=ft.FontWeight.BOLD)
        
        self.title_text = ft.Text("Hardware Connections", size=20, weight=ft.FontWeight.BOLD)
        self.btn_export = ft.ElevatedButton(text="Export Template", icon=ft.icons.DOWNLOAD, on_click=self._handle_export)
        self.btn_import = ft.ElevatedButton(text="Import Config", icon=ft.icons.UPLOAD, on_click=self._handle_import)

        # UI Components - Enhanced DataTable Styling
        self.table = ft.DataTable(
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=8,
            heading_row_color=ft.colors.SURFACE_VARIANT,
            horizontal_margin=20,
            column_spacing=40,
            columns=[
                ft.DataColumn(self.col_id_text),
                ft.DataColumn(self.col_ip_text),
                ft.DataColumn(self.col_status_text),
                ft.DataColumn(self.col_action_text),
            ],
            rows=[]
        )

        self._build_layout()

    def _build_layout(self):
        """Constructs the internal Flet layout for the card with responsive scrolling."""
        
        header_row = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.CABLE, color=ft.colors.BLUE_700),
                        self.title_text,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Row(
                    controls=[
                        self.btn_export,
                        self.btn_import,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            wrap=True
        )

        self.content = ft.Container(
            padding=20,
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    header_row,
                    ft.Divider(height=15, color=ft.colors.TRANSPARENT),
                    ft.Column(
                        expand=True,
                        scroll=ft.ScrollMode.ADAPTIVE,
                        controls=[
                            ft.Row(
                                controls=[self.table],
                                scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True
                            )
                        ]
                    )
                ]
            )
        )

    def load_agents_data(self, agents_list: List[Dict[str, str]]):
        """
        Populates the data table with agent data from the backend.
        Expected format: [{"agent_id": "Intersection_1", "ip_address": "192.168.1.50", "status": "disconnected"}]
        """
        self.last_agents_list = agents_list
        self.table.rows.clear()
        self.ip_fields.clear()
        
        hint_ip = "e.g. 10.0.0.5"
        status_disconnected_str = "disconnected"
        status_connected_str = "connected"
        btn_connect_str = "Connect"
        btn_disconnect_str = "Disconnect"
        
        if self.lm:
            hint_ip = self.lm.get_string("settings_view.hardware_card.hint_ip", default=hint_ip)
            status_disconnected_str = self.lm.get_string("settings_view.hardware_card.status_disconnected", default=status_disconnected_str)
            status_connected_str = self.lm.get_string("settings_view.hardware_card.status_connected", default=status_connected_str)
            btn_connect_str = self.lm.get_string("settings_view.hardware_card.btn_connect", default=btn_connect_str)
            btn_disconnect_str = self.lm.get_string("settings_view.hardware_card.btn_disconnect", default=btn_disconnect_str)
        
        for agent in agents_list:
            agent_id = agent.get("agent_id", "Unknown")
            ip_address = agent.get("ip_address", "")
            status = agent.get("status", "disconnected")

            # Inline IP Input Field
            ip_field = ft.TextField(
                value=ip_address,
                hint_text=hint_ip,
                width=160,
                dense=True,
                disabled=(status != "disconnected") # Lock field if connected
            )
            self.ip_fields[agent_id] = ip_field

            # Determine visual status
            status_color = ft.colors.RED_500 if status == "disconnected" else ft.colors.GREEN_500
            status_icon = ft.icons.RADIO_BUTTON_CHECKED if status != "disconnected" else ft.icons.RADIO_BUTTON_UNCHECKED
            
            status_label = status_disconnected_str if status == "disconnected" else status_connected_str
            
            status_display = ft.Row([
                ft.Icon(status_icon, color=status_color, size=16),
                ft.Text(status_label.upper(), color=status_color, weight=ft.FontWeight.W_500)
            ])

            # ActionButton
            action_text = btn_disconnect_str if status != "disconnected" else btn_connect_str
            action_btn = ft.OutlinedButton(
                text=action_text,
                on_click=lambda e, a=agent_id: self._handle_toggle(a)
            )

            # Create the row
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(agent_id)),
                    ft.DataCell(ip_field),
                    ft.DataCell(status_display),
                    ft.DataCell(action_btn),
                ]
            )
            self.table.rows.append(row)
            
        if self.page:
            self.update()

    # --- Internal Event Handlers ---

    def _handle_import(self, e):
        logger.debug("Import button clicked on UI.")
        if self.on_import_click:
            self.on_import_click(e)

    def _handle_export(self, e):
        logger.debug("Export button clicked on UI.")
        if self.on_export_click:
            self.on_export_click(e)

    def _handle_toggle(self, agent_id: str):
        """Passes the Intersection ID and whatever IP is currently in the text field."""
        current_ip = self.ip_fields[agent_id].value
        logger.debug(f"Toggle connection clicked for {agent_id} with IP: {current_ip}")
        if self.on_toggle_connection:
            self.on_toggle_connection(agent_id, current_ip)

    def update_translations(self, lm):
        self.lm = lm
        self.title_text.value = self.lm.get_string("settings_view.hardware_card.title", default="Hardware Connections")
        self.btn_export.text = self.lm.get_string("settings_view.hardware_card.btn_export", default="Export Template")
        self.btn_import.text = self.lm.get_string("settings_view.hardware_card.btn_import", default="Import Config")
        self.col_id_text.value = self.lm.get_string("settings_view.hardware_card.col_id", default="Intersection ID")
        self.col_ip_text.value = self.lm.get_string("settings_view.hardware_card.col_ip", default="IP Address")
        self.col_status_text.value = self.lm.get_string("settings_view.hardware_card.col_status", default="Status")
        self.col_action_text.value = self.lm.get_string("settings_view.hardware_card.col_action", default="Action")
        
        # Reload the rows with the new language
        if hasattr(self, 'last_agents_list') and self.last_agents_list:
            self.load_agents_data(self.last_agents_list)
        elif self.page:
            self.update()