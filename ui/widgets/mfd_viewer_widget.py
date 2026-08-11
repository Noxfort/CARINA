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

# File: ui/widgets/mfd_viewer_widget.py
# Author: Gabriel Moraes
# Date: June 19, 2026

import flet as ft
import os
import shutil
import logging
from ui.handlers.locale_manager import LocaleManager
from ui.widgets.explanation_viewer_widget import ExplanationViewerWidget
from ui.widgets.plot_viewer_widget import PlotViewerWidget
from ui.clients.mfd_analysis_client import MfdAnalysisClient

class MfdViewerWidget(ft.Column):
    """
    Main widget for the MFD Optimization Analysis tab.
    Maintains clean separation of concerns by delegating orchestration, I/O, 
    and IPC to MfdAnalysisClient, acting strictly as a passive view.
    """
    def __init__(self, locale_manager: LocaleManager, results_dir: str, control_client=None):
        super().__init__()
        self.locale_manager = locale_manager
        self.results_dir = results_dir
        self.control_client = control_client
        self.generated_img_base64 = None
        self.generated_txt_content = None
        self.is_analyzing = False
        
        # Initialize MfdAnalysisClient to orchestrate the backend request/response cycle
        self.mfd_client = MfdAnalysisClient(
            on_analysis_complete_callback=self._on_mfd_analysis_complete,
            results_dir=self.results_dir
        )
        
        # Column Configuration
        self.expand = True
        self.spacing = 10
        
        # UI Components
        self.analyze_btn = ft.ElevatedButton(
            text=self.locale_manager.get_string("mfd_viewer.analyze_btn", default="Gerar Relatório de Otimização MFD"),
            icon=ft.Icons.ANALYTICS_ROUNDED,
            on_click=self._on_analyze_click,
            disabled=False
        )

        self.export_btn = ft.ElevatedButton(
            text=self.locale_manager.get_string("mfd_viewer.export_btn", default="Salvar Laudo MFD (.docx)"),
            icon=ft.Icons.SAVE_ROUNDED,
            on_click=self._on_export_click,
            visible=False
        )
        
        self.status_text = ft.Text(value="", color=ft.Colors.GREY_400, size=12)
        
        # Visualization Sub-widgets
        self.plot_viewer = PlotViewerWidget(locale_manager)
        self.explanation_viewer = ExplanationViewerWidget(locale_manager)
        
        # File Picker for saving reports
        self.file_picker = ft.FilePicker(on_result=self._on_save_docx_result)
        
        # Defines children controls
        self.controls = [
            ft.Row(
                controls=[self.analyze_btn, self.export_btn],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15
            ),
            self.status_text,
            ft.Divider(),
            ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text=self.locale_manager.get_string("mfd_viewer.tab_chart", default="Curva MFD (Gráfico)"),
                        icon=ft.Icons.BAR_CHART_ROUNDED,
                        content=ft.Container(
                            content=self.plot_viewer,
                            padding=10
                        )
                    ),
                    ft.Tab(
                        text=self.locale_manager.get_string("mfd_viewer.tab_text", default="Laudo Estruturado (Relatório SLM)"),
                        icon=ft.Icons.DESCRIPTION_ROUNDED,
                        content=ft.Container(
                            content=self.explanation_viewer,
                            padding=10
                        )
                    ),
                ],
                expand=True
            )
        ]

    def did_mount(self):
        if self.page:
            self.page.overlay.append(self.file_picker)
            self.page.update()

    def update_translations(self, locale_manager: LocaleManager):
        self.locale_manager = locale_manager
        self.analyze_btn.text = locale_manager.get_string("mfd_viewer.analyze_btn", default="Gerar Relatório de Otimização MFD")
        self.export_btn.text = locale_manager.get_string("mfd_viewer.export_btn", default="Salvar Laudo MFD (.docx)")
        
        # Tabs
        self.controls[3].tabs[0].text = locale_manager.get_string("mfd_viewer.tab_chart", default="Curva MFD (Gráfico)")
        self.controls[3].tabs[1].text = locale_manager.get_string("mfd_viewer.tab_text", default="Laudo Estruturado (Relatório SLM)")
        
        if self.page: self.update()

    def _on_analyze_click(self, e):
        # 1. Immediate UI Feedback
        self.is_analyzing = True
        self.analyze_btn.disabled = True
        self.export_btn.visible = False
        self.generated_img_base64 = None
        self.generated_txt_content = None
        
        # Clear previous results
        self.plot_viewer.load_plot_base64(None) 
        self.explanation_viewer.set_text(None) 
        
        self.status_text.value = self.locale_manager.get_string("mfd_viewer.status_requesting", default="Processando dados do Diagrama Fundamental Macroscópico (MFD) e invocando SLM...")
        self.status_text.color = ft.Colors.ORANGE_400
        self.update()

        # 2. Delegate orchestration exclusively to MfdAnalysisClient (single trigger via IPC)
        logging.info("[MFD_WIDGET] Requesting MFD optimization analysis via MfdAnalysisClient")
        self.mfd_client.start_analysis()

    def _on_mfd_analysis_complete(self, response: dict):
        """Callback received from MfdAnalysisClient thread on analysis completion."""
        if not self.page:
            return
            
        if response.get("status") == "complete":
            image_base64 = response.get("image_base64")
            text_content = response.get("text_report")
            
            if image_base64 and text_content:
                self._safe_update_ui(image_base64, text_content, success=True)
            else:
                missing_msg = self.locale_manager.get_string("mfd_viewer.missing_response", default="Success signal received, but response data is missing.")
                self._safe_update_ui(None, missing_msg, success=False)
        else:
            err_msg = response.get("message", "Unknown error")
            self._safe_update_ui(None, err_msg, success=False)
 
    def _safe_update_ui(self, image_base64, text_content, success):
        """Updates the UI elements (runs on Flet UI thread)."""
        self.is_analyzing = False
        self.analyze_btn.disabled = False
        
        if success:
            self.plot_viewer.load_plot_base64(image_base64)
            self.explanation_viewer.set_text(text_content)
 
            self.generated_img_base64 = image_base64
            self.generated_txt_content = text_content
            self.export_btn.visible = True
 
            self.status_text.value = self.locale_manager.get_string("mfd_viewer.status_success", default="Relatório de otimização gerado com sucesso!")
            self.status_text.color = ft.Colors.GREEN_400
        else:
            self.status_text.value = self.locale_manager.get_string("mfd_viewer.status_error", default="Falha: {error}", error=text_content)
            self.status_text.color = ft.Colors.RED_400
            self.export_btn.visible = False
            self.generated_img_base64 = None
            self.generated_txt_content = None
        
        self.update()
 
    def _on_export_click(self, e):
        if not self.generated_txt_content or not self.generated_img_base64:
            return
            
        self.file_picker.save_file(
            dialog_title=self.locale_manager.get_string("mfd_viewer.export_title", default="Salvar Relatório MFD"),
            file_name=self.locale_manager.get_string("mfd_viewer.export_filename", default="relatorio_otimizacao_mfd.docx"),
            allowed_extensions=["docx"]
        )
 
    def _on_save_docx_result(self, e):
        if e.path and self.generated_txt_content and self.generated_img_base64:
            from ui.formatting.report_exporter import ReportExporter
            central_control_label = self.locale_manager.get_string("mfd_viewer.central_control", default="CARINA Central Control")
            ReportExporter.export_report(
                page=self.page,
                locale_manager=self.locale_manager,
                save_path=e.path,
                image_base64=self.generated_img_base64,
                text_content=self.generated_txt_content,
                results_dir=self.results_dir,
                mode="MFD",
                agent_id=central_control_label
            )
