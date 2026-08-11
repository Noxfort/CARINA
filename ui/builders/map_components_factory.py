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

# File: ui/builders/map_components_factory.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import flet as ft
import flet.canvas as cv
from typing import Dict, List, Callable, Any, Tuple

from ui.interfaces.map_protocols import (
    InteractionHandlerProtocol,
    StreetInteractionHandlerProtocol,
    EventRouterProtocol,
    MapDrawerProtocol,
    MapStateManagerProtocol,
    MapAnimatorProtocol,
    MapViewportManagerProtocol,
    MapControlsAssemblerProtocol
)

class MapComponentsFactory:
    """
    Factory to instantiate concrete map sub-components,
    preserving DIP by isolating live_canvas_map_widget.py from concrete imports.
    """
    @staticmethod
    def create_viewport_manager() -> MapViewportManagerProtocol:
        from ui.managers.map_viewport_manager import MapViewportManager
        return MapViewportManager()

    @staticmethod
    def create_controls_assembler() -> MapControlsAssemblerProtocol:
        from ui.builders.map_controls_assembler import MapControlsAssembler
        return MapControlsAssembler()

    @staticmethod
    def create_interaction_handler(viewport_width: float, viewport_height: float, on_update: Callable[[], None]) -> InteractionHandlerProtocol:
        from ui.handlers.map_interaction_handler import MapInteractionHandler
        return MapInteractionHandler(
            base_width=viewport_width,
            base_height=viewport_height,
            on_update_callback=on_update
        )

    @staticmethod
    def create_street_interaction_handler() -> StreetInteractionHandlerProtocol:
        from ui.handlers.street_interaction_handler import StreetInteractionHandler
        return StreetInteractionHandler(on_street_selected=None)

    @staticmethod
    def create_event_router(
        interaction_handler: InteractionHandlerProtocol,
        street_interaction_handler: StreetInteractionHandlerProtocol,
        on_update: Callable[[], None],
        on_semaphore_click: Callable[[str | None], None],
        on_street_click: Callable[[str | None], None]
    ) -> EventRouterProtocol:
        from ui.router.map_event_router import MapEventRouter
        return MapEventRouter(
            interaction_handler=interaction_handler,
            street_interaction_handler=street_interaction_handler,
            safe_update_callback=on_update,
            on_semaphore_click=on_semaphore_click,
            on_street_click=on_street_click
        )

    @staticmethod
    def create_drawer(nodes: Dict, edges: List) -> MapDrawerProtocol:
        from ui.renderers.map_drawer import MapDrawer
        return MapDrawer(nodes, edges)

    @staticmethod
    def create_state_manager(canvas: cv.Canvas, stack: ft.Stack, edge_paths: Dict, interactive_widgets: Dict) -> MapStateManagerProtocol:
        from ui.managers.map_state_manager import MapStateManager
        return MapStateManager(
            canvas=canvas,
            stack=stack,
            edge_paths=edge_paths,
            interactive_widgets=interactive_widgets
        )

    @staticmethod
    def create_animator(
        widget_to_update: ft.Container,
        get_panel_state_callback: Callable[[], Dict],
        on_panel_update_callback: Callable[[str, Dict, str, str], None],
        edge_paths: Dict,
        interactive_widgets: Dict,
        topology_edges: List
    ) -> MapAnimatorProtocol:
        from ui.animators.map_animator import MapAnimator
        return MapAnimator(
            widget_to_update=widget_to_update,
            get_panel_state_callback=get_panel_state_callback,
            on_panel_update_callback=on_panel_update_callback,
            edge_paths=edge_paths,
            semaforo_widgets=interactive_widgets,
            topology_edges=topology_edges
        )
