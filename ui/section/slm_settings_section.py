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

# File: ui/formatting/slm_settings_section.py
# Author: Gabriel Moraes
# Date: 2026-07-01

import flet as ft
from typing import Dict, Any
from ui.handlers.locale_manager import LocaleManager

class SlmSettingsSection(ft.Column):
    """
    Sub-widget of ReportFormattingCard managing SLM execution hardware and GPU offload options.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()
        self.spacing = 15
        self.lm = None
        
        self.lbl_slm_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_slm_device = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_slm_gpu_layers = ft.Text(size=11, weight=ft.FontWeight.W_500)
        
        self.dd_slm_device = ft.Dropdown(
            options=[
                ft.dropdown.Option("cpu", "CPU Apenas (CPU Only)"),
                ft.dropdown.Option("gpu", "GPU Total (Full GPU Offload)"),
                ft.dropdown.Option("mixed", "Modo Misto (CPU + GPU Offload)"),
            ],
            value=initial_values.get("xai_slm_device", "cpu"),
            width=220,
            on_change=self._on_slm_device_change
        )
        
        self.tf_slm_gpu_layers = ft.TextField(
            value=str(initial_values.get("xai_slm_gpu_layers", "16")),
            width=120,
            text_align=ft.TextAlign.RIGHT,
            keyboard_type=ft.KeyboardType.NUMBER,
            disabled=(initial_values.get("xai_slm_device", "cpu") != "mixed"),
            on_change=self._on_gpu_layers_change
        )
        
        self.controls = [
            self.lbl_slm_title,
            ft.Row(
                controls=[
                    ft.Column([self.lbl_slm_device, self.dd_slm_device]),
                    ft.Column([self.lbl_slm_gpu_layers, self.tf_slm_gpu_layers]),
                ],
                spacing=20
            )
        ]

    def _on_slm_device_change(self, e):
        self.tf_slm_gpu_layers.disabled = (self.dd_slm_device.value != "mixed")
        self.validate_slm_gpu_layers(self.tf_slm_gpu_layers.value)
        self.tf_slm_gpu_layers.update()

    def _on_gpu_layers_change(self, e):
        self.validate_slm_gpu_layers(self.tf_slm_gpu_layers.value)
        self.tf_slm_gpu_layers.update()

    def validate_slm_gpu_layers(self, val: str) -> bool:
        if self.dd_slm_device.value != "mixed":
            self.tf_slm_gpu_layers.error_text = None
            return True
        if not val or not val.strip():
            msg = "O número de camadas para GPU é obrigatório no modo misto"
            if self.lm:
                msg = self.lm.get_string("settings_view.formatting_card.gpu_layers_required", default=msg)
            self.tf_slm_gpu_layers.error_text = msg
            return False
        try:
            num = int(val.strip())
            if num <= 0:
                raise ValueError()
            self.tf_slm_gpu_layers.error_text = None
            return True
        except ValueError:
            msg = "Deve ser um número inteiro maior que 0"
            if self.lm:
                msg = self.lm.get_string("settings_view.formatting_card.gpu_layers_invalid", default=msg)
            self.tf_slm_gpu_layers.error_text = msg
            return False

    def validate_fields(self) -> bool:
        return self.validate_slm_gpu_layers(self.tf_slm_gpu_layers.value)

    def get_values(self) -> Dict[str, Any]:
        return {
            "xai_slm_device": self.dd_slm_device.value,
            "xai_slm_gpu_layers": int(self.tf_slm_gpu_layers.value) if self.tf_slm_gpu_layers.value else 16
        }

    def set_values(self, values: Dict[str, Any]):
        self.dd_slm_device.value = values.get("xai_slm_device", "cpu")
        self.tf_slm_gpu_layers.value = str(values.get("xai_slm_gpu_layers", "16"))
        self.tf_slm_gpu_layers.disabled = (self.dd_slm_device.value != "mixed")

    def update_translations(self, lm: LocaleManager):
        self.lm = lm
        self.lbl_slm_title.value = lm.get_string("settings_view.formatting_card.slm_title", default="Hardware e Processamento do Modelo (SLM)")
        self.lbl_slm_device.value = lm.get_string("settings_view.formatting_card.slm_device", default="Dispositivo de Execução (Device)")
        self.lbl_slm_gpu_layers.value = lm.get_string("settings_view.formatting_card.slm_gpu_layers", default="Camadas offload para GPU")
