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

    def __init__(self, db_manager, topology_edges: Optional[Dict[str, dict]] = None, batch_size: int = 10, locale_manager: Any = None, topology_manager: Any = None):
        """
        Initializes the TrafficDataRecorder.

        Args:
            db_manager: The DatabaseManager instance for database operations.
            topology_edges: Optional dict mapping edge_id -> {length, lanes, max_speed}
                            from the ScenarioDefinition topology.
            batch_size: Number of edge samples to buffer before flushing to DB.
            locale_manager: Optional LocaleManagerBackend instance.
            topology_manager: Optional TopologyManager instance for maturity stage resolution.
        """
        self.db = db_manager
        self.topology = topology_edges or {}
        self._batch_buffer = []
        self._batch_size = batch_size
        self._total_recorded = 0
        self.locale_manager = locale_manager
        self.topology_manager = topology_manager
        self.scenario_name = "default"
        
        # 60-second in-memory aggregation buffer to reduce DB inserts by 98.3%
        self._ram_60s_buffer = {}
        self._last_ram_flush = datetime.now()
        
        # Dedicated worker thread for DB inserts to prevent thread explosion
        import queue
        self._flush_queue = queue.Queue(maxsize=1000)
        self._worker_thread = threading.Thread(target=self._db_worker_loop, daemon=True)
        self._worker_thread.start()

    def set_scenario_name(self, scenario_name: str):
        """Sets the scenario_name for telemetry tagging."""
        self.scenario_name = scenario_name or "default"

    def set_topology(self, topology_edges: Dict[str, dict]):
        """
        Updates the topology metadata used to enrich samples.
        Called when a new ScenarioDefinition is loaded.

        Args:
            topology_edges: {edge_id: {'length': float, 'lanes': int, 'max_speed': float}}
        """
        self.topology = topology_edges
        logger.info(self._get_string("sas_recorder.topology_updated", default="[TrafficDataRecorder] Topology updated with {count} edges.", count=len(topology_edges)))

    def record_frame(self, frame: Any):
        """
        Accumulates all edge states from a TrafficFrame into the 60-second in-memory buffer.
        Flushes 1-minute consolidated records to database every 60 seconds.

        Args:
            frame: A gRPC TrafficFrame message with .edges (map<string, EdgeState>).
        """
        now = datetime.now()
        cache = getattr(self.topology_manager, 'agent_maturity_cache', {}) if self.topology_manager else {}

        for edge_id, state in frame.edges.items():
            topo = self.topology.get(edge_id, {})
            to_junction = topo.get('to') or topo.get('to_junction') or 'unassigned'
            maturity_stage = 'CHILD'
            if cache:
                if to_junction and to_junction in cache:
                    maturity_stage = cache[to_junction]
                elif edge_id in cache:
                    maturity_stage = cache[edge_id]

            if edge_id not in self._ram_60s_buffer:
                self._ram_60s_buffer[edge_id] = {
                    'speeds': [],
                    'densities': [],
                    'queues': [],
                    'occupancies': [],
                    'topo': topo,
                    'to_junction': to_junction,
                    'maturity_stage': maturity_stage
                }

            buf = self._ram_60s_buffer[edge_id]
            buf['speeds'].append(state.mean_speed)
            buf['densities'].append(state.density)
            buf['queues'].append(state.queue_length)
            buf['occupancies'].append(state.occupancy)

        # Check if 60-second RAM window has elapsed or buffer needs flushing
        if (now - self._last_ram_flush).total_seconds() >= 60.0 or len(self._ram_60s_buffer) > 5000:
            self._flush_ram_buffer(now)

    def _flush_ram_buffer(self, timestamp: datetime):
        """Consolidates 60-second RAM buffer into 1-minute records and queues for DB insert."""
        if not self._ram_60s_buffer:
            return

        for edge_id, data in list(self._ram_60s_buffer.items()):
            speeds = data['speeds']
            densities = data['densities']
            queues = data['queues']
            occupancies = data['occupancies']

            if not speeds:
                continue

            avg_speed = sum(speeds) / len(speeds)
            min_speed = min(speeds)
            avg_density = sum(densities) / len(densities)
            avg_queue = sum(queues) / len(queues)
            max_queue = max(queues)
            avg_occupancy = sum(occupancies) / len(occupancies)

            topo = data['topo']
            self._batch_buffer.append({
                'collected_at': timestamp,
                'scenario_name': self.scenario_name,
                'intersection_id': data['to_junction'],
                'edge_id': edge_id,
                'density': float(avg_density),
                'mean_speed': float(avg_speed),
                'min_speed': float(min_speed),
                'queue_length': int(round(avg_queue)),
                'max_queue': int(max_queue),
                'occupancy': float(avg_occupancy),
                'edge_length': topo.get('length'),
                'num_lanes': topo.get('lanes'),
                'speed_limit': topo.get('max_speed'),
                'maturity_stage': data['maturity_stage'],
            })

        self._ram_60s_buffer.clear()
        self._last_ram_flush = timestamp

        if len(self._batch_buffer) >= self._batch_size:
            self.flush()

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
            logger.error(self._get_string("sas_recorder.queue_full", default="[TrafficDataRecorder] DB flush queue is FULL! Dropping samples."))

    @property
    def total_recorded(self) -> int:
        """Returns the total number of samples recorded since initialization."""
        return self._total_recorded
