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

# File: ui/clients/infrastructure_client.py (Pure In-Memory IPC Client)
# Author: Gabriel Moraes
# Date: 2026-06-09

import os
import logging
import threading
import time
from typing import Callable

class InfrastructureClient:
    """
    Escuta a fila de resultados IPC da análise de infraestrutura em uma thread separada, 
    garantindo comunicação 100% em memória sem criar arquivos de cache ou status no disco.
    """
    def __init__(self, on_complete_callback: Callable[[dict], None], sas_result_queue=None):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.on_complete = on_complete_callback
        self.sas_result_queue = sas_result_queue

    def _fetch_thread_target(self, trigger_time: float = None):
        result = {}
        start_poll = time.time()
        time_margin = 2.0  # 2 seconds tolerance for timestamp comparison

        min_valid_timestamp = (trigger_time - time_margin) if trigger_time is not None else 0.0

        # Dynamically resolve sas_result_queue if not provided at instantiation
        queue = self.sas_result_queue
        if queue is None:
            try:
                import ui.main_ui as ui_module
                queue = getattr(ui_module, 'sas_result_queue', None)
            except Exception as ex:
                logging.error(f"[InfrastructureClient] Error resolving sas_result_queue dynamically: {ex}")

        if queue is None:
            logging.error("[InfrastructureClient] sas_result_queue está NULO. Não é possível receber resultados IPC do backend.")
            result = {
                "status": "error",
                "message": "Fila IPC de resultados (sas_result_queue) não foi conectada pela interface."
            }
            if self.on_complete:
                self.on_complete(result)
            return

        logging.info(f"[InfrastructureClient] Iniciando busca assíncrona por resposta da análise SAS (sem limite de tempo)...")

        # Drain any old/stale messages sitting in the IPC queue before waiting for fresh analysis.
        try:
            while True:
                item = queue.get_nowait()
                if isinstance(item, dict):
                    item_time = item.get("timestamp", time.time())
                    if item_time >= min_valid_timestamp:
                        logging.info(f"[InfrastructureClient] Mensagem válida capturada na fase de drain (timestamp={item_time}).")
                        result = item
                        break
                    else:
                        logging.info(f"[InfrastructureClient] Mensagem antiga descartada na limpeza (timestamp={item_time} < min_valid={min_valid_timestamp}).")
        except Exception:
            pass

        if result:
            if self.on_complete:
                self.on_complete(result)
            return

        # Poll continuously without timeout for triggered requests
        while True:
            try:
                ipc_result = queue.get(block=True, timeout=0.5)
                if ipc_result and isinstance(ipc_result, dict):
                    msg_time = ipc_result.get("timestamp", time.time())
                    if msg_time >= min_valid_timestamp:
                        logging.info(f"[InfrastructureClient] Sucesso: Novo relatório de análise recebido da fila IPC (status={ipc_result.get('status')}).")
                        result = ipc_result
                        break
                    else:
                        logging.warning(f"[InfrastructureClient] Ignorando resultado IPC com timestamp antigo: {msg_time} < {min_valid_timestamp}")
            except Exception:
                pass

            # Passive poll timeout (only when trigger_time is None)
            if trigger_time is None and (time.time() - start_poll >= 5.0):
                break

        if not result and trigger_time is None:
            result = {
                "status": "error",
                "message": "Nenhuma análise recebida da Engine."
            }
        
        if result and self.on_complete:
            self.on_complete(result)

    def start_fetching_latest_analysis(self, trigger_time: float = None):
        thread = threading.Thread(target=self._fetch_thread_target, args=(trigger_time,), daemon=True)
        thread.start()