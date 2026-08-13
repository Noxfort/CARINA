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

# File: src/mfd/mfd_history_reconstructor.py
# Author: Gabriel Moraes
# Date: July 10, 2026

import logging
from typing import Optional, Any

from utils.locale_manager_backend import LocaleManagerBackend
from database.database_manager import DatabaseManager
from mfd.mfd_network_parser import MFDNetworkParser
from mfd.mfd_db_fetcher import MFDDataFetcher
from mfd.mfd_metrics_processor import MFDMetricsProcessor


class MFDHistoryReconstructor:
    """
    Orchestrator and Facade class responsible for reconstructing historical MFD snapshots.
    Delegates network XML parsing, DB batch fetching, and metric processing to specialized sub-modules.
    """

    def __init__(self, scenario_results_dir: str, db_manager: Optional[DatabaseManager] = None):
        self.scenario_results_dir = scenario_results_dir
        self.locale_manager = LocaleManagerBackend()
        self.db = db_manager or DatabaseManager(self.locale_manager)

        # Initialize sub-component handlers
        self.network_parser = MFDNetworkParser(scenario_results_dir)
        self.db_fetcher = MFDDataFetcher(self.db)
        self.metrics_processor = MFDMetricsProcessor()

    def get_earliest_child_timestamp(self) -> Optional[Any]:
        """Retrieves the earliest timestamp (collected_at) where maturity_stage == 'CHILD'."""
        return self.db_fetcher.get_earliest_child_timestamp()

    def _process_mfd_step_data(self, timestamp: str, edges_data: dict, edge_lengths: dict, edge_to_tl: dict) -> dict:
        """Forwarder helper for single step MFD metrics calculation."""
        return self.metrics_processor.process_mfd_step_data(timestamp, edges_data, edge_lengths, edge_to_tl)

    def reconstruct_from_db(self, batch_size: int = 50000) -> dict:
        """
        Reconstructs the MFD history and peak stats directly from the database
        using memory-efficient batch streaming, anchored to the earliest Infância (CHILD) timestamp.
        """
        # 1. Parse static SUMO network XML topology
        edge_lengths, edge_to_tl = self.network_parser.parse_network()

        # 2. Connect to database
        conn = self.db.engine.get_connection()
        if not conn:
            return {"peak_production": 0.0, "peak_accumulation": 0.0, "history": []}

        t_child = self.get_earliest_child_timestamp()
        if t_child:
            logging.info(f"[MFDHistoryReconstructor] Ancorando análise MFD no início da Fase Infância (CHILD / Linha Base) em {t_child}.")

        history = []
        peak_production = 0.0
        peak_accumulation = 0.0

        try:
            cursor = conn.cursor()
            query, params = self.db_fetcher.get_query_and_params(t_child, table="synapse_fluid_dynamics")
            cursor.execute(query, params)

            current_timestamp = None
            current_edges = {}
            has_rows = False

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                has_rows = True
                for row in rows:
                    if len(row) >= 8:
                        collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length, maturity_stage = row[:8]
                    else:
                        collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length = row[:7]
                        maturity_stage = 'CHILD'

                    timestamp_key = str(collected_at)
                    if current_timestamp is None:
                        current_timestamp = timestamp_key

                    if timestamp_key != current_timestamp:
                        step_data = self._process_mfd_step_data(
                            current_timestamp, current_edges, edge_lengths, edge_to_tl
                        )
                        if step_data:
                            history.append(step_data)
                            if step_data["production"] > peak_production:
                                peak_production = step_data["production"]
                                peak_accumulation = step_data["accumulation"]
                        current_timestamp = timestamp_key
                        current_edges = {}

                    current_edges[edge_id] = {
                        "density": float(density) if density is not None else 0.0,
                        "mean_speed": float(mean_speed) if mean_speed is not None else 0.0,
                        "queue_length": float(queue_length) if queue_length is not None else 0.0,
                        "occupancy": float(occupancy) if occupancy is not None else 0.0,
                        "edge_length": float(edge_length) if edge_length is not None else 100.0,
                        "maturity_stage": maturity_stage
                    }

            # Fallback to synapse_edge_phase_hourly_summary if no raw rows found
            if not has_rows:
                logging.info("[MFDHistoryReconstructor] synapse_fluid_dynamics is empty. Reconstructing MFD from synapse_edge_phase_hourly_summary.")
                query, params = self.db_fetcher.get_query_and_params(t_child, table="synapse_edge_phase_hourly_summary")
                cursor.execute(query, params)

                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    for row in rows:
                        collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length, maturity_stage = row[:8]
                        timestamp_key = str(collected_at)
                        if current_timestamp is None:
                            current_timestamp = timestamp_key

                        if timestamp_key != current_timestamp:
                            step_data = self._process_mfd_step_data(
                                current_timestamp, current_edges, edge_lengths, edge_to_tl
                            )
                            if step_data:
                                history.append(step_data)
                                if step_data["production"] > peak_production:
                                    peak_production = step_data["production"]
                                    peak_accumulation = step_data["accumulation"]
                            current_timestamp = timestamp_key
                            current_edges = {}

                        current_edges[edge_id] = {
                            "density": float(density) if density is not None else 0.0,
                            "mean_speed": float(mean_speed) if mean_speed is not None else 0.0,
                            "queue_length": float(queue_length) if queue_length is not None else 0.0,
                            "occupancy": float(occupancy) if occupancy is not None else 0.0,
                            "edge_length": float(edge_length) if edge_length is not None else 100.0,
                            "maturity_stage": maturity_stage
                        }

            # Process the last remaining step
            if current_edges:
                step_data = self._process_mfd_step_data(
                    current_timestamp, current_edges, edge_lengths, edge_to_tl
                )
                if step_data:
                    history.append(step_data)
                    if step_data["production"] > peak_production:
                        peak_production = step_data["production"]
                        peak_accumulation = step_data["accumulation"]

        except Exception as e:
            logging.error(f"[MFDHistoryReconstructor] Error processing MFD database batch: {e}", exc_info=True)
        finally:
            conn.close()

        # 3. Post-process history
        self.metrics_processor.post_process_history(history, peak_production, peak_accumulation)

        return {
            "peak_production": peak_production,
            "peak_accumulation": peak_accumulation,
            "history": history
        }
