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

# File: ui/builders/map_element_factory.py
# Author: Gabriel Moraes
# Date: June 13, 2026

import flet as ft
from typing import Dict, Any, Callable, Type
from ui.widgets.traffic_light_widget import TrafficLightWidget

class MapElementFactory:
    """
    Factory for creating interactive map elements (OCP compliant).
    New elements can be registered without modifying this class.
    """
    _registry: Dict[str, Callable[[str, float, float], ft.Control]] = {}

    @classmethod
    def register_element(cls, node_type: str, builder: Callable[[str, float, float], ft.Control]):
        cls._registry[node_type] = builder

    @classmethod
    def create_element(cls, node_type: str, node_id: str, tx: float, ty: float) -> ft.Control | None:
        builder = cls._registry.get(node_type)
        if builder:
            return builder(node_id, tx, ty)
        return None

# Register known elements
def _build_traffic_light(node_id: str, tx: float, ty: float) -> ft.Control:
    widget = TrafficLightWidget(semaphore_id=node_id)
    widget.left = tx - (widget.width / 2)
    widget.top = ty - (widget.height / 2)
    return widget

MapElementFactory.register_element('traffic_light', _build_traffic_light)
