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

# File: ui/views/planning_view.py (Refactored for Clean Stateless Export & Progress Flow)
# Author: Gabriel Moraes
# Date: December 15, 2025

import flet as ft
import os
import logging
from datetime import datetime

from ui.components.interactive_map import InteractiveMap
from ui.clients.infrastructure_client import InfrastructureClient
from ui.handlers.locale_manager import LocaleManager

class PlanningView(ft.Container):
    def __init__(self, locale_manager: LocaleManager, control_client=None, sas_result_queue=None):
        super().__init__(expand=True)

        self.locale_manager = locale_manager
        self.control_client = control_client
        self.client = InfrastructureClient(on_complete_callback=self._on_analysis_complete, sas_result_queue=sas_result_queue)
        self.last_report_content = None
        self.last_scenario_dir = None
        self.is_analyzing = False

        self.file_picker = ft.FilePicker(on_result=self._on_save_result)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        
        def on_node_click(tl_id):
            if self.page:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Semáforo selecionado: {tl_id}"))
                self.page.snack_bar.open = True
                self.page.update()

        self.map_widget = InteractiveMap(
            project_root=project_root, 
            on_node_click=on_node_click,
            on_topology_loaded=self._on_topology_loaded
        )
        
        self.analyze_button = ft.ElevatedButton("Carregar Análise", disabled=True, on_click=self._load_analysis_click)
        self.save_report_button = ft.ElevatedButton("Gerar Relatório", icon=ft.Icons.SAVE_ALT_ROUNDED, on_click=self._save_report_click, disabled=True)
        self.status_text = ft.Text("Aguardando carregamento da topologia do mapa...", italic=True)

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
        self.update_translations(self.locale_manager)
        self.load_map()
        self.page.update()

    def load_map(self):
        if self.map_widget:
            self.map_widget.load_map()

    def _on_topology_loaded(self):
        if self.is_analyzing:
            return
        self.analyze_button.disabled = False
        if self.locale_manager:
            self.status_text.value = self.locale_manager.get_string("planning_view.status_ready", default="Topologia carregada. Pronto para análise.")
        else:
            self.status_text.value = "Topologia carregada. Pronto para análise."
        self.status_text.italic = True
        self.status_text.color = None
        self.update()

    def update_translations(self, lm: LocaleManager):
        self.analyze_button.text = lm.get_string("planning_view.analyze_button")
        self.analyze_button.tooltip = lm.get_string("planning_view.analyze_tooltip")
        self.save_report_button.text = lm.get_string("planning_view.generate_report_button")
        if not self.is_analyzing and not self.analyze_button.disabled:
            self.status_text.value = lm.get_string("planning_view.status_ready")
        
        self.legend_title.value = lm.get_string("planning_view.legend_title", "Legenda:")
        self.legend_tl_keep.value = lm.get_string("planning_view.legend_tl_keep", "Manter")
        self.legend_tl_remove.value = lm.get_string("planning_view.legend_tl_remove", "Tirar")
        self.legend_tl_add.value = lm.get_string("planning_view.legend_tl_add", "Por")
        self.legend_junction.value = lm.get_string("planning_view.legend_junction", "Cruzamento")
        self.legend_street.value = lm.get_string("planning_view.legend_street", "Vias")

    def _load_analysis_click(self, e):
        import time
        trigger_time = time.time()
        
        self.is_analyzing = True
        # 1. Clean slate: Reset all memory from previous runs
        self.last_report_content = None
        self.last_scenario_dir = None
        if self.map_widget:
            self.map_widget.set_recommendations({})

        self.analyze_button.disabled = True
        self.save_report_button.disabled = True
        if self.locale_manager:
            self.status_text.value = self.locale_manager.get_string("planning_view.status_processing", default="Processando análise e gerando laudo por inteligência artificial... Por favor, aguarde.")
        else:
            self.status_text.value = "Processando análise e gerando laudo por inteligência artificial... Por favor, aguarde."
        self.status_text.italic = False
        self.status_text.color = ft.Colors.CYAN
        self.update()
        
        self.map_widget.load_map()
        
        if self.control_client:
            try:
                self.control_client.trigger_analysis()
            except Exception as ex:
                logging.error(f"[PLANNING_VIEW] Error triggering analysis: {ex}")
        
        self.client.start_fetching_latest_analysis(trigger_time=trigger_time)

    def _on_analysis_complete(self, response: dict):
        try:
            self._process_analysis_response(response)
        except Exception as ex:
            logging.error(f"[PLANNING_VIEW] Error processing analysis response: {ex}", exc_info=True)

    def _process_analysis_response(self, response: dict):
        self.is_analyzing = False
        self.analyze_button.disabled = False
        
        if response.get("status") == "error":
            self.status_text.value = response.get("message", "Erro desconhecido.")
            self.status_text.color = ft.Colors.RED
            self.last_report_content = None
            self.save_report_button.disabled = True
            if self.page:
                self.page.update()
            else:
                self.update()
            return

        self.last_report_content = response.get("report_content")
        self.last_scenario_dir = response.get("scenario_dir")
        
        recs = response.get("analysis_results", {})
        if recs and self.map_widget:
            self.map_widget.set_recommendations(recs)
        
        if self.last_report_content:
            self.save_report_button.disabled = False
        else:
            self.save_report_button.disabled = True
        
        if response.get("significant_change") is False:
            self.status_text.value = self.locale_manager.get_string("planning_view.status_loaded_no_change")
            self.status_text.color = ft.Colors.AMBER
        else:
            self.status_text.value = self.locale_manager.get_string("planning_view.status_loaded_with_change")
            self.status_text.color = ft.Colors.GREEN
        
        if self.page:
            self.page.update()
        else:
            self.update()

    def _save_report_click(self, e):
        if not self.last_report_content:
            return
            
        self.file_picker.save_file(
            dialog_title=self.locale_manager.get_string("planning_view.file_picker_title"),
            file_name=f"relatorio_infraestrutura_{datetime.now().strftime('%Y%m%d')}.docx",
            allowed_extensions=["docx"]
        )

    def _on_save_result(self, e):
        if e.path and self.last_report_content:
            save_path = e.path
            if not save_path.lower().endswith(".docx"):
                save_path += ".docx"
            try:
                import base64
                image_base64 = ""
                if self.last_scenario_dir:
                    map_path = os.path.join(self.last_scenario_dir, "map_planning.png")
                    if not os.path.exists(map_path):
                        map_path = os.path.join(self.last_scenario_dir, "maps", "map_planning.png")
                    if os.path.exists(map_path):
                        with open(map_path, "rb") as img_file:
                            image_base64 = base64.b64encode(img_file.read()).decode("utf-8")
                
                from ui.formatting.report_exporter import ReportExporter
                success = ReportExporter.export_report(
                    page=self.page,
                    locale_manager=self.locale_manager,
                    save_path=save_path,
                    image_base64=image_base64,
                    text_content=self.last_report_content,
                    results_dir=self.last_scenario_dir if self.last_scenario_dir else "",
                    mode="PLANNING",
                    agent_id="CARINA SAS Engine"
                )
                
                if success:
                    self.status_text.value = self.locale_manager.get_string("planning_view.status_report_saved")
                    self.status_text.italic = True
                    self.status_text.color = None
                else:
                    self.status_text.value = "Erro ao exportar relatório DOCX."
                    self.status_text.color = ft.Colors.RED
            except Exception as ex:
                self.status_text.value = f"Erro ao salvar arquivo: {ex}"
                self.status_text.color = ft.Colors.RED
        else:
            self.status_text.value = self.locale_manager.get_string("planning_view.status_save_cancelled")
        self.update()