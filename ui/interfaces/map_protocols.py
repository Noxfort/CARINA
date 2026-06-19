# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
# Licensed under GNU GPL v3 or later.

# File: ui/interfaces/map_protocols.py

import flet as ft
import flet.canvas as cv
from typing import Dict, List, Tuple, Any, Protocol, runtime_checkable

@runtime_checkable
class InteractionHandlerProtocol(Protocol):
    """Protocol defining the map pan/zoom interaction contract."""
    scale: ft.Scale
    offset: ft.Offset
    base_width: float
    base_height: float

    def center_and_reset_zoom(self) -> None:
        ...

    def handle_pan_update(self, e: ft.DragUpdateEvent) -> None:
        ...

    def handle_zoom(self, e: ft.ScrollEvent, mouse_x: float = None, mouse_y: float = None) -> None:
        ...

    def get_map_coordinates(self, local_x: float, local_y: float) -> Tuple[float, float]:
        ...


@runtime_checkable
class StreetInteractionHandlerProtocol(Protocol):
    """Protocol defining street selection and click detection contract."""
    edge_paths: Dict[str, cv.Path]
    selected_edge_id: str | None

    def load_paths(self, edge_paths: Dict[str, cv.Path]) -> None:
        ...

    def handle_click(self, click_x: float, click_y: float, current_scale: float) -> None:
        ...


@runtime_checkable
class EventRouterProtocol(Protocol):
    """Protocol defining how events are dispatched from the map."""
    def handle_map_tap(self, e: ft.TapEvent) -> None:
        ...

    def handle_street_click(self, street_id: str | None) -> None:
        ...

    def set_semaphore_override_state(self, semaphore_id: str, state: str) -> None:
        ...

    def set_street_override_state(self, street_id: str, state: str) -> None:
        ...

    def attach_managers(self, map_state_manager: Any, animator: Any) -> None:
        ...


@runtime_checkable
class MapDrawerProtocol(Protocol):
    """Protocol defining the vector map rendering contract."""
    nodes: Dict[str, Dict]
    edges: List[Dict]

    def calculate_transformations(self, view_width: int, view_height: int) -> None:
        ...

    def draw_initial_map(self, canvas: cv.Canvas, stroke_width: float) -> Dict[str, cv.Path]:
        ...

    def transform_point(self, sumo_x: float, sumo_y: float) -> Tuple[float, float]:
        ...


@runtime_checkable
class MapStateManagerProtocol(Protocol):
    """Protocol defining selection state management on the map."""
    def set_selection(self, item_type: str | None, item_id: str | None) -> None:
        ...


@runtime_checkable
class MapAnimatorProtocol(Protocol):
    """Protocol defining simulation animation contract."""
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def update_data(self, data_packet: dict) -> None:
        ...


@runtime_checkable
class MapViewportManagerProtocol(Protocol):
    """Protocol defining viewport dimension calculations."""
    width: int
    height: int
    def calculate_dimensions(self, page_width: float | None, page_height: float | None) -> Tuple[int, int]:
        ...


@runtime_checkable
class MapControlsAssemblerProtocol(Protocol):
    """Protocol defining interactive controls assembler."""
    def assemble_map_controls(
        self,
        drawer: MapDrawerProtocol,
        canvas: cv.Canvas
    ) -> Tuple[List[ft.Control], Dict[str, Any]]:
        ...
