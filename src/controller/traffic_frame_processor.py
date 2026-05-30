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

# File: src/controller/traffic_frame_processor.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import logging
import time
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import Any

from controller.failsafe_manager import FailsafeManager
from controller.topology_manager import TopologyManager

logger = logging.getLogger(__name__)

class TrafficFrameProcessor:
    """
    Responsible for unpacking hardware/synapse frames and routing them
    correctly to the AI and the UI visual aggregator.
    
    NOTE: Heartbeat is now sent immediately in the gRPC hot-path (hft_server.py),
    NOT here. This processor runs on the cold-path worker thread.
    """
    def __init__(self, ai_pipe_conn: Connection, watchdog_queue: Queue, sds_data_queue: Queue, 
                 failsafe_manager: FailsafeManager, topology_manager: TopologyManager, telemetry_aggregator: Any,
                 traffic_data_recorder: Any = None):
        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_queue = watchdog_queue
        self.sds_data_queue = sds_data_queue
        
        self.failsafe_manager = failsafe_manager
        self.topology_manager = topology_manager
        self.telemetry_aggregator = telemetry_aggregator
        self.traffic_data_recorder = traffic_data_recorder
        
        # --- Two-Stage Readiness Latch ---
        self.is_system_ready = False
        
        # --- Processing time tracking ---
        self._proc_warning_threshold_ms = 100.0
        
    def set_system_ready(self, state: bool):
        self.is_system_ready = state

    def process_traffic_frame(self, frame: Any):
        """
        Processes a single Traffic Frame received from Synapse.
        This is the TRIGGER for the AI Decision Cycle.
        
        NOTE: Heartbeat is already sent in the gRPC hot-path. This method
        only handles failsafe recovery, AI dispatch, and visualization.
        
        Returns:
            float: Processing time in milliseconds (for diagnostics).
        """
        t_start = time.perf_counter()
        
        # 0. RECORD FRAME ARRIVAL (for in-process Synapse silence detection)
        self.failsafe_manager.record_frame_received()
        
        # 1. FAILSAFE RECOVERY
        # If we were in failsafe mode and a frame just arrived, Synapse is back.
        # FixedTimeController will deactivate and put all intersections in ALL_RED
        # for a safe handoff back to the Neural Network.
        self.failsafe_manager.attempt_recovery()

        # 1.5 RECORD FRAME TO DATABASE (for historical optimization analysis)
        if self.traffic_data_recorder:
            try:
                self.traffic_data_recorder.record_frame(frame)
            except Exception as rec_err:
                logger.debug(f"[TrafficFrameProcessor] Data recording error: {rec_err}")

        # 2. NORMAL PROCESSING (AI Step)
        current_time = frame.timestamp
        
        traffic_data = {'timestamp': current_time, 'sequence_id': frame.sequence_id, 'edges': {}}
        
        # Prepare data for AI (still manual as it is control logic, not visualization)
        for edge_id, state in frame.edges.items():
            traffic_data['edges'][edge_id] = {
                'occupancy': state.occupancy,
                'mean_speed': state.mean_speed,
                'queue_length': state.queue_length
            }

        # AGREEMENT: This is the ONLY place triggering the HFT Step.
        # SAFETY: Do NOT send AI commands while FixedTimeController is active.
        # The fixed-time plan must have exclusive control during failsafe to
        # prevent conflicting signal commands.
        # NOTE (Fix): Removed strict 'is_system_ready' drop so headless mock clients
        # can still trigger AI decisions without needing a UI 'carina_ready' connection.
        if not self.failsafe_manager.failsafe_active:
            try: 
                self.ai_pipe_conn.send(('custom', 'hft_step', (traffic_data,), {}))
            except Exception as e: 
                logger.error(f"Error sending frame to AI: {e}")
        else:
            if self.failsafe_manager.failsafe_active:
                logger.debug("[TrafficFrameProcessor] AI dispatch blocked — FixedTimeController is active.")
            # Drop AI frame dispatch, but allow visualization to continue.

        # 3. VISUALIZATION AGGREGATION & SYNC
        self.telemetry_aggregator.process_frame(frame)
        
        # 3.1 FAST PATH (Lightweight Sync for Semaphores/Maturity) -> 0.5s
        if getattr(self, '_last_fast_ui_sync', 0.0) == 0.0:
            self._last_fast_ui_sync = 0.0
            
        if current_time - self._last_fast_ui_sync >= 0.5:
            self._last_fast_ui_sync = current_time
            fast_payload = {
                'timestamp': current_time,
                'maturity': getattr(self.topology_manager, 'agent_maturity_cache', {}),
                'tls_phases': getattr(self.topology_manager, 'tls_phases_cache', {}),
                'edges': {} # Empty edges skips congestion update, preventing flickering
            }
            try:
                self.sds_data_queue.put(('hft_rich_update', fast_payload))
            except Exception:
                pass
        
        # 3.2 SLOW PATH (Heavy Heatmap Rendering) -> Controller.interval (e.g. 5.0s)
        if self.telemetry_aggregator.should_update(current_time):
            if not self.topology_manager.agent_maturity_cache:
                self.topology_manager.try_restore_state()
            
            rich_payload = self.telemetry_aggregator.compute_rich_payload(
                current_time, 
                self.topology_manager.agent_maturity_cache
            )
            
            rich_payload['tls_phases'] = getattr(self.topology_manager, 'tls_phases_cache', {})
            
            try:
                self.sds_data_queue.put(('hft_rich_update', rich_payload))
            except Exception as e:
                logger.error(f"Error putting rich update on SDS queue: {e}")
        
        # 4. MEASURE AND DIAGNOSE PROCESSING TIME
        t_end = time.perf_counter()
        proc_delta_ms = (t_end - t_start) * 1000
        
        if proc_delta_ms > self._proc_warning_threshold_ms:
            logger.warning(
                f"[TrafficFrameProcessor] ⏱️ Slow processing: {proc_delta_ms:.1f}ms "
                f"(>{self._proc_warning_threshold_ms:.0f}ms). Seq: {frame.sequence_id}"
            )
        
        return proc_delta_ms
