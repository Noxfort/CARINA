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

# File: ui/cards/report_formatting_card.py
# Author: Gabriel Moraes
# Date: 2026-06-19

import flet as ft
from typing import Dict, Any
from ui.handlers.locale_manager import LocaleManager

class ReportFormattingCard(ft.Card):
    """
    Card to customize styling, layout, and metadata for generated reports.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()
        
        self.initial_values = initial_values
        self.lm = None
        
        # --- UI CONTROLS ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.desc_text = ft.Text(size=12, color=ft.Colors.GREY_400)
        
        # Section 1 Labels
        self.lbl_typography_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_font = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_size = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_alignment = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_spacing = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        # Section 2 Labels
        self.lbl_margins_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_margin_top = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_margin_bottom = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_margin_left = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_margin_right = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        # Section 3 Labels
        self.lbl_official_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_report_title = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_logo_path = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_secretary_name = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_secretary_title = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_agency_name = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_department_name = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        # Section 1: Typography & Formatting
        self.dd_font_name = ft.Dropdown(
            options=[
                ft.dropdown.Option("Arial", "Arial"),
                ft.dropdown.Option("Calibri", "Calibri"),
                ft.dropdown.Option("Courier New", "Courier New"),
                ft.dropdown.Option("Times New Roman", "Times New Roman"),
                ft.dropdown.Option("Verdana", "Verdana"),
            ],
            value=initial_values.get("xai_font_name", "Arial"),
            width=200
        )
        
        self.dd_font_size = ft.Dropdown(
            options=[
                ft.dropdown.Option("9", "9 pt"),
                ft.dropdown.Option("10", "10 pt"),
                ft.dropdown.Option("11", "11 pt"),
                ft.dropdown.Option("12", "12 pt"),
                ft.dropdown.Option("14", "14 pt"),
                ft.dropdown.Option("16", "16 pt"),
            ],
            value=str(initial_values.get("xai_font_size", "11")),
            width=120
        )
        
        self.dd_alignment = ft.Dropdown(
            options=[
                ft.dropdown.Option("left", "Esquerda (Left)"),
                ft.dropdown.Option("center", "Centralizado (Center)"),
                ft.dropdown.Option("right", "Direita (Right)"),
                ft.dropdown.Option("justify", "Justificado (Justified)"),
            ],
            value=initial_values.get("xai_alignment", "justify"),
            width=180
        )
        
        self.dd_line_spacing = ft.Dropdown(
            options=[
                ft.dropdown.Option("1.0", "Simples (1.0)"),
                ft.dropdown.Option("1.15", "1.15"),
                ft.dropdown.Option("1.5", "1.5"),
                ft.dropdown.Option("2.0", "Duplo (2.0)"),
            ],
            value=str(initial_values.get("xai_line_spacing", "1.15")),
            width=140
        )
        
        # Section 2: Margins (in Inches)
        self.tf_margin_top = ft.TextField(
            value=str(initial_values.get("xai_margin_top", "1.0")),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        self.tf_margin_bottom = ft.TextField(
            value=str(initial_values.get("xai_margin_bottom", "1.0")),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        self.tf_margin_left = ft.TextField(
            value=str(initial_values.get("xai_margin_left", "1.0")),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        self.tf_margin_right = ft.TextField(
            value=str(initial_values.get("xai_margin_right", "1.0")),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Section 3: Official Metadata / Headers
        self.tf_report_title = ft.TextField(
            value=initial_values.get("xai_report_title", "LAUDO TÉCNICO DE EXPLICABILIDADE DE IA (XAI)"),
            expand=True
        )
        self.tf_logo_path = ft.TextField(
            value=initial_values.get("xai_logo_path", ""),
            expand=True
        )
        self.btn_browse_logo = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
            on_click=self._on_browse_logo_click
        )
        
        self.tf_secretary_name = ft.TextField(
            value=initial_values.get("xai_secretary_name", "Dr. Gabriel Moraes"),
            width=300
        )
        self.tf_secretary_title = ft.TextField(
            value=initial_values.get("xai_secretary_title", "Secretário de Mobilidade e Trânsito"),
            expand=True
        )
        
        self.tf_agency_name = ft.TextField(
            value=initial_values.get("xai_agency_name", "Prefeitura Municipal / Secretaria de Trânsito"),
            expand=True
        )
        self.tf_department_name = ft.TextField(
            value=initial_values.get("xai_department_name", "Departamento de Mobilidade Inteligente"),
            expand=True
        )
        
        self.tf_block_order = ft.TextField(
            value=initial_values.get("xai_block_order", "header,title,metadata,chart,content,signature"),
            expand=True
        )
 
        # File picker for Logo selection
        self.logo_file_picker = ft.FilePicker(on_result=self._on_logo_selected)
 
        # --- STRUCTURE ---
        self.content = ft.Container(
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, size=24), self.title_text]),
                    self.desc_text,
                    ft.Divider(),
                    
                    # Row 1: Typography
                    self.lbl_typography_title,
                    ft.Row(
                        controls=[
                            ft.Column([self.lbl_font, self.dd_font_name]),
                            ft.Column([self.lbl_size, self.dd_font_size]),
                            ft.Column([self.lbl_alignment, self.dd_alignment]),
                            ft.Column([self.lbl_spacing, self.dd_line_spacing]),
                        ],
                        spacing=20,
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.Divider(),
                    
                    # Row 2: Margins
                    self.lbl_margins_title,
                    ft.Row(
                        controls=[
                            ft.Column([self.lbl_margin_top, self.tf_margin_top]),
                            ft.Column([self.lbl_margin_bottom, self.tf_margin_bottom]),
                            ft.Column([self.lbl_margin_left, self.tf_margin_left]),
                            ft.Column([self.lbl_margin_right, self.tf_margin_right]),
                        ],
                        spacing=20
                    ),
                    ft.Divider(),
                    
                    # Row 3: Official Authority Metadata
                    self.lbl_official_title,
                    ft.Row([
                        ft.Column([self.lbl_report_title, self.tf_report_title], expand=True),
                    ]),
                    ft.Row([
                        ft.Column([
                            self.lbl_logo_path,
                            ft.Row([self.tf_logo_path, self.btn_browse_logo])
                        ], expand=True),
                    ]),
                    ft.Row([
                        ft.Column([self.lbl_secretary_name, self.tf_secretary_name]),
                        ft.Column([self.lbl_secretary_title, self.tf_secretary_title], expand=True),
                    ], spacing=20),
                    ft.Row([
                        ft.Column([self.lbl_agency_name, self.tf_agency_name], expand=True),
                        ft.Column([self.lbl_department_name, self.tf_department_name], expand=True),
                    ], spacing=20)
                ],
                spacing=15
            )
        )
 
    def did_mount(self):
        if self.page:
            self.page.overlay.append(self.logo_file_picker)
            self.page.update()
 
    def _on_browse_logo_click(self, e):
        dlg_title = "Selecione o Logotipo Oficial"
        if self.lm:
            dlg_title = self.lm.get_string("settings_view.formatting_card.logo_dialog_title", default=dlg_title)
        self.logo_file_picker.pick_files(
            dialog_title=dlg_title,
            allowed_extensions=["png", "jpg", "jpeg"]
        )
 
    def _on_logo_selected(self, e):
        if e.files:
            self.tf_logo_path.value = e.files[0].path
            self.tf_logo_path.update()
 
    def get_values(self) -> Dict[str, Any]:
        return {
            "xai_font_name": self.dd_font_name.value,
            "xai_font_size": int(self.dd_font_size.value) if self.dd_font_size.value else 11,
            "xai_alignment": self.dd_alignment.value,
            "xai_line_spacing": float(self.dd_line_spacing.value) if self.dd_line_spacing.value else 1.15,
            "xai_margin_top": float(self.tf_margin_top.value) if self.tf_margin_top.value else 1.0,
            "xai_margin_bottom": float(self.tf_margin_bottom.value) if self.tf_margin_bottom.value else 1.0,
            "xai_margin_left": float(self.tf_margin_left.value) if self.tf_margin_left.value else 1.0,
            "xai_margin_right": float(self.tf_margin_right.value) if self.tf_margin_right.value else 1.0,
            "xai_report_title": self.tf_report_title.value,
            "xai_logo_path": self.tf_logo_path.value,
            "xai_secretary_name": self.tf_secretary_name.value,
            "xai_secretary_title": self.tf_secretary_title.value,
            "xai_agency_name": self.tf_agency_name.value,
            "xai_department_name": self.tf_department_name.value,
            "xai_block_order": self.tf_block_order.value
        }
 
    def set_values(self, values: Dict[str, Any]):
        self.dd_font_name.value = values.get("xai_font_name", "Arial")
        self.dd_font_size.value = str(values.get("xai_font_size", "11"))
        self.dd_alignment.value = values.get("xai_alignment", "justify")
        self.dd_line_spacing.value = str(values.get("xai_line_spacing", "1.15"))
        
        self.tf_margin_top.value = str(values.get("xai_margin_top", "1.0"))
        self.tf_margin_bottom.value = str(values.get("xai_margin_bottom", "1.0"))
        self.tf_margin_left.value = str(values.get("xai_margin_left", "1.0"))
        self.tf_margin_right.value = str(values.get("xai_margin_right", "1.0"))
        
        self.tf_report_title.value = values.get("xai_report_title", "LAUDO TÉCNICO DE EXPLICABILIDADE DE IA (XAI)")
        self.tf_logo_path.value = values.get("xai_logo_path", "")
        self.tf_secretary_name.value = values.get("xai_secretary_name", "Dr. Gabriel Moraes")
        self.tf_secretary_title.value = values.get("xai_secretary_title", "Secretário de Mobilidade e Trânsito")
        self.tf_agency_name.value = values.get("xai_agency_name", "Prefeitura Municipal / Secretaria de Trânsito")
        self.tf_department_name.value = values.get("xai_department_name", "Departamento de Mobilidade Inteligente")
        self.tf_block_order.value = values.get("xai_block_order", "header,title,metadata,chart,content,signature")
        
        if self.page: self.update()
 
    def update_translations(self, lm: LocaleManager):
        self.lm = lm
        self.title_text.value = lm.get_string("settings_view.formatting_card_title", default="Formatação e Layout dos Laudos")
        self.desc_text.value = lm.get_string("settings_view.formatting_card_desc", default="Personalize as fontes, alinhamentos, margens e informações oficiais do documento exportado.")
        
        # Section 1 Labels
        self.lbl_typography_title.value = lm.get_string("settings_view.formatting_card.typography_title", default="Tipografia e Espaçamento")
        self.lbl_font.value = lm.get_string("settings_view.formatting_card.font_label", default="Fonte")
        self.lbl_size.value = lm.get_string("settings_view.formatting_card.size_label", default="Tamanho")
        self.lbl_alignment.value = lm.get_string("settings_view.formatting_card.alignment_label", default="Alinhamento")
        self.lbl_spacing.value = lm.get_string("settings_view.formatting_card.spacing_label", default="Espaçamento")
        
        # Section 2 Labels
        self.lbl_margins_title.value = lm.get_string("settings_view.formatting_card.margins_title", default="Margens da Página (polegadas)")
        self.lbl_margin_top.value = lm.get_string("settings_view.formatting_card.margin_top", default="Superior")
        self.lbl_margin_bottom.value = lm.get_string("settings_view.formatting_card.margin_bottom", default="Inferior")
        self.lbl_margin_left.value = lm.get_string("settings_view.formatting_card.margin_left", default="Esquerda")
        self.lbl_margin_right.value = lm.get_string("settings_view.formatting_card.margin_right", default="Direita")
        
        # Section 3 Labels
        self.lbl_official_title.value = lm.get_string("settings_view.formatting_card.official_title", default="Informações Oficiais do Laudo")
        self.lbl_report_title.value = lm.get_string("settings_view.formatting_card.report_title", default="Título do Relatório")
        self.lbl_logo_path.value = lm.get_string("settings_view.formatting_card.logo_path", default="Caminho do Logotipo (Logo)")
        self.lbl_secretary_name.value = lm.get_string("settings_view.formatting_card.secretary_name", default="Nome do Secretário/Autoridade")
        self.lbl_secretary_title.value = lm.get_string("settings_view.formatting_card.secretary_title", default="Cargo/Título")
        self.lbl_agency_name.value = lm.get_string("settings_view.formatting_card.agency_name", default="Órgão/Secretaria")
        self.lbl_department_name.value = lm.get_string("settings_view.formatting_card.department_name", default="Departamento")
        
        # Dropdown options text update
        if len(self.dd_alignment.options) >= 4:
            self.dd_alignment.options[0].text = lm.get_string("settings_view.formatting_card.alignment_left", default="Esquerda (Left)")
            self.dd_alignment.options[1].text = lm.get_string("settings_view.formatting_card.alignment_center", default="Centralizado (Center)")
            self.dd_alignment.options[2].text = lm.get_string("settings_view.formatting_card.alignment_right", default="Direita (Right)")
            self.dd_alignment.options[3].text = lm.get_string("settings_view.formatting_card.alignment_justify", default="Justificado (Justified)")
            
        if len(self.dd_line_spacing.options) >= 4:
            self.dd_line_spacing.options[0].text = lm.get_string("settings_view.formatting_card.spacing_simple", default="Simples (1.0)")
            self.dd_line_spacing.options[1].text = "1.15"
            self.dd_line_spacing.options[2].text = "1.5"
            self.dd_line_spacing.options[3].text = lm.get_string("settings_view.formatting_card.spacing_double", default="Duplo (2.0)")
            
        if self.page: self.update()
