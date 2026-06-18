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

# File: src/handlers/ai_request_handler.py
# Author: Gabriel Moraes
# Date: 2026-04-17

import logging
from queue import Full
from typing import Any

class AIRequestHandler:
    """
    Handles all requests and packages sent over the AI Pipe.
    Can be HFT Tuples or Standard TraCI Commands.
    """
    def __init__(self, locale_manager, topology_manager, sds_queue, sas_queue, health_monitor, override_manager):
        self.locale_manager = locale_manager
        self.topology_manager = topology_manager
        self.sds_queue = sds_queue
        self.sas_queue = sas_queue
        self.health_monitor = health_monitor
        self.override_manager = override_manager
        
        self.maturity_phases = {}
        self.current_run_id = None
        self.on_backend_ready = None

    def set_backend_ready_callback(self, cb):
        self.on_backend_ready = cb

    def process(self, request: Any, sumo_conn: Any, ai_pipe_conn: Any, override_commands_buffer: list, collect_step_data_func=None):
        lm = self.locale_manager

        # --- Handling of AI Telemetry Sync (2-element tuple) ---
        if isinstance(request, tuple) and len(request) == 2:
            msg_type, payload = request
            
            if msg_type == "ai_telemetry_sync":
                # Update local maturity cache
                if "maturity" in payload:
                    self.topology_manager.agent_maturity_cache.update(payload["maturity"])
                    
                # Update local phase cache for TrafficFrameProcessor
                if "tls_phases" in payload:
                    if not hasattr(self.topology_manager, 'tls_phases_cache'):
                        self.topology_manager.tls_phases_cache = {}
                    self.topology_manager.tls_phases_cache.update(payload["tls_phases"])
                
                # Routes to SAS (Analysis) for metric logging AND to SDS (UI) for Traffic Light updates!
                try:
                    self.sas_queue.put_nowait(("hft_rich_update", payload))
                    
                    # Prevent raw 'edges' data from overwriting UI telemetry
                    # Keep 'tls_phases', 'tls_lanes_state', and 'maturity' for fast UI updates
                    ui_payload = payload.copy()
                    if "edges" in ui_payload:
                        del ui_payload["edges"]
                        
                    self.sds_queue.put_nowait(("hft_rich_update", ui_payload))
                except Full:
                    pass
                    
                # AI Telemetry updates are push data, not commands to TraCI/Override
                return
                
            elif msg_type == "system" and payload == "backend_ready":
                logging.info("✅ [RequestProcessor] Comando interno 'backend_ready' recebido da Engine de IA.")
                if self.on_backend_ready and callable(self.on_backend_ready):
                    self.on_backend_ready()
                return

        self.health_monitor.record_activity()

        # --- Standard Commands (4-Element Tuple) ---
        if self.override_manager.is_ai_command_blocked(request):
            module_name, func_name, args, _ = request
            if module_name == 'trafficlight' and func_name == 'setPhase' and args:
                tl_id = args[0]
                override_state = self.override_manager.active_overrides.get(tl_id, "N/A")
                logging.info(
                    lm.get_string(
                        "request_processor.override.ai_ignored",
                        tl_id=tl_id,
                        state=override_state
                    )
                )
            ai_pipe_conn.send(None)
            return

        module_name, func_name, args, kwargs = request
        result = None

        if module_name == 'custom':
            if func_name == 'update_maturity_state':
                new_phases_data = args[0] if args else {}
                if isinstance(new_phases_data, dict):
                    self.maturity_phases = new_phases_data
                    
                    # Update HFT Cache
                    real_maturity_map = new_phases_data.get("agent_maturity")
                    if not real_maturity_map:
                        real_maturity_map = {
                            k: v for k, v in new_phases_data.items() 
                            if k != "run_id"
                        }
                    if real_maturity_map:
                        self.topology_manager.agent_maturity_cache.update(real_maturity_map)

                    if self.current_run_id is None and isinstance(new_phases_data.get("run_id"), int):
                         self.current_run_id = new_phases_data.get("run_id")
                         logging.info(f"[RequestProcessor] Run ID {self.current_run_id} recebido da IA.")
                result = True

            elif func_name == 'get_batched_step_data':
                if callable(collect_step_data_func):
                    result = collect_step_data_func(sumo_conn)
                else:
                    return # Feature deprecated or unavailable

                if result:
                    if override_commands_buffer:
                        result["override_commands"] = override_commands_buffer.copy()
                        override_commands_buffer.clear()
                    try:
                        self.sds_queue.put_nowait(result)
                        self.sas_queue.put_nowait(result)
                    except Full:
                        pass

        else:
            if sumo_conn is None:
                 pass 
            else:
                result = AttributeError(f"Módulo ou Função desconhecida requisitada pela IA: '{module_name}.{func_name}'")
                logging.error(str(result))

        ai_pipe_conn.send(result)
