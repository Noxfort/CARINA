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

# File: ui/formatting/official_info_section.py
# Author: Gabriel Moraes
# Date: 2026-07-01

import flet as ft
from typing import Dict, Any
from ui.handlers.locale_manager import LocaleManager

class OfficialInfoSection(ft.Column):
    """
    Sub-widget of ReportFormattingCard managing official metadata, headings, layout ordering, and logo path.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()
        self.spacing = 15
        self.lm = None
        
        self.lbl_official_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_report_title = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_city_uf = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_logo_path = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_secretary_name = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_secretary_title = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_agency_name = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_department_name = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        self.tf_report_title = ft.TextField(
            value=initial_values.get("report_title") or initial_values.get("xai_report_title", "LAUDO TÉCNICO DE ENGENHARIA DE TRÁFEGO"),
            expand=True
        )
        self.tf_city = ft.TextField(
            value=initial_values.get("report_city", "Apucarana"),
            width=220
        )
        self.tf_state_uf = ft.TextField(
            value=initial_values.get("report_state_uf", "PR"),
            width=80
        )
        self.tf_logo_path = ft.TextField(
            value=initial_values.get("report_logo_path") or initial_values.get("xai_logo_path", ""),
            expand=True,
            on_change=self._on_logo_path_change
        )
        self.btn_browse_logo = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
            on_click=self._on_browse_logo_click
        )
        
        self.tf_secretary_name = ft.TextField(
            value=initial_values.get("report_secretary_name") or initial_values.get("xai_secretary_name", "Dr. Gabriel Moraes"),
            width=300
        )
        self.tf_secretary_title = ft.TextField(
            value=initial_values.get("report_secretary_title") or initial_values.get("xai_secretary_title", "Secretário de Mobilidade e Trânsito"),
            expand=True
        )
        
        self.lbl_ordinance = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        ord_enabled_init = bool(initial_values.get("report_ordinance_enabled", False))
        self.chk_ordinance = ft.Checkbox(
            label="Incluir Portaria no Bloco de Assinatura",
            value=ord_enabled_init,
            on_change=self._on_ordinance_chk_change
        )
        self.tf_ordinance_number = ft.TextField(
            value=initial_values.get("report_ordinance_number", "123/2026"),
            disabled=not ord_enabled_init,
            expand=True
        )

        self.tf_agency_name = ft.TextField(
            value=initial_values.get("report_agency_name") or initial_values.get("xai_agency_name", "Prefeitura Municipal / Secretaria de Trânsito"),
            expand=True
        )
        self.tf_department_name = ft.TextField(
            value=initial_values.get("report_department_name") or initial_values.get("xai_department_name", "Departamento de Mobilidade Inteligente"),
            expand=True
        )
        
        self.tf_block_order = ft.TextField(
            value=initial_values.get("report_block_order") or initial_values.get("xai_block_order", "header,title,metadata,chart,content,signature"),
            expand=True
        )
        
        self.logo_file_picker = ft.FilePicker(on_result=self._on_logo_selected)

        self.controls = [
            self.lbl_official_title,
            ft.Row([
                ft.Column([self.lbl_report_title, self.tf_report_title], expand=True),
                ft.Column([self.lbl_city_uf, ft.Row([self.tf_city, self.tf_state_uf], spacing=5)]),
            ], spacing=15),
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
                ft.Column([self.chk_ordinance, self.tf_ordinance_number], expand=True),
            ], spacing=20),
            ft.Row([
                ft.Column([self.lbl_agency_name, self.tf_agency_name], expand=True),
                ft.Column([self.lbl_department_name, self.tf_department_name], expand=True),
            ], spacing=20)
        ]

    def _on_ordinance_chk_change(self, e):
        self.tf_ordinance_number.disabled = not self.chk_ordinance.value
        self.tf_ordinance_number.update()

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
            path = e.files[0].path
            self.tf_logo_path.value = path
            self.validate_logo_path(path)
            self.tf_logo_path.update()

    def _on_logo_path_change(self, e):
        self.validate_logo_path(self.tf_logo_path.value)
        self.tf_logo_path.update()

    def validate_logo_path(self, path: str) -> bool:
        if not path or not path.strip():
            self.tf_logo_path.error_text = None
            return True
        import os
        ext = os.path.splitext(path.strip().lower())[1]
        if ext in ['.png', '.jpg', '.jpeg']:
            self.tf_logo_path.error_text = None
            return True
        else:
            msg = "O caminho do logotipo deve ser uma imagem JPEG ou PNG (.png, .jpg, .jpeg)"
            if self.lm:
                msg = self.lm.get_string("settings_view.formatting_card.logo_error_format", default=msg)
            self.tf_logo_path.error_text = msg
            return False

    def validate_fields(self) -> bool:
        return self.validate_logo_path(self.tf_logo_path.value)

    def get_values(self) -> Dict[str, Any]:
        return {
            "report_title": self.tf_report_title.value,
            "report_city": self.tf_city.value,
            "report_state_uf": self.tf_state_uf.value,
            "report_logo_path": self.tf_logo_path.value,
            "report_secretary_name": self.tf_secretary_name.value,
            "report_secretary_title": self.tf_secretary_title.value,
            "report_ordinance_enabled": self.chk_ordinance.value,
            "report_ordinance_number": self.tf_ordinance_number.value,
            "report_agency_name": self.tf_agency_name.value,
            "report_department_name": self.tf_department_name.value,
            "report_block_order": self.tf_block_order.value,

            # Legacy aliases
            "xai_report_title": self.tf_report_title.value,
            "xai_logo_path": self.tf_logo_path.value,
            "xai_secretary_name": self.tf_secretary_name.value,
            "xai_secretary_title": self.tf_secretary_title.value,
            "xai_agency_name": self.tf_agency_name.value,
            "xai_department_name": self.tf_department_name.value,
            "xai_block_order": self.tf_block_order.value
        }

    def set_values(self, values: Dict[str, Any]):
        self.tf_report_title.value = values.get("report_title") or values.get("xai_report_title", "LAUDO TÉCNICO DE ENGENHARIA DE TRÁFEGO")
        self.tf_city.value = values.get("report_city", "Apucarana")
        self.tf_state_uf.value = values.get("report_state_uf", "PR")
        self.tf_logo_path.value = values.get("report_logo_path") or values.get("xai_logo_path", "")
        self.tf_secretary_name.value = values.get("report_secretary_name") or values.get("xai_secretary_name", "Dr. Gabriel Moraes")
        self.tf_secretary_title.value = values.get("report_secretary_title") or values.get("xai_secretary_title", "Secretário de Mobilidade e Trânsito")
        
        ord_enabled = bool(values.get("report_ordinance_enabled", False))
        self.chk_ordinance.value = ord_enabled
        self.tf_ordinance_number.value = values.get("report_ordinance_number", "123/2026")
        self.tf_ordinance_number.disabled = not ord_enabled
        
        self.tf_agency_name.value = values.get("report_agency_name") or values.get("xai_agency_name", "Prefeitura Municipal / Secretaria de Trânsito")
        self.tf_department_name.value = values.get("report_department_name") or values.get("xai_department_name", "Departamento de Mobilidade Inteligente")
        self.tf_block_order.value = values.get("report_block_order") or values.get("xai_block_order", "header,title,metadata,chart,content,signature")

    def update_translations(self, lm: LocaleManager):
        self.lm = lm
        self.lbl_official_title.value = lm.get_string("settings_view.formatting_card.official_title", default="Informações Oficiais do Laudo")
        self.lbl_report_title.value = lm.get_string("settings_view.formatting_card.report_title", default="Título do Relatório")
        self.lbl_city_uf.value = lm.get_string("settings_view.formatting_card.city_uf", default="Município e Estado (UF)")
        self.lbl_logo_path.value = lm.get_string("settings_view.formatting_card.logo_path", default="Caminho do Logotipo (Logo)")
        self.lbl_secretary_name.value = lm.get_string("settings_view.formatting_card.secretary_name", default="Nome do Secretário/Autoridade")
        self.lbl_secretary_title.value = lm.get_string("settings_view.formatting_card.secretary_title", default="Cargo/Título")
        self.chk_ordinance.label = lm.get_string("settings_view.formatting_card.chk_ordinance", default="Incluir Portaria no Bloco de Assinatura")
        self.tf_ordinance_number.label = lm.get_string("settings_view.formatting_card.ordinance_number", default="Número/Ano da Portaria (ex: 123/2026)")
        self.lbl_agency_name.value = lm.get_string("settings_view.formatting_card.agency_name", default="Órgão/Secretaria")
        self.lbl_department_name.value = lm.get_string("settings_view.formatting_card.department_name", default="Departamento")
