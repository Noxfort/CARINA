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

# File: ui/clients/mfd_analysis_client.py
# Author: Gabriel Moraes
# Date: 2026

import os
import logging
import threading
import time
from typing import Callable, Optional

class MfdAnalysisClient:
    """
    Listens to the MFD analysis IPC result queue in a separate thread,
    guaranteeing 100% in-memory IPC communication without creating cache or request files on disk,
    mirroring the exact architecture of InfrastructureClient (SAS Engine).
    """
    def __init__(self, on_analysis_complete_callback: Callable[[dict], None], results_dir: Optional[str] = None, mfd_result_queue=None, mfd_trigger_queue=None):
        self.on_analysis_complete = on_analysis_complete_callback
        self.results_dir = results_dir
        self.mfd_result_queue = mfd_result_queue
        self.mfd_trigger_queue = mfd_trigger_queue

    def start_analysis(self):
        """
        Puts an MFD trigger packet into mfd_trigger_queue and starts listening for MFD optimization results in memory.
        Returns immediately. The result will be delivered via the callback.
        """
        # Resolve mfd_trigger_queue if not explicitly provided
        trig_queue = self.mfd_trigger_queue
        if trig_queue is None:
            try:
                import ui.main_ui as ui_module
                trig_queue = getattr(ui_module, 'mfd_trigger_queue', None)
            except Exception:
                pass

        if trig_queue is not None:
            try:
                trig_queue.put(("trigger_mfd", {}))
                logging.info("[MfdAnalysisClient] Pacote de disparo MFD enviado com sucesso para mfd_trigger_queue em memória.")
            except Exception as ex:
                logging.error(f"[MfdAnalysisClient] Erro ao enviar disparo para mfd_trigger_queue: {ex}")

        trigger_time = time.time()
        thread = threading.Thread(
            target=self._fetch_thread_target,
            args=(trigger_time,),
            daemon=True
        )
        thread.start()

    def _fetch_thread_target(self, trigger_time: float = None):
        result = {}
        time_margin = 2.0
        min_valid_timestamp = (trigger_time - time_margin) if trigger_time is not None else 0.0

        # Dynamically resolve mfd_result_queue if not provided at instantiation
        queue = self.mfd_result_queue
        if queue is None:
            try:
                import ui.main_ui as ui_module
                queue = getattr(ui_module, 'mfd_result_queue', None)
            except Exception as ex:
                logging.error(f"[MfdAnalysisClient] Error resolving mfd_result_queue dynamically: {ex}")

        if queue is None:
            logging.error("[MfdAnalysisClient] mfd_result_queue is NULL. Cannot receive in-memory IPC results.")
            result = {
                "status": "error",
                "message": "Fila IPC de resultados MFD (mfd_result_queue) não foi conectada pela interface."
            }
            if self.on_analysis_complete:
                self.on_analysis_complete(result)
            return

        logging.info("[MfdAnalysisClient] Starting asynchronous in-memory IPC queue poll for MFD report (no timeout)...")

        # Drain all stale messages from queue before polling for new job result
        try:
            while not queue.empty():
                queue.get_nowait()
        except Exception:
            pass

        try:
            ipc_result = queue.get(block=True)
            if isinstance(ipc_result, dict):
                logging.info(f"[MfdAnalysisClient] Success: New MFD report received via in-memory IPC queue (status={ipc_result.get('status')}).")
                result = ipc_result
            else:
                result = {"status": "error", "message": "Formato inválido retornado da fila IPC de resultados MFD."}
        except Exception as poll_err:
            logging.error(f"[MfdAnalysisClient] Error reading MFD result from IPC queue: {poll_err}")
            result = {"status": "error", "message": f"Erro na recepção do resultado MFD: {poll_err}"}

        if self.on_analysis_complete:
            self.on_analysis_complete(result)
