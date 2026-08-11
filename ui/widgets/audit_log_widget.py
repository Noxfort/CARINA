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

# File: ui/widgets/audit_log_widget.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import flet as ft
import os
import json
import logging
from datetime import datetime
from src.utils.paths import get_base_output_dir
from ui.handlers.locale_manager import LocaleManager

class AuditLogWidget(ft.Container):
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(expand=True)
        self.locale_manager = locale_manager
        self.audit_file = os.path.join(get_base_output_dir(), "results", "audit_log.json")
        
        self.title = ft.Text(self.locale_manager.get_string("audit.title", "Registro de Auditoria (Audit Logs)"), size=20, weight=ft.FontWeight.BOLD)
        
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(self.locale_manager.get_string("audit.date_time", "Data/Hora"))),
                ft.DataColumn(ft.Text(self.locale_manager.get_string("audit.user", "Usuário"))),
                ft.DataColumn(ft.Text(self.locale_manager.get_string("audit.action", "Ação"))),
                ft.DataColumn(ft.Text(self.locale_manager.get_string("audit.details", "Detalhes"))),
            ],
            rows=[],
            heading_row_color=ft.Colors.BLACK26,
            data_row_min_height=40,
            data_row_max_height=80,
            column_spacing=20,
            show_bottom_border=True
        )
        
        self.list_view = ft.ListView(
            expand=True,
            controls=[self.table]
        )
        
        self.refresh_btn = ft.ElevatedButton(self.locale_manager.get_string("audit.refresh", "Atualizar"), icon=ft.Icons.REFRESH, on_click=self._load_logs)
        
        self.content = ft.Column([
            ft.Row([ft.Icon(ft.Icons.POLICY), self.title, self.refresh_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Container(
                content=self.list_view,
                expand=True,
                border=ft.border.all(1, ft.Colors.WHITE24),
                border_radius=5
            )
        ])

    def did_mount(self):
        self._load_logs()

    def _load_logs(self, e=None):
        if not os.path.exists(self.audit_file):
            self.table.rows.clear()
            if self.page: self.update()
            return

        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Mostra os mais recentes primeiro
            data = list(reversed(data))
            
            rows = []
            for entry in data:
                try:
                    dt = datetime.fromisoformat(entry.get("timestamp", ""))
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    time_str = entry.get("timestamp", "")
                    
                rows.append(ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(time_str, size=12)),
                        ft.DataCell(ft.Text(entry.get("username", "Unknown"), size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(entry.get("action", ""), size=12, color=ft.Colors.AMBER_400)),
                        ft.DataCell(ft.Text(entry.get("details", ""), size=12, italic=True)),
                    ]
                ))
            
            self.table.rows = rows
            if self.page: self.update()
            
        except Exception as ex:
            logging.error(f"[AuditLogWidget] Erro ao carregar logs: {ex}")
