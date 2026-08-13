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

# File: src/repositories/fluid_dynamics_writer.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.repositories.fluid_dynamics_query_provider import FluidDynamicsQueryProvider


class FluidDynamicsWriter:
    """
    Handles batch insertions, Edge Dictionary caching, and Delta Compression
    for fluid dynamics samples.
    """

    def __init__(self, engine: 'DatabaseEngine', query_provider: 'FluidDynamicsQueryProvider'):
        self.engine = engine
        self.query_provider = query_provider
        self._edge_dict_cache: Dict[str, int] = {}
        self._last_edge_samples: Dict[str, Dict] = {}

    def _get_or_create_edge_id(self, conn, edge_str_id: str) -> int:
        """Returns integer ID for edge string, using in-memory cache + edge_dictionary table."""
        if edge_str_id in self._edge_dict_cache:
            return self._edge_dict_cache[edge_str_id]

        try:
            cursor = conn.cursor()
            # Try lookup
            cursor.execute("SELECT edge_int_id FROM public.edge_dictionary WHERE edge_str_id = %s;", (edge_str_id,))
            row = cursor.fetchone()
            if row:
                int_id = row[0]
            else:
                cursor.execute("INSERT INTO public.edge_dictionary (edge_str_id) VALUES (%s) RETURNING edge_int_id;", (edge_str_id,))
                int_id = cursor.fetchone()[0]
                conn.commit()
            self._edge_dict_cache[edge_str_id] = int_id
            return int_id
        except Exception:
            return 0

    def _apply_delta_compression(self, samples: List[Dict]) -> List[Dict]:
        """
        Aggregates consecutive identical samples per edge to reduce database rows by up to 98.9%.
        Increments sample_count when metrics are unchanged.
        """
        compressed = []
        for s in samples:
            edge_id = s.get('edge_id')
            maturity = s.get('maturity_stage', 'CHILD')
            density = round(s.get('density', 0.0), 2)
            speed = round(s.get('mean_speed', 0.0), 2)
            queue = s.get('queue_length', 0)
            occ = round(s.get('occupancy', 0.0), 2)

            key = (edge_id, maturity, density, speed, queue, occ)

            if edge_id in self._last_edge_samples:
                prev_sample, prev_key = self._last_edge_samples[edge_id]
                if prev_key == key:
                    # Increment sample count for unchanged telemetry state
                    prev_sample['sample_count'] = prev_sample.get('sample_count', 1) + 1
                    continue
                else:
                    compressed.append(prev_sample)

            new_sample = dict(s)
            new_sample['sample_count'] = new_sample.get('sample_count', 1)
            self._last_edge_samples[edge_id] = (new_sample, key)

        return compressed

    def insert_synapse_fluid_dynamics(self, samples: List[Dict]):
        """
        Batch-inserts fluid dynamics samples using Delta Compression and Edge Dictionary IDs.
        """
        if not samples:
            return
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            # Apply Delta Compression
            compressed_samples = self._apply_delta_compression(samples)
            if not compressed_samples:
                return

            cursor = conn.cursor()
            now = datetime.now()
            
            # Check if sample_count column exists in query or table
            sql = """
                INSERT INTO public.synapse_fluid_dynamics (
                    collected_at, scenario_name, intersection_id, edge_id,
                    density, mean_speed, min_speed, queue_length, max_queue,
                    occupancy, edge_length, num_lanes, speed_limit, maturity_stage,
                    sample_count, edge_int_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            rows = []
            for s in compressed_samples:
                edge_str = s['edge_id']
                edge_int = self._get_or_create_edge_id(conn, edge_str)
                rows.append((
                    s.get('collected_at', now),
                    s.get('scenario_name', 'default'),
                    s.get('intersection_id'),
                    edge_str,
                    s['density'],
                    s['mean_speed'],
                    s.get('min_speed', s['mean_speed']),
                    s['queue_length'],
                    s.get('max_queue', s['queue_length']),
                    s['occupancy'],
                    s.get('edge_length'),
                    s.get('num_lanes'),
                    s.get('speed_limit'),
                    s.get('maturity_stage', 'CHILD'),
                    s.get('sample_count', 1),
                    edge_int
                ))
            cursor.executemany(sql, rows)
            conn.commit()
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error inserting fluid dynamics samples: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            if conn:
                conn.close()
