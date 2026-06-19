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

# File: ui/builders/map_controls_assembler.py
# Author: Gabriel Moraes
# Date: October 1, 2025

import flet as ft
import flet.canvas as cv
from typing import Dict, List, Tuple, Any
from ui.builders.map_element_factory import MapElementFactory
from ui.interfaces.map_protocols import MapDrawerProtocol

class MapControlsAssembler:
    """
    Assembles Flet Canvas and Interactive elements for the Map Stack.
    """
    def assemble_map_controls(
        self,
        drawer: MapDrawerProtocol,
        canvas: cv.Canvas
    ) -> Tuple[List[ft.Control], Dict[str, Any]]:
        """
        Creates control instances using the element factory and returns them as a Stack-ready list.
        """
        interactive_widgets_map: Dict[str, Any] = {}
        widgets_list = []
        
        for node_id, node_data in drawer.nodes.items():
            node_type = node_data.get('type')
            if node_type:
                tx, ty = drawer.transform_point(node_data['x'], node_data['y'])
                widget = MapElementFactory.create_element(node_type, node_id, tx, ty)
                
                if widget:
                    widgets_list.append(widget)
                    if hasattr(widget, 'apply_telemetry'):
                        interactive_widgets_map[node_id] = widget

        stack_controls = [canvas]
        stack_controls.extend(widgets_list)
        
        return stack_controls, interactive_widgets_map
