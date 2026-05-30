# File: ui/widgets/live_canvas_map_widget.py (RESPONSIVE)
# Author: Gabriel Moraes
# Date: October 1, 2025

"""
Define o LiveCanvasMapWidget.

Versão responsiva: usa expand=True para preencher o espaço disponível,
mas calcula dimensões concretas para o Canvas no momento da montagem.
Recalcula automaticamente ao redimensionar a janela.
"""

import flet as ft
import flet.canvas as cv
import logging
from typing import Dict, Any, Callable, Tuple, TYPE_CHECKING

from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.handlers.map_drawer import MapDrawer
from ui.handlers.map_animator import MapAnimator
from ui.handlers.street_interaction_handler import StreetInteractionHandler
from ui.handlers.map_state_manager import MapStateManager
from ui.widgets.traffic_light_widget import TrafficLightWidget

# Prevents circular import by allowing type annotations
if TYPE_CHECKING:
    from ui.views.dashboard_view import DashboardView
    from ui.widgets.control_panel_widget import ControlPanelWidget

# Estimated pixels consumed by UI chrome (AppBar, Tabs, padding, ControlPanel)
_CHROME_WIDTH_OFFSET = 420   # Control panel (~380) + padding/borders
_CHROME_HEIGHT_OFFSET = 160  # AppBar + Tabs + padding

