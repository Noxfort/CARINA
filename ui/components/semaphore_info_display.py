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
from typing import Dict, Callable
from ui.handlers.locale_manager import LocaleManager
from ui.managers.alias_manager import AliasManager

class SemaphoreInfoDisplayWidget(ft.Column):
    """
    Um widget que exibe os dados estáticos, a fase e o estado das vias de um semáforo.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__()
        
        self.locale_manager = locale_manager
        self.alias_manager = AliasManager()
        self._current_semaphore_id = None
        self._lane_controls_map = {}
        self.semaphore_id_text_template = ""
        
        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.]")
        
        self.semaphore_id_text = ft.TextField(
            text_size=14,
            height=40,
            expand=True,
            on_submit=self._on_submit,
            on_blur=self._on_submit,
            tooltip="Pressione Enter para salvar"
        )
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
        
        # Green and Yellow time fields removed as per request

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
        ]
        self.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.spacing = 8

    def did_mount(self):
        self.update_translations(self.locale_manager)
        if self.page: self.update()

    def update_translations(self, lm: LocaleManager):
        self.semaphore_id_text_template = lm.get_string("dashboard_view.semaphore_controls_title_prefix")
        self.semaphore_id_text.label = self.semaphore_id_text_template
        self.maturity_phase_label.value = lm.get_string("dashboard_view.maturity_phase_label")
        self.lane_states_title.value = lm.get_string("dashboard_view.lane_states_title")
        if self.page: self.update()

    def update_info(self, semaphore_id: str, phase_key: str, semaphore_data: Dict):
        """
        Atualiza as informações do painel.
        Crucial: Deve chamar self.update() ao final para renderizar as mudanças.
        """
        if self._current_semaphore_id != semaphore_id:
            self._current_semaphore_id = semaphore_id
            self.semaphore_id_text.value = self.alias_manager.get_alias(semaphore_id)
        
        # Update Maturity Phase
        translation_key = f"maturity_phases.{phase_key.upper()}"
        translated_phase = self.locale_manager.get_string(translation_key)
        if translated_phase == translation_key:
            translated_phase = self.locale_manager.get_string("maturity_phases.UNKNOWN")
        self.maturity_phase_text.value = translated_phase
        
        phase_colors = {"ADULT": ft.Colors.GREEN_ACCENT_400, "TEEN": ft.Colors.AMBER_ACCENT_400, "CHILD": ft.Colors.CYAN_ACCENT_400}
        self.maturity_phase_text.color = phase_colors.get(phase_key.upper(), ft.Colors.WHITE)
        
        # Updates Track Status (Lamps)
        if self._current_semaphore_id != getattr(self, '_last_populated_sem_id', None):
            self.lane_states_column.controls.clear()
            self._lane_controls_map.clear()
            self._last_populated_sem_id = self._current_semaphore_id
        
        lanes_state = semaphore_data.get("lanes_state", {})
        if not lanes_state:
            if not self.lane_states_column.controls:
                self.lane_states_column.controls.append(ft.Text("Nenhum dado de via disponível.", italic=True, size=12))
        else:
            # Remove "Nenhum dado" message if real data arrives
            if len(self.lane_states_column.controls) == 1 and isinstance(self.lane_states_column.controls[0], ft.Text):
                self.lane_states_column.controls.clear()
                
            for lane_id, state in sorted(lanes_state.items()):
                state_map = {
                    'G': ft.Colors.GREEN_ACCENT_700, 'g': ft.Colors.GREEN_ACCENT_700,
                    'Y': ft.Colors.AMBER_ACCENT_700, 'y': ft.Colors.AMBER_ACCENT_700, 's': ft.Colors.AMBER_ACCENT_700,
                    'R': ft.Colors.RED_ACCENT_700, 'r': ft.Colors.RED_ACCENT_700,
                    'u': ft.Colors.RED_ACCENT_700, 'o': ft.Colors.RED_ACCENT_700
                }
                color = state_map.get(str(state), ft.Colors.RED_ACCENT_700)

                # Update existing row or create a new one
                if lane_id in self._lane_controls_map:
                    color_box = self._lane_controls_map[lane_id]
                    if color_box.bgcolor != color:
                        color_box.bgcolor = color
                        if self.page: color_box.update()
                else:
                    alias = self.alias_manager.get_alias(str(lane_id))
                    lane_text = ft.TextField(
                        value=alias,
                        text_size=12,
                        height=28,
                        expand=True,
                        content_padding=ft.padding.only(left=8, right=8),
                        border=ft.InputBorder.OUTLINE,
                        border_color=ft.Colors.WHITE24,
                        bgcolor=ft.Colors.WHITE10,
                        border_radius=4,
                        on_blur=lambda e, lid=str(lane_id): self._on_lane_alias_submit(e, lid),
                        on_submit=lambda e, lid=str(lane_id): self._on_lane_alias_submit(e, lid),
                        tooltip="Clique para renomear"
                    )
                    
                    color_box = ft.Container(width=14, height=14, bgcolor=color, border_radius=7)
                    self._lane_controls_map[lane_id] = color_box
                    
                    lane_row = ft.Row(
                        controls=[color_box, lane_text],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10
                    )
                    self.lane_states_column.controls.append(lane_row)
        
        # Critical protection against Event Loop termination (Graceful Shutdown)
        try:
            if self.page:
                self.maturity_phase_text.update()
                self.lane_states_column.update()
                if self._current_semaphore_id != getattr(self, '_last_rendered_id', None):
                    self.semaphore_id_text.update()
                    self._last_rendered_id = self._current_semaphore_id
        except AssertionError:
            pass
        except RuntimeError as e:
            if "Event loop is closed" not in str(e) and "shutdown" not in str(e):
                logging.error(f"[SemaphoreInfoDisplay] Erro inesperado ao atualizar UI: {e}")
        except Exception:
            pass

    def _on_submit(self, e):
        """Salva o novo nome (alias) para o semáforo."""
        if self._current_semaphore_id:
            self.alias_manager.set_alias(self._current_semaphore_id, self.semaphore_id_text.value)
            if self.page:
                self.page.snack_bar = ft.SnackBar(ft.Text("Nome do semáforo salvo com sucesso!"), bgcolor="green700")
                self.page.snack_bar.open = True
                self.page.update()

    def _on_lane_alias_submit(self, e, lane_id: str):
        """Salva o novo nome (alias) para uma via específica."""
        new_alias = e.control.value
        if new_alias:
            self.alias_manager.set_alias(lane_id, new_alias)
        else:
            # If empty, revert to original lane_id visually and remove alias
            e.control.value = lane_id
            e.control.update()
            self.alias_manager.set_alias(lane_id, "")
            
        if self.page:
            self.page.snack_bar = ft.SnackBar(ft.Text("Nome da via salvo com sucesso!"), bgcolor="green700")
            self.page.snack_bar.open = True
            self.page.update()