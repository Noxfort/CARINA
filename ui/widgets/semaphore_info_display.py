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

# File: ui/widgets/semaphore_info_display.py
# Author: Gabriel Moraes
# Date: February 19, 2026

import flet as ft
import logging
from typing import Dict
from ui.handlers.locale_manager import LocaleManager

class SemaphoreInfoDisplayWidget(ft.Column):
    """
    Um widget que exibe os dados estáticos, a fase e o estado das vias de um semáforo.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__()
        
        self.locale_manager = locale_manager
        self.semaphore_id_text_template = ""
        
        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.]")
        
        self.semaphore_id_text = ft.Text(weight=ft.FontWeight.BOLD)
        self.maturity_phase_label = ft.Text(size=12, color=ft.Colors.WHITE54)
        self.maturity_phase_text = ft.Text("---", weight=ft.FontWeight.BOLD, size=16)
        
        self.lane_states_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lane_states_column = ft.Column(
            scroll=ft.ScrollMode.ADAPTIVE,
            spacing=4
        )
        self.lane_states_container = ft.Container(
            content=self.lane_states_column,
            height=120,
            border=ft.border.all(1, ft.Colors.WHITE12),
            border_radius=5,
            padding=ft.padding.all(8)
        )
        
        self.green_time_field = ft.TextField(
            value="--", 
            text_align=ft.TextAlign.CENTER, 
            read_only=True,
            height=40,
            text_size=12,
            input_filter=numeric_filter
        )
        self.yellow_time_field = ft.TextField(
            value="--", 
            text_align=ft.TextAlign.CENTER, 
            read_only=True,
            height=40,
            text_size=12,
            input_filter=numeric_filter
        )

        self.controls = [
            ft.Row(
                [ft.Icon(ft.Icons.TRAFFIC_ROUNDED), self.semaphore_id_text], 
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row(
                [
                    ft.Icon(ft.Icons.SCHOOL_ROUNDED, color=ft.Colors.WHITE54, size=30),
                    ft.Column(
                        [self.maturity_phase_label, self.maturity_phase_text],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15
            ),
            ft.Divider(height=10),
            self.lane_states_title,
            self.lane_states_container,
            ft.Divider(height=10),
            self.green_time_field,
            self.yellow_time_field,
        ]
        self.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.spacing = 8

    def did_mount(self):
        self.update_translations(self.locale_manager)
        if self.page: self.update()

    def update_translations(self, lm: LocaleManager):
        self.semaphore_id_text_template = lm.get_string("dashboard_view.semaphore_controls_title_prefix")
        self.maturity_phase_label.value = lm.get_string("dashboard_view.maturity_phase_label")
        self.lane_states_title.value = lm.get_string("dashboard_view.lane_states_title")
        self.green_time_field.label = lm.get_string("dashboard_view.green_time")
        self.yellow_time_field.label = lm.get_string("dashboard_view.yellow_time")
        if self.page: self.update()

    def update_info(self, semaphore_id: str, phase_key: str, semaphore_data: Dict):
        """
        Atualiza as informações do painel.
        Crucial: Deve chamar self.update() ao final para renderizar as mudanças.
        """
        self.semaphore_id_text.value = f"{self.semaphore_id_text_template} {semaphore_id}"
        
        # Update Maturity Phase
        translation_key = f"maturity_phases.{phase_key.upper()}"
        translated_phase = self.locale_manager.get_string(translation_key)
        if translated_phase == translation_key:
            translated_phase = self.locale_manager.get_string("maturity_phases.UNKNOWN")
        self.maturity_phase_text.value = translated_phase
        
        phase_colors = {"ADULT": ft.Colors.GREEN_ACCENT_400, "TEEN": ft.Colors.AMBER_ACCENT_400, "CHILD": ft.Colors.CYAN_ACCENT_400}
        self.maturity_phase_text.color = phase_colors.get(phase_key.upper(), ft.Colors.WHITE)
        
        # Updates Track Status (Lamps)
        self.lane_states_column.controls.clear()
        
        lanes_state = semaphore_data.get("lanes_state", {})
        if not lanes_state:
            self.lane_states_column.controls.append(ft.Text("Nenhum dado de via disponível.", italic=True, size=12))
        else:
            for lane_id, state in sorted(lanes_state.items()):
                state_map = {
                    # Green States
                    'G': ft.Colors.GREEN_ACCENT_700, 'g': ft.Colors.GREEN_ACCENT_700,
                    # Yellow/Transitional States
                    'Y': ft.Colors.AMBER_ACCENT_700, 'y': ft.Colors.AMBER_ACCENT_700, 's': ft.Colors.AMBER_ACCENT_700,
                    # Red/Stop States
                    'R': ft.Colors.RED_ACCENT_700, 'r': ft.Colors.RED_ACCENT_700,
                    # Off or Unknown States (Secure Fallback)
                    'u': ft.Colors.RED_ACCENT_700, 'o': ft.Colors.RED_ACCENT_700
                }
                color = state_map.get(str(state), ft.Colors.RED_ACCENT_700)

                lane_row = ft.Row(
                    controls=[
                        ft.Container(width=14, height=14, bgcolor=color, border_radius=7),
                        ft.Text(str(lane_id), font_family="monospace", size=12) 
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                )
                self.lane_states_column.controls.append(lane_row)
        
        # Critical protection against Event Loop termination (Graceful Shutdown)
        try:
            if self.page:
                self.update()
        except AssertionError:
            # Interface control has already been dropped from the page
            pass
        except RuntimeError as e:
            if "Event loop is closed" in str(e) or "shutdown" in str(e):
                pass
            else:
                logging.error(f"[SemaphoreInfoDisplay] Erro inesperado ao atualizar UI: {e}")
        except Exception:
            pass