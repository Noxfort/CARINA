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

# File: ui/widgets/traffic_light_widget.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define a classe TrafficLightWidget.

Esta é a versão final simplificada. É um componente 'burro' cuja única
responsabilidade é exibir visualmente um estado de luz que é comandado
por um controlador externo. A lógica de clique foi removida para ser
centralizada no widget pai.
"""

import flet as ft
import logging
from typing import Callable

class TrafficLightWidget(ft.Container):
    """
    Um widget visual que representa um semáforo.
    """
    def __init__(
        self,
        semaphore_id: str,
        initial_state: str = "RED"
    ):
        super().__init__()
        
        self.semaphore_id = semaphore_id
        self.current_state = initial_state

        self.width = 20
        self.height = 50
        self.bgcolor = ft.Colors.BLACK
        self.border_radius = 5
        self.padding = 4

        self.lights = {
            "RED": self._criar_luz(ft.Colors.RED),
            "YELLOW": self._criar_luz(ft.Colors.AMBER),
            "GREEN": self._criar_luz(ft.Colors.GREEN),
        }

        self.content = ft.Column(
            controls=list(self.lights.values()),
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        self._update_visuals()

    def _criar_luz(self, cor: str) -> ft.Container:
        """Cria um único container circular para uma luz."""
        return ft.Container(
            width=12,
            height=12,
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.2, cor),
            animate=ft.Animation(100, "ease")
        )

    def _update_visuals(self):
        """Atualiza a cor das luzes com base no estado atual."""
        for state, light_container in self.lights.items():
            base_color = getattr(ft.Colors, state)
            light_container.bgcolor = ft.Colors.with_opacity(0.2, base_color)
        
        # The "OFF" state now simply doesn't turn on any lights
        if self.current_state in self.lights:
            light_to_turn_on = self.lights[self.current_state]
            base_color = getattr(ft.Colors, self.current_state)
            light_to_turn_on.bgcolor = base_color
        
        if self.page:
            try: self.update()
            except Exception: pass

    def set_state(self, new_state: str):
        """
        Método público para alterar o estado do semáforo.
        """
        valid_states = ["RED", "YELLOW", "GREEN", "ALERT", "OFF"]
        if new_state not in valid_states:
            logging.warning(f"Tentativa de definir estado inválido '{new_state}' para o semáforo {self.semaphore_id}")
            return
        
        visual_state = "YELLOW" if new_state == "ALERT" else new_state

        if self.current_state != visual_state:
            self.current_state = visual_state
            self._update_visuals()

    def apply_telemetry(self, telemetry_data: dict, overrides: dict, blink_toggle: bool):
        """
        Applies new telemetry data ensuring OCP. The MapAnimator doesn't need to know
        how a traffic light processes its data.
        """
        override_state = overrides.get(self.semaphore_id)
        if override_state:
            if override_state == 'ALERT':
                self.set_state('YELLOW' if blink_toggle else 'OFF')
            elif override_state == 'OFF':
                self.set_state('OFF')
        else:
            semaforo_data = telemetry_data.get(self.semaphore_id, {})
            new_state = semaforo_data.get("display_state", "RED")
            self.set_state(new_state)