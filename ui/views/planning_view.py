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

# File: ui/views/planning_view.py (CHANGED: InteractiveMap Integration)
# Author: Gabriel Moraes
# Date: December 15, 2025

import flet as ft
import os
from datetime import datetime

# We replaced NativeMapWidget with InteractiveMap
from ui.components.interactive_map import InteractiveMap
from ui.clients.infrastructure_client import InfrastructureClient
from ui.handlers.locale_manager import LocaleManager

class PlanningView(ft.Container):
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(expand=True)

        self.locale_manager = locale_manager
        self.client = InfrastructureClient(on_complete_callback=self._on_analysis_complete)
        self.last_report_content = None

        self.dialog_title = ft.Text()
        self.dialog_content = ft.Text()
        self.dialog_confirm_button = ft.ElevatedButton(on_click=self._handle_dialog_confirm)
        self.dialog_cancel_button = ft.TextButton(on_click=self._handle_dialog_cancel)

        self.confirmation_dialog = ft.AlertDialog(
            modal=True, title=self.dialog_title, content=self.dialog_content,
            actions=[self.dialog_confirm_button, self.dialog_cancel_button],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.file_picker = ft.FilePicker(on_result=self._on_save_result)
        
        # --- CHANGE: Instantiate InteractiveMap ---
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        
        def on_node_click(tl_id):
            if self.page:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Semáforo selecionado: {tl_id}"))
                self.page.snack_bar.open = True
                self.page.update()

        self.map_widget = InteractiveMap(project_root=project_root, on_node_click=on_node_click)
        # -------------------------------------------
        
        self.analyze_button = ft.ElevatedButton(on_click=self._load_analysis_click)
        self.save_report_button = ft.ElevatedButton(icon=ft.Icons.SAVE_ALT_ROUNDED, on_click=self._save_report_click, disabled=True)
        self.status_text = ft.Text(italic=True)

        # Original Command Bar
        self.command_bar = ft.Container(
            content=ft.Row(
                controls=[
                    self.analyze_button, ft.Container(expand=True),
                    self.status_text, ft.Container(expand=True),
                    self.save_report_button,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            height=60, padding=ft.padding.symmetric(horizontal=20),
            border_radius=ft.border_radius.only(top_left=10, top_right=10),
            bgcolor=ft.Colors.WHITE10
        )
        
        # --- NEW: Map Legend ---
        self.legend_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.legend_tl_keep = ft.Text("Manter")
        self.legend_tl_remove = ft.Text("Tirar")
        self.legend_tl_add = ft.Text("Por")
        self.legend_junction = ft.Text()
        self.legend_street = ft.Text()

        self.legend_bar = ft.Container(
            content=ft.Row(
                controls=[
                    self.legend_title,
                    ft.Icon(ft.Icons.SQUARE, color=ft.Colors.BLUE_800, size=16),
                    self.legend_tl_keep,
                    ft.Icon(ft.Icons.SQUARE, color=ft.Colors.RED_700, size=16),
                    self.legend_tl_remove,
                    ft.Icon(ft.Icons.SQUARE, color=ft.Colors.GREEN_700, size=16),
                    self.legend_tl_add,
                    ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.ORANGE_600, size=16),
                    self.legend_junction,
                    ft.Container(width=20, height=4, bgcolor=ft.Colors.BLACK, border_radius=2),
                    self.legend_street,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(vertical=5),
        )

        self.content = ft.Column(
            controls=[self.map_widget, self.legend_bar, self.command_bar],
            expand=True, spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )

    def did_mount(self):
        self.page.overlay.append(self.file_picker)
        self.page.overlay.append(self.confirmation_dialog)
        self.update_translations(self.locale_manager)
        # Try loading the map when riding
        self.load_map()
        self.page.update()

    def load_map(self):
        """Método público para recarregar o mapa (chamado pela MainUI)."""
        if self.map_widget:
            self.map_widget.load_map()

    def update_translations(self, lm: LocaleManager):
        self.analyze_button.text = lm.get_string("planning_view.analyze_button")
        self.analyze_button.tooltip = lm.get_string("planning_view.analyze_tooltip")
        self.save_report_button.text = lm.get_string("planning_view.generate_report_button")
        self.status_text.value = lm.get_string("planning_view.status_ready")
        self.dialog_title.value = lm.get_string("planning_view.dialog_no_change_title")
        self.dialog_content.value = lm.get_string("planning_view.dialog_no_change_content")
        self.dialog_confirm_button.text = lm.get_string("planning_view.dialog_confirm_button")
        self.dialog_cancel_button.text = lm.get_string("dialogs.cancel_button")
        
        # Translations for Legend
        self.legend_title.value = lm.get_string("planning_view.legend_title", "Legenda:")
        self.legend_tl_keep.value = lm.get_string("planning_view.legend_tl_keep", "Manter")
        self.legend_tl_remove.value = lm.get_string("planning_view.legend_tl_remove", "Tirar")
        self.legend_tl_add.value = lm.get_string("planning_view.legend_tl_add", "Por")
        self.legend_junction.value = lm.get_string("planning_view.legend_junction", "Cruzamento")
        self.legend_street.value = lm.get_string("planning_view.legend_street", "Vias")
        # The new widget does not need explicit update_translations as it is visual

    def _load_analysis_click(self, e):
        self.status_text.value = self.locale_manager.get_string("planning_view.status_loading")
        self.status_text.italic = False
        self.status_text.color = ft.Colors.CYAN
        self.save_report_button.disabled = True
        self.update()
        
        # Also reloads the map visuals
        self.map_widget.load_map()
        
        self.client.start_fetching_latest_analysis()

    def _on_analysis_complete(self, response: dict):
        def update_ui_on_main_thread():
            self._process_analysis_response(response)
        if self.page:
            self.page.run_on_ui(update_ui_on_main_thread)

    def _process_analysis_response(self, response: dict):
        if response.get("status") == "error":
            self.status_text.value = response.get("message", "Erro desconhecido.")
            self.status_text.color = ft.Colors.RED
            self.last_report_content = None
            self.update()
            return

        self.last_report_content = response.get("report_content")
        
        # Pass recommendations to the map to update colors
        recs = response.get("analysis_results", {})
        if recs and self.map_widget:
            self.map_widget.set_recommendations(recs)
        
        if response.get("significant_change") is False:
            self.confirmation_dialog.open = True
            self.status_text.value = self.locale_manager.get_string("planning_view.status_loaded_no_change")
            self.status_text.color = ft.Colors.AMBER
        else:
            self.status_text.value = self.locale_manager.get_string("planning_view.status_loaded_with_change")
            self.status_text.color = ft.Colors.GREEN
            self.save_report_button.disabled = False
        
        self.update()

    def _save_report_click(self, e):
        self.file_picker.save_file(
            dialog_title=self.locale_manager.get_string("planning_view.file_picker_title"),
            file_name=f"relatorio_infraestrutura_{datetime.now().strftime('%Y%m%d')}.txt",
            allowed_extensions=["txt"]
        )

    def _on_save_result(self, e):
        if e.path and self.last_report_content:
            save_path = e.path
            if not save_path.lower().endswith(".txt"): save_path += ".txt"
            try:
                with open(save_path, "w", encoding="utf-8") as f: f.write(self.last_report_content)
                template = self.locale_manager.get_string("planning_view.snackbar_report_saved")
                self.page.snack_bar = ft.SnackBar(content=ft.Text(template.format(path=save_path)))
                self.page.snack_bar.open = True
                self.status_text.value = self.locale_manager.get_string("planning_view.status_report_saved")
                self.status_text.italic = True
                self.status_text.color = None
            except Exception as ex:
                self.status_text.value = f"Erro ao salvar arquivo: {ex}"
                self.status_text.color = ft.Colors.RED
        else:
            self.status_text.value = self.locale_manager.get_string("planning_view.status_save_cancelled")
        self.update()

    def _handle_dialog_confirm(self, e):
        self.confirmation_dialog.open = False
        self.save_report_button.disabled = False
        self.page.update()

    def _handle_dialog_cancel(self, e):
        self.confirmation_dialog.open = False
        self.page.update()