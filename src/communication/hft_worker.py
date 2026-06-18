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

# File: src/communication/hft_worker.py
# Author: Gabriel Moraes
# Date: 2026-06-09

# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
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
#
# File: src/communication/hft_worker.py
# Author: Gabriel Moraes
# Date: 2026-04-17

import queue
import threading
import time
import logging
from typing import Optional
from src.communication.hft_diagnostics import HFTDiagnostics

class HFTWorker:
    """
    Manages the Cold Path of the HFT pipeline. Dequeues frames
    from the hot gRPC thread and passes them to the Controller to be processed.
    """
    
    _BACKPRESSURE_THRESHOLD = 10

    def __init__(self, controller, diagnostics: HFTDiagnostics, server_ref):
        self.controller = controller
        self.diagnostics = diagnostics
        self.server_ref = server_ref # To check if server state is "RUNNING"
        
        self.frame_queue: queue.Queue = queue.Queue(maxsize=100)
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_running = threading.Event()

    def get_queue_depth(self) -> int:
        return self.frame_queue.qsize()

    def enqueue(self, frame, current_recv_time):
        """Enqueues a frame for async processing."""
        try:
            self.frame_queue.put_nowait((frame, current_recv_time))
        except queue.Full:
            logging.error(
                "[HFT] ❌ Frame queue FULL! Dropping frame. "
                "CARINA processing is critically overloaded."
            )

    def start(self):
        """Starts the dedicated frame processing worker thread."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        
        self._worker_running.set()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="HFT-FrameWorker",
            daemon=True
        )
        self._worker_thread.start()
        logging.info("[HFT] 🧵 Frame Worker Thread started (dedicated processing).")

    def stop(self):
        """Signals the worker thread to stop gracefully."""
        self._worker_running.clear()
        try:
            self.frame_queue.put(None, timeout=0.1)
        except queue.Full:
            pass

    def _worker_loop(self):
        """
        Worker loop: dequeues frames and processes them via the controller.
        Measures processing time (proc_delta) for diagnostics.
        """
        logging.info("[HFT] 🔄 Frame Worker Loop running.")
        
        while self._worker_running.is_set():
            try:
                frame_item = self.frame_queue.get(timeout=0.5)
                
                if frame_item is None:
                    break
                
                frame, recv_time = frame_item
                
                t_proc_start = time.perf_counter()
                
                if getattr(self.server_ref, 'state', None) == "RUNNING":
                    self.controller.process_traffic_frame(frame)
                
                t_proc_end = time.perf_counter()
                proc_delta_ms = (t_proc_end - t_proc_start) * 1000
                
                current_depth = self.get_queue_depth()
                self.diagnostics.log_processing(recv_time, proc_delta_ms, current_depth, self._BACKPRESSURE_THRESHOLD)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"[HFT] Error in frame worker: {e}")
        
        logging.info("[HFT] 🛑 Frame Worker Loop exited.")
