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

# File: src/core/hft_event_loop.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import logging
import time

class HftEventLoop:
    """
    SRP: Handles the main background event loop for HFT monitoring, pipe signals,
    and failsafe ticking.
    """
    def __init__(self, ai_pipe_conn, failsafe_manager, request_processor, sds_data_queue):
        self.ai_pipe_conn = ai_pipe_conn
        self.failsafe_manager = failsafe_manager
        self.request_processor = request_processor
        self.sds_data_queue = sds_data_queue
        self.is_running = True

    def run_loop(self):
        logging.info("[HftEventLoop] Entering main HFT processing loop...")
        while self.is_running:
            # Check for shutdown signal from launcher
            # Drain all pending messages from the AI process pipe
            while self.ai_pipe_conn.poll():
                try:
                    cmd = self.ai_pipe_conn.recv()
                    if isinstance(cmd, tuple) and len(cmd) >= 2 and cmd[0] == "system" and cmd[1] == "shutdown":
                        logging.info("[HftEventLoop] Shutdown signal received. Exiting main loop gracefully...")
                        self.is_running = False
                        break
                    else:
                        self.request_processor.handle_single_request(cmd, sumo_conn=None)
                except EOFError:
                    self.is_running = False
                    break
                except Exception as e:
                    logging.error(f"[HftEventLoop] Pipe poll error: {e}")
                    break

            # --- FAILSAFE MONITORING (In-Process Synapse Silence Detection) ---
            if not self.failsafe_manager.failsafe_active:
                if not self.failsafe_manager.check_synapse_health():
                    self.failsafe_manager.trigger_failsafe()
            else:
                phase_changes = self.failsafe_manager.tick()
                if phase_changes:
                    try:
                        self.sds_data_queue.put(('failsafe_phase_update', {
                            'changes': phase_changes,
                            'status': self.failsafe_manager.get_status()
                        }))
                    except Exception as e:
                        logging.error(f"[HftEventLoop] Error sending failsafe update: {e}")

            try:
                self.request_processor.process_queues(sumo_conn=None, is_ai_healthy=not self.failsafe_manager.failsafe_active)
            except Exception as e_proc:
                logging.error(f"[HftEventLoop] Error in processing loop: {e_proc}")
            
            time.sleep(0.05)

    def stop(self):
        self.is_running = False