class LiveCanvasMapWidget(ft.Container):
    """
    Um widget que orquestra especialistas para desenhar e animar um mapa.
    Responsivo: preenche o espaço disponível e recalcula ao redimensionar.
    """
    def __init__(
        self,
        dashboard_view: 'DashboardView',
        control_panel: 'ControlPanelWidget',
        on_semaphore_click: Callable[[str | None], None] = None,
        on_street_click: Callable[[str | None], None] = None
    ):
        super().__init__(
            expand=True, bgcolor="#F7F7F7", border_radius=10,
            alignment=ft.alignment.center,
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )
        
        self.dashboard_view = dashboard_view
        self.control_panel = control_panel
        
        self.on_semaphore_click = on_semaphore_click
        self.on_street_click = on_street_click
        
        # Current effective dimensions (calculated on mount / resize)
        self._canvas_width: int = 1280
        self._canvas_height: int = 720
        
        self.interaction_handler = MapInteractionHandler(
            base_width=self._canvas_width, 
            base_height=self._canvas_height, 
            on_update_callback=self._safe_update
        )
        self.last_mouse_x = self._canvas_width / 2
        self.last_mouse_y = self._canvas_height / 2
        self.street_interaction_handler = StreetInteractionHandler(on_street_selected=self._handle_street_click)
        self.drawer: MapDrawer | None = None
        self.animator: MapAnimator | None = None
        self.map_state_manager: MapStateManager | None = None
        
        # Pending map data (stored if initialize_map is called before mount)
        self._pending_map_data: Tuple | None = None
        self._is_map_built = False
        
        self.canvas = cv.Canvas(shapes=[], width=self._canvas_width, height=self._canvas_height)
        self.map_stack = ft.Stack(
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
        )
        
        def _on_hover(e: ft.HoverEvent):
            self.last_mouse_x = e.local_x
            self.last_mouse_y = e.local_y

        self.gesture_detector = ft.GestureDetector(
            content=self.map_stack,
            on_hover=_on_hover,
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=lambda e: self.interaction_handler.handle_zoom(e, self.last_mouse_x, self.last_mouse_y),
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_tap_down=self._handle_map_tap
        )
        
        self.content = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text("Aguardando Conexão com o Cenário...")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        self.did_mount = self._on_mount
        self.will_unmount = self.on_unmount

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _on_mount(self):
        """Called when the widget is attached to the page. Hooks resize and processes pending data."""
        # Hook into page resize
        if self.page:
            original_on_resized = self.page.on_resized
            def _handle_resized(e):
                if original_on_resized and callable(original_on_resized):
                    original_on_resized(e)
                self._rebuild_for_current_size()
            self.page.on_resized = _handle_resized
        
        # If map data arrived before mount, build now with real dimensions
        if self._pending_map_data and not self._is_map_built:
            self._calculate_dimensions()
            self._build_map(self._pending_map_data)
            self._pending_map_data = None

    def _calculate_dimensions(self):
        """Calculates canvas dimensions from the current page size."""
        if self.page:
            pw = self.page.width or 1280
            ph = self.page.height or 800
            self._canvas_width = max(int(pw - _CHROME_WIDTH_OFFSET), 400)
            self._canvas_height = max(int(ph - _CHROME_HEIGHT_OFFSET), 300)
        # else: keep defaults 1280x720

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def initialize_map(self, map_data: Tuple | None):
        """
        Receives map geometry. If the widget is already mounted, builds immediately.
        Otherwise, stores data and defers to did_mount.
        """
        if not map_data:
            self.content = ft.Text("ERRO: Dados de geometria do mapa não foram fornecidos.", color=ft.Colors.RED)
            if self.page: self.update()
            return

        if self.page:
            # Already mounted — build immediately with real dimensions
            self._calculate_dimensions()
            self._build_map(map_data)
        else:
            # Not mounted yet — defer
            self._pending_map_data = map_data
            logging.info("[LiveCanvasMap] Map data received before mount. Deferred.")

    def clear_all_selections(self):
        if self.map_state_manager:
            self.map_state_manager.set_selection(item_type=None, item_id=None)
            self._safe_update()

    def update_data(self, data_packet: dict):
        if self.animator:
            self.animator.update_data(data_packet)
    
    def on_unmount(self):
        if self.animator: self.animator.stop()

    # ------------------------------------------------------------------
    # Internal: Build / Rebuild
    # ------------------------------------------------------------------
    def _build_map(self, map_data: Tuple):
        """Builds (or rebuilds) the entire map canvas with current dimensions."""
        nodes, edges, _ = map_data
        
        # Store raw data for rebuilds on resize
        self._pending_map_data = map_data
        
        # Stop existing animator if rebuilding
        if self.animator:
            self.animator.stop()

        # Fresh canvas with concrete dimensions
        self.canvas = cv.Canvas(shapes=[], width=self._canvas_width, height=self._canvas_height)
        
        # Update interaction handler dimensions
        self.interaction_handler.base_width = self._canvas_width
        self.interaction_handler.base_height = self._canvas_height
        
        # Calculate transformations and draw
        self.drawer = MapDrawer(nodes, edges)
        self.drawer.calculate_transformations(self._canvas_width, self._canvas_height)
        
        edge_paths = self.drawer.draw_initial_map(self.canvas, stroke_width=5.0)
        self.street_interaction_handler.load_paths(edge_paths)
        
        # Traffic light widgets
        traffic_light_widgets_map: Dict[str, TrafficLightWidget] = {}
        traffic_light_widgets_list = []
        for node_id, node_data in self.drawer.nodes.items():
            if node_data.get('type') == 'traffic_light':
                tx, ty = self.drawer._transform_point(node_data['x'], node_data['y'])
                widget = TrafficLightWidget(semaphore_id=node_id)
                widget.left, widget.top = tx - (widget.width / 2), ty - (widget.height / 2)
                traffic_light_widgets_list.append(widget)
                traffic_light_widgets_map[node_id] = widget

        self.map_stack.controls = [self.canvas, *traffic_light_widgets_list]
        
        self.map_state_manager = MapStateManager(
            canvas=self.canvas, stack=self.map_stack,
            edge_paths=edge_paths, traffic_light_widgets=traffic_light_widgets_map
        )

        self.animator = MapAnimator(
            widget_to_update=self,
            dashboard_view=self.dashboard_view,
            control_panel=self.control_panel,
            edge_paths=edge_paths,
            semaforo_widgets=traffic_light_widgets_map,
            interval=0.5
        )
        
        self.animator.start()
        self._is_map_built = True
        
        self.content = self.gesture_detector
        if self.page: self.update()
        logging.info(f"[LiveCanvasMap] Mapa inicializado ({self._canvas_width}x{self._canvas_height}).")

    def _rebuild_for_current_size(self):
        """Called on window resize. Recalculates dimensions and rebuilds the map."""
        if not self._is_map_built or not self._pending_map_data:
            return
        
        old_w, old_h = self._canvas_width, self._canvas_height
        self._calculate_dimensions()
        
        # Only rebuild if size changed significantly (>20px) to avoid churn
        if abs(self._canvas_width - old_w) > 20 or abs(self._canvas_height - old_h) > 20:
            logging.info(f"[LiveCanvasMap] Resize detectado: {old_w}x{old_h} → {self._canvas_width}x{self._canvas_height}. Reconstruindo...")
            self._build_map(self._pending_map_data)

    def _safe_update(self):
        """Wrapper to call update only when mounted."""
        if self.page:
            try:
                self.update()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------
    def _handle_street_click(self, edge_id: str | None):
        if self.map_state_manager:
            self.map_state_manager.set_selection(item_type='street', item_id=edge_id)
            self._safe_update()
        if self.on_street_click: self.on_street_click(edge_id)

    def _handle_semaphore_click(self, semaphore_id: str):
        if not self.map_state_manager: return
        current_selection = self.map_state_manager.selected_semaphore_id
        new_selection_id = semaphore_id if current_selection != semaphore_id else None
        self.map_state_manager.set_selection(item_type='semaphore', item_id=new_selection_id)
        self._safe_update()
        if self.on_semaphore_click: self.on_semaphore_click(new_selection_id)

    def _handle_map_tap(self, e: ft.TapEvent):
        scale = self.interaction_handler.scale.scale
        offset = self.interaction_handler.offset
        center_x, center_y = self._canvas_width / 2, self._canvas_height / 2
        offset_x_px = offset.x * self._canvas_width
        offset_y_px = offset.y * self._canvas_height
        unpanned_x, unpanned_y = e.local_x - offset_x_px, e.local_y - offset_y_px
        map_space_x = ((unpanned_x - center_x) / scale) + center_x
        map_space_y = ((unpanned_y - center_y) / scale) + center_y

        if self.map_state_manager and self.map_state_manager.traffic_light_widgets:
            for tl_id, widget in self.map_state_manager.traffic_light_widgets.items():
                left, top = widget.left, widget.top
                right, bottom = left + widget.width, top + widget.height
                if left <= map_space_x <= right and top <= map_space_y <= bottom:
                    self._handle_semaphore_click(tl_id)
                    return

        self.street_interaction_handler.handle_click(map_space_x, map_space_y, scale)

    def set_semaphore_override_state(self, semaphore_id: str, state: str):
        if self.map_state_manager and self.animator:
            widget = self.map_state_manager.traffic_light_widgets.get(semaphore_id)
            if widget:
                command = {"id": semaphore_id, "state": state}
                self.animator.command_queue.put(command)