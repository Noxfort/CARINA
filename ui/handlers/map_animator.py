# File: ui/handlers/map_animator.py (FIXED)
# Author: Gabriel Moraes
# Date: October 1, 2025

"""
Define a classe MapAnimator.

Nesta versão, ele assume a responsabilidade de atualizar TODOS os componentes
visuais de alta frequência (mapa e painel de detalhes) dentro do seu loop
controlado, para evitar a sobrecarga da thread da UI.
"""

import flet as ft
import flet.canvas as cv
import logging
import threading
import time
import queue
from typing import Dict, Any, TYPE_CHECKING

from ui.widgets.traffic_light_widget import TrafficLightWidget

# Prevents circular import at runtime, but allows the code editor to understand types
if TYPE_CHECKING:
    from ui.views.dashboard_view import DashboardView
    from ui.widgets.control_panel_widget import ControlPanelWidget

class MapAnimator:
    """
    Gerencia uma thread para aplicar atualizações visuais de alta frequência.
    """
    def __init__(
        self,
        widget_to_update: ft.Control,
        # --- CHANGE 1: Receive references to Dashboard and Control Panel ---
        dashboard_view: 'DashboardView',
        control_panel: 'ControlPanelWidget',
        edge_paths: Dict[str, cv.Path] = None,
        semaforo_widgets: Dict[str, TrafficLightWidget] = None,
        interval: float = 0.5
    ):
        self.widget = widget_to_update
        self.dashboard_view = dashboard_view
        self.control_panel = control_panel
        self.edge_paths = edge_paths or {}
        self.semaforo_widgets = semaforo_widgets or {}
        self.interval = interval
        
        self.thread = None
        self.is_running = False
        
        self.data_lock = threading.Lock()
        self.latest_congestion_data: Dict[str, Dict] = {}
        self.latest_panel_data: Dict[str, Dict] = {}

        self.command_queue = queue.Queue()
        self.overrides: Dict[str, str] = {}
        self.blink_toggle = False
        
        # Adicionando throttling para atualizações de congestão
        self.last_update_time = 0
        self.throttle_interval = 0.1  # 100ms entre atualizações

    def start(self):
        if not self.thread or not self.thread.is_alive():
            self.is_running = True
            self.thread = threading.Thread(target=self._updater_loop, daemon=True)
            self.thread.start()
            logging.info("[MapAnimator] Thread de animação (modo renderização) iniciada.")

    def stop(self):
        self.is_running = False
        logging.info("[MapAnimator] Sinal para parar a thread de animação enviado.")

    def update_data(self, data_packet: dict):
        with self.data_lock:
            if data_packet.get("type") == "initial_map_geometry":
                 self.latest_congestion_data = data_packet.get("congestion_update", {})
            elif data_packet.get("type") == "congestion_update":
                self.latest_congestion_data = data_packet.get("payload", {})
            
            self.latest_panel_data = data_packet.get("panel_data", {})

    def _get_precise_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> str:
        """
        Converte um valor de congestão em uma cor hexadecimal com alta precisão.
        
        Args:
            value: Valor de congestão a ser convertido
            max_expected_value: Valor máximo esperado (para normalização)
            
        Returns:
            String hexadecimal representando a cor apropriada
        """
        # Normaliza o valor entre 0 e 1, considerando o valor máximo esperado
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        
        # Escala de cores de verde (baixa congestão) a vermelho (alta congestão)
        # usando uma transição suave e contínua
        if normalized <= 0.5:
            # Transição de verde (0,255,0) para amarelo (255,255,0) até 50% de congestão
            r = int(2 * normalized * 255)  # 0->255
            g = 255  # Constante
            b = 0    # Constante
        else:
            # Transição de amarelo (255,255,0) para vermelho (255,0,0) acima de 50%
            r = 255  # Constante
            g = int((1 - (normalized - 0.5) * 2) * 255)  # 255->0
            b = 0    # Constante
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _get_color_for_congestion(self, value: float, max_value: float = 100.0) -> str:
        # Chamando a nova função precisa para manter compatibilidade
        return self._get_precise_color_for_congestion(value, max_value)

    def _updater_loop(self):
        """O loop que lê os dados mais recentes e aplica TODAS as atualizações visuais."""
        while self.is_running:
            try:
                self.blink_toggle = not self.blink_toggle

                with self.data_lock:
                    congestion_to_render = self.latest_congestion_data.copy()
                    panel_data_to_render = self.latest_panel_data.copy()

                # Aplicar throttling para atualizações de congestão
                current_time = time.time()
                should_update_congestion = (current_time - self.last_update_time) >= self.throttle_interval
                
                if should_update_congestion and self.edge_paths and congestion_to_render:
                    for edge_id, path_object in self.edge_paths.items():
                        if edge_id in congestion_to_render:
                            congestion_value = congestion_to_render[edge_id]
                            if isinstance(congestion_value, dict):
                                congestion_value = congestion_value.get('congestion', 0.0)
                            new_color = self._get_precise_color_for_congestion(congestion_value)
                        else:
                            new_color = ft.colors.BLUE_900 # Base map color for empty streets
                            
                        if path_object.paint.color != new_color:
                            path_object.paint.color = new_color
                    
                    # Atualizar o tempo da última atualização
                    self.last_update_time = current_time

                if self.semaforo_widgets and panel_data_to_render:
                    for semaforo_id, widget in self.semaforo_widgets.items():
                        override_state = self.overrides.get(semaforo_id)
                        if override_state:
                            if override_state == 'ALERT':
                                widget.set_state('YELLOW' if self.blink_toggle else 'OFF')
                            elif override_state == 'OFF':
                                widget.set_state('OFF')
                        else:
                            semaforo_data = panel_data_to_render.get(semaforo_id, {})
                            new_state = semaforo_data.get("display_state", "RED")
                            widget.set_state(new_state)

                # --- CHANGE 2: New responsibility - Update details pane ---
                # Access the state directly from the DashboardView to know which item is selected
                selected_id = getattr(self.dashboard_view, 'selected_semaphore_id', None)
                
                # Only updates the panel if it is visible and a traffic light is selected
                if selected_id and getattr(self.control_panel, 'specific_controls', None) and self.control_panel.specific_controls.visible:
                    semaphore_data = panel_data_to_render.get(selected_id, {})
                    
                    # Security check for maturity_phases dictionary
                    phases_dict = getattr(self.dashboard_view, 'maturity_phases', {})
                    phase = phases_dict.get(selected_id, "UNKNOWN") if phases_dict else "UNKNOWN"
                    
                    mode = getattr(self.dashboard_view, 'current_mode', "UNKNOWN")
                    
                    # Commands update of the details panel (this will call .update() internally)
                    self.control_panel.exibir_controles_semaforo(
                        selected_id,
                        semaphore_data,
                        phase,
                        mode
                    )
                # --- END OF CHANGE 2 ---

                # Major map update still required
                if self.widget and getattr(self.widget, 'page', None):
                    self.widget.update()
                
                time.sleep(self.interval)

            except AssertionError:
                # Flet raises AssertionError when trying to update something that is not already on the page
                logging.info("[MapAnimator Thread] Interface gráfica foi descartada. Encerrando o loop suavemente.")
                self.is_running = False
                break
            except RuntimeError as e:
                # Protection against "Event loop is closed"
                if "Event loop is closed" in str(e) or "shutdown" in str(e):
                    logging.info("[MapAnimator Thread] Event Loop do Flet encerrado. Parando animações.")
                    self.is_running = False
                    break
                else:
                    logging.error(f"[MapAnimator Thread] Erro de Runtime inesperado: {e}")
            except Exception as e:
                logging.error(f"[MapAnimator Thread] Erro: {e}. Encerrando a thread.", exc_info=True)
                self.is_running = False
                break