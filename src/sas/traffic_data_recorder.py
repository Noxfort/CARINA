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

# File: src/sas/traffic_data_recorder.py
# Author: Gabriel Moraes
# Date: April 22, 2026

"""
TrafficDataRecorder — Records Synapse TrafficFrame data into the database.

This module is the bridge between the real-time gRPC data stream (TrafficFrame)
and the historical database used by the Optimization Analysis Engine.

Each TrafficFrame contains per-edge metrics (density, mean_speed, queue_length,
occupancy). The recorder enriches each sample with topology metadata
(edge_length, num_lanes, speed_limit) and batch-inserts into the
'traffic_samples' table for later analysis.
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TrafficDataRecorder:
    """
    Records Synapse TrafficFrame data into the database for historical analysis.

    The recorder buffers samples and flushes them in batches to minimize
    database I/O overhead during high-frequency frame processing.
    """

    def __init__(self, db_manager, topology_edges: Optional[Dict[str, dict]] = None, batch_size: int = 10):
        """
        Initializes the TrafficDataRecorder.

        Args:
            db_manager: The DatabaseManager instance for database operations.
            topology_edges: Optional dict mapping edge_id -> {length, lanes, max_speed}
                            from the ScenarioDefinition topology.
            batch_size: Number of edge samples to buffer before flushing to DB.
        """
        self.db = db_manager
        self.topology = topology_edges or {}
        self._batch_buffer = []
        self._batch_size = batch_size
        self._total_recorded = 0
        
        # Dedicated worker thread for DB inserts to prevent thread explosion
        import queue
        self._flush_queue = queue.Queue(maxsize=1000)
        self._worker_thread = threading.Thread(target=self._db_worker_loop, daemon=True)
        self._worker_thread.start()
        
        logger.info(
            f"[TrafficDataRecorder] Initialized. "
            f"Topology edges: {len(self.topology)}, batch_size: {self._batch_size}"
        )

    def _db_worker_loop(self):
        """Background thread loop to process database inserts sequentially."""
        while True:
            try:
                samples = self._flush_queue.get()
                if samples is None:
                    break
                count_val = len(samples)
                self.db.insert_synapse_fluid_dynamics(samples)
                self._total_recorded += count_val
            except Exception as e:
                logger.error(f"[TrafficDataRecorder] Async flush failed: {e}")

    def set_topology(self, topology_edges: Dict[str, dict]):
        """
        Updates the topology metadata used to enrich samples.
        Called when a new ScenarioDefinition is loaded.

        Args:
            topology_edges: {edge_id: {'length': float, 'lanes': int, 'max_speed': float}}
        """
        self.topology = topology_edges
        logger.info(f"[TrafficDataRecorder] Topology updated with {len(topology_edges)} edges.")

    def record_frame(self, frame: Any):
        """
        Records all edge states from a single TrafficFrame into the buffer.
        Automatically flushes to the database when the buffer reaches batch_size.

        Args:
            frame: A gRPC TrafficFrame message with .edges (map<string, EdgeState>).
        """
        timestamp = datetime.now()

        for edge_id, state in frame.edges.items():
            topo = self.topology.get(edge_id, {})
            self._batch_buffer.append({
                'collected_at': timestamp,
                'edge_id': edge_id,
                'density': state.density,
                'mean_speed': state.mean_speed,
                'queue_length': state.queue_length,
                'occupancy': state.occupancy,
                'edge_length': topo.get('length'),
                'num_lanes': topo.get('lanes'),
                'speed_limit': topo.get('max_speed'),
            })

        if len(self._batch_buffer) >= self._batch_size:
            self.flush()

    def flush(self):
        """Flushes the buffered samples to the database asynchronously via queue."""
        if not self._batch_buffer:
            return
            
        samples_to_flush = list(self._batch_buffer)
        self._batch_buffer.clear()
        
        try:
            self._flush_queue.put_nowait(samples_to_flush)
        except queue.Full:
            logger.error("[TrafficDataRecorder] DB flush queue is FULL! Dropping samples.")

    @property
    def total_recorded(self) -> int:
        """Returns the total number of samples recorded since initialization."""
        return self._total_recorded
