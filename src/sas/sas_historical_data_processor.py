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

# File: src/sas/sas_historical_data_processor.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import logging
import gc
from collections import defaultdict
from typing import Tuple
from utils.network_topology_parser import NetworkTopologyParser
from sas.sas_helpers import EdgeClassifier, TrafficMetricsCalculator, SyntheticSampleGenerator


class SASHistoricalDataProcessor:
    """
    Processes historical traffic monitoring data from database queries (Pushdown Aggregations
    or streaming batches) for the AnalyzerEngine.
    """

    def __init__(self, locale_manager, topology_parser=None):
        self.locale_manager = locale_manager
        self.topology_parser = topology_parser or NetworkTopologyParser(self.locale_manager)

    def process(self, db_manager, net_file_path: str, limit_seconds: int = None) -> Tuple[dict, list]:
        """Queries historical DB records and constructs junction grouped data structures."""
        logging.info("[SAS_HISTORICAL_PROCESSOR] Processing historical data from database in batches...")

        # 1. Parse topology if net_file_path is provided
        junction_types, junction_incoming_edges = {}, {}
        if net_file_path:
            try:
                junction_types, junction_incoming_edges = self.topology_parser.build(net_file_path)
            except Exception as e:
                logging.warning(f"[SAS_HISTORICAL_PROCESSOR] Failed to parse net file topology ({e}). Will fallback to synthetic topology.")

        true_traffic_light_ids = [j_id for j_id, j_type in junction_types.items() if j_type == 'traffic_light']

        edge_summaries = {}

        # 2. Query traffic samples from DB using Pushdown Aggregation Query (or fallback to batches)
        total_samples = 0
        try:
            if hasattr(db_manager, "query_aggregated_fluid_dynamics"):
                aggregated_rows = db_manager.query_aggregated_fluid_dynamics(limit_seconds=limit_seconds)
                if aggregated_rows:
                    logging.info(f"[SAS_HISTORICAL_PROCESSOR] Pushdown Query executed successfully: {len(aggregated_rows)} aggregated edge summaries loaded.")
                    for row in aggregated_rows:
                        edge_id = row['edge_id']
                        avg_q = int(row.get('avg_queue') or 0)
                        max_q = int(row.get('max_queue') or 0)
                        q_bin = (max_q // 5) * 5
                        edge_summaries[edge_id] = {
                            'volume_sum': float(row.get('volume_sum') or 0.0),
                            'volume_cnt': int(row.get('volume_cnt') or 1),
                            'delay_sum': float(row.get('delay_sum') or 0.0),
                            'delay_cnt': int(row.get('delay_cnt') or 1),
                            'queue_freq': {q_bin: int(row.get('total_samples') or 1)},
                            'edge_length': float(row.get('edge_length')) if row.get('edge_length') is not None else None,
                            'num_lanes': int(row.get('num_lanes')) if row.get('num_lanes') is not None else None,
                            'speed_limit': float(row.get('speed_limit')) if row.get('speed_limit') is not None else None
                        }
                        total_samples += int(row.get('total_samples') or 0)
        except Exception as e:
            logging.warning(f"[SAS_HISTORICAL_PROCESSOR] Pushdown query failed ({e}), falling back to batch iteration.")
            edge_summaries = {}
            total_samples = 0

        # Fallback to batch iteration if Pushdown Query returned no rows
        if total_samples == 0:
            try:
                batch_generator = db_manager.query_fluid_dynamics_history_batches(limit_seconds=limit_seconds, batch_size=50000)
                for batch in batch_generator:
                    total_samples += len(batch)
                    for sample in batch:
                        edge_id = sample['edge_id']
                        if edge_id not in edge_summaries:
                            edge_summaries[edge_id] = {
                                'volume_sum': 0.0,
                                'volume_cnt': 0,
                                'delay_sum': 0.0,
                                'delay_cnt': 0,
                                'queue_freq': defaultdict(int),
                                'edge_length': float(sample['edge_length']) if sample.get('edge_length') is not None else None,
                                'num_lanes': int(sample['num_lanes']) if sample.get('num_lanes') is not None else None,
                                'speed_limit': float(sample['speed_limit']) if sample.get('speed_limit') is not None else None
                            }
                        
                        summary = edge_summaries[edge_id]
                        
                        if summary['edge_length'] is None and sample.get('edge_length') is not None:
                            summary['edge_length'] = float(sample.get('edge_length'))
                        if summary['num_lanes'] is None and sample.get('num_lanes') is not None:
                            summary['num_lanes'] = int(sample.get('num_lanes'))
                        if summary['speed_limit'] is None and sample.get('speed_limit') is not None:
                            summary['speed_limit'] = float(sample.get('speed_limit'))

                        density = float(sample.get('density', 0.0))
                        mean_speed = float(sample.get('mean_speed', 0.0))
                        q = TrafficMetricsCalculator.compute_volume(density, mean_speed)
                        summary['volume_sum'] += q
                        summary['volume_cnt'] += 1

                        edge_length = float(summary['edge_length']) if summary.get('edge_length') is not None else 0.0
                        speed_limit = float(summary['speed_limit']) if summary.get('speed_limit') is not None else 13.89
                        delay = TrafficMetricsCalculator.compute_delay(edge_length, mean_speed, speed_limit)
                        summary['delay_sum'] += delay
                        summary['delay_cnt'] += 1

                        q_len = int(sample.get('queue_length', 0))
                        q_bin = (q_len // 5) * 5
                        summary['queue_freq'][q_bin] += 1
            except Exception as e:
                logging.error(f"[SAS_HISTORICAL_PROCESSOR] Error processing historical data batches: {e}", exc_info=True)

        logging.info(f"[SAS_HISTORICAL_PROCESSOR] Processed {total_samples} traffic samples from database in batches.")

        if total_samples == 0:
            return {}, true_traffic_light_ids

        # 3. Create representative/synthetic samples for each edge
        samples_by_edge = {}
        edge_volumes_cache = {}
        for edge_id, summary in edge_summaries.items():
            avg_volume = summary['volume_sum'] / summary['volume_cnt'] if summary['volume_cnt'] > 0 else 0.0
            edge_volumes_cache[edge_id] = avg_volume
            avg_delay = summary['delay_sum'] / summary['delay_cnt'] if summary['delay_cnt'] > 0 else 0.0
            
            rep_queues = [TrafficMetricsCalculator.get_percentile(summary['queue_freq'], i / 100.0) for i in range(100)]
            
            edge_len = float(summary['edge_length']) if summary.get('edge_length') is not None else 0.0
            spd_lim = float(summary['speed_limit']) if summary.get('speed_limit') is not None else 13.89
            adjusted_speed_ms = TrafficMetricsCalculator.compute_adjusted_speed(edge_len, avg_delay, spd_lim)
            
            samples_by_edge[edge_id] = SyntheticSampleGenerator.generate_historical(
                edge_id=edge_id,
                avg_volume=avg_volume,
                adjusted_speed_ms=adjusted_speed_ms,
                rep_queues=rep_queues,
                edge_len=summary['edge_length'],
                num_lanes=summary['num_lanes'],
                speed_limit=summary['speed_limit']
            )

        del edge_summaries
        gc.collect()

        # Fallback topology if no valid net file topology was parsed
        if not junction_incoming_edges and samples_by_edge:
            logging.info("[SAS_HISTORICAL_PROCESSOR] Building synthetic fallback topology for database edges.")
            synth_dict = {}
            for edge_id, samples in samples_by_edge.items():
                first_s = samples[0] if samples else {}
                synth_dict[edge_id] = {
                    'length': float(first_s.get('edge_length') or 100.0),
                    'num_lanes': int(first_s.get('num_lanes') or 1),
                    'speed_limit': float(first_s.get('speed_limit') or 13.89)
                }
            junction_incoming_edges = {"j_synthetic": synth_dict}
            junction_types = {"j_synthetic": "traffic_light"}
            if not true_traffic_light_ids:
                true_traffic_light_ids = ["j_synthetic"]

        # 4. Group by junction: primary vs secondary edges
        processed_data = {}
        for j_id, incoming_edges in junction_incoming_edges.items():
            if not incoming_edges:
                continue

            edge_volumes = {edge_id: edge_volumes_cache.get(edge_id, 0.0) for edge_id in incoming_edges}
            sorted_edges, has_different_lanes, max_lanes, primary_ids = EdgeClassifier.classify(incoming_edges, edge_volumes)

            primary_edges = {}
            secondary_edges = {}

            for edge_id, edge_data in sorted_edges:
                edge_samples = samples_by_edge.get(edge_id, [])
                if not edge_samples:
                    continue

                for s in edge_samples:
                    if s.get('edge_length') is None:
                        s['edge_length'] = edge_data.get('length', 0)
                    if s.get('num_lanes') is None:
                        s['num_lanes'] = edge_data.get('num_lanes', 1)
                    if s.get('speed_limit') is None:
                        s['speed_limit'] = edge_data.get('speed_limit', 13.89)

                is_primary = (edge_data['num_lanes'] == max_lanes) if has_different_lanes else (edge_id in primary_ids)

                if is_primary:
                    primary_edges[edge_id] = edge_samples
                else:
                    secondary_edges[edge_id] = edge_samples

            if primary_edges or secondary_edges:
                processed_data[j_id] = {
                    'primary_edges': primary_edges,
                    'secondary_edges': secondary_edges,
                    'conflict_events': 0,
                    'type': junction_types.get(j_id, 'unknown'),
                }

        logging.info(f"[SAS_HISTORICAL_PROCESSOR] Processed {len(processed_data)} junctions from historical data using batching.")
        del edge_volumes_cache
        del samples_by_edge
        gc.collect()
        return processed_data, true_traffic_light_ids
