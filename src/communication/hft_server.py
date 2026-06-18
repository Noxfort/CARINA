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

# File: src/communication/hft_server.py
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
# File: src/communication/hft_server.py
# Author: Gabriel Moraes
# Date: 2026-02-20

import logging
import time
import os
import sys
import queue
import threading
from datetime import datetime
from typing import Optional

from src.communication.hft_diagnostics import HFTDiagnostics
from src.communication.hft_worker import HFTWorker
from src.communication.hft_session_manager import HFTSessionManager

# Ensure project root and proto paths are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
proto_path = os.path.join(project_root, 'proto')

if proto_path not in sys.path:
    sys.path.insert(0, proto_path)

# Import generated gRPC modules
try:
    import synapse_hft_pb2 as pb2 # type: ignore
    import synapse_hft_pb2_grpc as pb2_grpc # type: ignore
except ImportError:
    logging.critical("[HFTServer] Failed to import generated gRPC modules. Ensure 'proto' folder exists and contains generated files.")
    pb2, pb2_grpc = None, None # type: ignore


class CarinaHFTImpl(pb2_grpc.HFTLinkServicer): # type: ignore
    """
    Implementation of the High-Frequency Traffic (HFT) Link gRPC Service.
    Acts as an Orchestrator/Facade to specialized components (Worker, Diagnostics, File System).
    
    Architecture:
        - gRPC StreamTraffic thread (HOT path): receives frames, sends heartbeat, enqueues.
        - Worker thread (COLD path): dequeues frames, processes them via controller.
        
    This separation ensures heartbeats are never delayed by processing, allowing
    accurate diagnosis of whether latency comes from Synapse or CARINA.
    """

    def __init__(self, controller_instance):
        """
        Args:
            controller_instance: Reference to the CentralController to delegate logic.
        """
        self.controller = controller_instance
        self.state = "IDLE"
        
        # Facade Instantiations (SRP compliant)
        self.diagnostics = HFTDiagnostics()
        self.worker = HFTWorker(controller=self.controller, diagnostics=self.diagnostics, server_ref=self)

    # ------------------------------------------------------------------
    # gRPC Service Methods
    # ------------------------------------------------------------------
    def Ping(self, request, context):
        """Health check method."""
        return pb2.SystemState(active=True, state=self.state, server_time=int(time.time()))

    def LoadScenario(self, request, context):
        """
        Receives the traffic network topology (map) from Synapse.
        Delegates map saving logic to HFTSessionManager, then triggers logic in Controller.
        """
        logging.info(f"[HFT] Receiving scenario from Synapse (Hash: {request.map_hash})...")
        
        if not request.map_file_content:
            logging.warning("[HFT] LoadScenario received without file content.")
            return pb2.ScenarioStatus(accepted=False, message="Empty map content")
            
        success, msg, map_path, maps_dir = HFTSessionManager.save_map_and_schedule(
            map_file_content=request.map_file_content,
            map_file_name=request.map_file_name,
            peak_schedule_json=request.peak_schedule_json
        )
        
        if success:
            # Process topology and notify AI via Controller
            self.controller.handle_new_map(map_path, maps_dir)
            self.state = "READY"
            
        return pb2.ScenarioStatus(accepted=success, message=msg)

    def SystemControl(self, request, context):
        """
        Handles Start/Stop commands for the AI Session.
        Delegates concurrency control to HFTWorker and session state to Controller.
        """
        cmd = request.action
        if cmd == pb2.ControlCommand.START:
            self.state = "RUNNING"
            self.controller.start_ai_session()
            
            # Inject UI Ready Latch Unlock directly via gRPC (Headless Single-Connection Mode)
            if hasattr(self.controller, 'ui_command_queue'):
                self.controller.ui_command_queue.put({"type": "carina_ready"})
                
            print(f"🚀 [SYSTEM] HFT Control Started. Latch Unlocked natively. State is now RUNNING.")
        elif cmd == pb2.ControlCommand.STOP:
            self.state = "IDLE"
            self.worker.stop()
            self.controller.stop_ai_session()
            print(f"🛑 [SYSTEM] HFT Control Stopped. State is now IDLE.")
        return pb2.CommandResponse(success=True, new_state=self.state)

    def StreamTraffic(self, request_iterator, context):
        """
        HOT PATH: Receives the stream of Traffic Frames from Synapse.
        
        This method ONLY does:
            1. Receive frame from gRPC iterator
            2. Send HEARTBEAT immediately to Watchdog
            3. Enqueue frame to HFTWorker for async processing
            4. Delegate diagnostics to log recv_delta
        """
        msg_counter = 0
        last_recv_time = 0.0
        last_recv_perf = 0.0

        # Ensure worker thread is running
        self.worker.start()

        try:
            for frame in request_iterator:
                
                current_recv_time = time.time()
                current_recv_perf = time.perf_counter()
                msg_counter += 1
                
                # ── 1. IMMEDIATE HEARTBEAT (before any processing) ──
                try:
                    self.controller.watchdog_queue.put("HEARTBEAT", block=False)
                    self.controller.failsafe_manager.record_frame_received()
                except Exception as e:
                    logging.error(f"[HFT] Failed to send Heartbeat: {e}")
                
                # ── 2. RECV DELTA CALCULATION & LOGGING ──
                if msg_counter > 1 and last_recv_time > 0:
                    delta_ms = (current_recv_perf - last_recv_perf) * 1000
                    current_depth = self.worker.get_queue_depth()
                    self.diagnostics.log_recv_delta(current_recv_time, delta_ms, current_depth)
                
                last_recv_time = current_recv_time
                last_recv_perf = current_recv_perf
                
                # ── 3. ENQUEUE FOR ASYNC PROCESSING ──
                self.worker.enqueue(frame, current_recv_time)
                    
        except Exception as e:
            logging.error(f"[HFT] Error in traffic stream: {e}")
            print(f"❌ [HFT] Stream Connection Lost: {e}")
        finally:
            self.worker.stop()
            
        return pb2.SystemState(active=True, state=self.state)