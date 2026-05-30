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

# File: ui/views/dashboard_view.py (FIXED: ID Robustness for Dashboard Data)
# Author: Gabriel Moraes
# Date: February 19, 2026

import flet as ft
from typing import Dict
import logging

from ui.widgets.control_panel_widget import ControlPanelWidget
from ui.widgets.live_canvas_map_widget import LiveCanvasMapWidget
from ui.clients.control_client import ControlClient
from ui.handlers.map_asset_loader import MapAssetLoader
from ui.handlers.locale_manager import LocaleManager

class DashboardView(ft.Container):
    def __init__(self, control_client: ControlClient, locale_manager: LocaleManager):
        super().__init__(expand=True)
        
        self.locale_manager = locale_manager
        self.latest_data_packet = {}
        self.current_mode = "Automático"
        self.selected_semaphore_id: str | None = None
        
        self.is_initialized = False
        self.maturity_phases: Dict[str, str] = {}

        self.control_panel = ControlPanelWidget(
            control_client=control_client,
            locale_manager=self.locale_manager,
            on_specific_command=self._handle_specific_command,
            on_details_close=self._handle_panel_close,
            on_mode_change=self._handle_mode_change
        )
        
        self.map_widget = LiveCanvasMapWidget(
            dashboard_view=self,
            control_panel=self.control_panel,
            on_semaphore_click=self._handle_semaphore_click,
            on_street_click=self._handle_street_click
        )
        
        self.content = ft.Row(
            controls=[
                ft.Container(content=self.map_widget, alignment=ft.alignment.center, expand=True),
                self.control_panel,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        
        self.current_mode = self.locale_manager.get_string("dashboard_view.mode_auto")

    def update_translations(self, lm: LocaleManager):
        self.current_mode = lm.get_string("dashboard_view.mode_auto")
        self.control_panel.update_translations(lm)
        if self.page: self.update()

    def update_live_data(self, data_packet: dict):
        """
        Recebe os dados em tempo real, processa a estrutura de maturidade e atualiza o mapa.
        """
        if not self.is_initialized and data_packet.get("type") == "initial_map_geometry":
            logging.info("[DashboardView] Inicializando mapa...")
            self.is_initialized = True
            
            asset_loader = MapAssetLoader()
            map_data = asset_loader.load_map_data()
            
            if map_data:
                nodes, _, _ = map_data
                traffic_light_ids = [node_id for node_id, data in nodes.items() if data.get('type') == 'traffic_light']
                self.maturity_phases = {tl_id: "UNKNOWN" for tl_id in traffic_light_ids}

            self.map_widget.initialize_map(map_data)
        
        # --- DATA MERGE CORRECTION ---
        # Instead of brutally overwriting the packet (which destroys data in separate queues), 
        # we selectively update internal UI caches.
        if "panel_data" in data_packet:
            self.latest_panel_data = data_packet["panel_data"]
        if "street_data" in data_packet:
            self.latest_street_data = data_packet["street_data"]
            
        # Extracts only the 'agent_maturity' dictionary to have the map {id: phase}.
        raw_maturity_data = data_packet.get("maturity_phases", {})
        if "agent_maturity" in raw_maturity_data:
            self.maturity_phases = raw_maturity_data["agent_maturity"]
        elif raw_maturity_data:
            self.maturity_phases = {
                k: v for k, v in raw_maturity_data.items() 
                if k != "run_id" and k != "scenario_name"
            }
            self.maturity_phases = {
                k: v for k, v in raw_maturity_data.items() 
                if k != "run_id" and k != "scenario_name"
            }
            
        # Check maturity to lock/unlock Global Controls
        if self.maturity_phases:
            all_adults = all(phase == "ADULT" for phase in self.maturity_phases.values())
            self.control_panel.global_controls.set_locked_state(not all_adults)
            
        if self.map_widget:
            self.map_widget.update_data(data_packet)

    def _handle_panel_close(self):
        self.selected_semaphore_id = None
        if self.map_widget:
            self.map_widget.clear_all_selections()

    def _handle_mode_change(self, mode: str):
        self.current_mode = mode
        if self.selected_semaphore_id:
            self.map_widget.clear_all_selections()
            self._handle_semaphore_click(self.selected_semaphore_id)

    def _handle_semaphore_click(self, semaphore_id: str | None):
        """
        Gerencia o clique no semáforo, recuperando dados com robustez de ID (com ou sem prefixo tl_).
        """
        self.selected_semaphore_id = semaphore_id
        
        if not self.control_panel: return
        if not semaphore_id:
            self.control_panel.ocultar_todos_detalhes()
            return

        # --- ID Robustness Logic ---
        # Create variations of the ID to search dictionary keys (ex: "tl_123" vs "123")
        possible_ids = [semaphore_id]
        if semaphore_id.startswith("tl_"):
            possible_ids.append(semaphore_id.replace("tl_", ""))
        else:
            possible_ids.append(f"tl_{semaphore_id}")

        # 1. Recovers the PHASE (Maturity)
        phase = "UNKNOWN"
        for pid in possible_ids:
            if pid in self.maturity_phases:
                phase = self.maturity_phases[pid]
                break
            
        # Commit log for terminal
        # print(f"[Dashboard] Click on '{semaphore_id}'. Tried IDs: {possible_ids}. Phase: {phase}")

        is_manual_mode = self.current_mode == self.locale_manager.get_string("dashboard_view.mode_manual")

        # Checks permission (only Adults can be manually controlled)
        if is_manual_mode and str(phase).upper() != "ADULT":
            self.control_panel.ocultar_todos_detalhes()
            self.map_widget.clear_all_selections()
            template = self.locale_manager.get_string("dashboard_view.snackbar_manual_control_denied")
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(template.format(id=semaphore_id, phase=phase)),
                    bgcolor="amber700"
                )
                self.page.snack_bar.open = True
                self.page.update()
            return

        # 2. Retrieves PANEL DATA (Road colors, times, etc.)
        # --- HERE WAS THE ERROR: It was necessary to apply the search for possible_ids in panel_data ---
        panel_data_source = getattr(self, 'latest_panel_data', {})
        semaphore_data = {}
        
        for pid in possible_ids:
            if pid in panel_data_source:
                semaphore_data = panel_data_source[pid]
                break
        
        if not semaphore_data:
            logging.warning(f"[Dashboard] Dados de painel não encontrados para {semaphore_id} (Tentado: {possible_ids})")
        
        self.control_panel.exibir_controles_semaforo(semaphore_id, semaphore_data, phase, self.current_mode)

    def _handle_street_click(self, street_id: str | None):
        self.selected_semaphore_id = None
        
        if not self.control_panel: return
        if street_id is None:
            self.control_panel.ocultar_todos_detalhes()
            return

        street_data_payload = getattr(self, 'latest_street_data', {})
        street_data_for_panel = street_data_payload.get(street_id, {})
        self.control_panel.exibir_info_rua(street_id, street_data_for_panel)

    def _handle_specific_command(self, semaphore_id: str, command: str):
        if self.map_widget:
            self.map_widget.set_semaphore_override_state(semaphore_id, command)