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

# File: src/xai/mfd_history_reconstructor.py
# Author: Gabriel Moraes
# Date: July 10, 2026

import os
import logging
import gzip
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

from utils.locale_manager_backend import LocaleManagerBackend
from database.database_manager import DatabaseManager
from mfd.calculator import MFDCalculator

class MFDHistoryReconstructor:
    """
    Service class responsible for reconstructing historical Macroscopic Fundamental Diagram (MFD)
    snapshots from the database in a memory-efficient, batch-processed manner.
    
    Adheres to the Single Responsibility Principle (SRP) by isolating database access,
    SUMO static network XML parsing, and step-by-step fluidic MFD calculations.
    """
    
    def __init__(self, scenario_results_dir: str, db_manager: Optional[DatabaseManager] = None):
        self.scenario_results_dir = scenario_results_dir
        self.locale_manager = LocaleManagerBackend()
        self.db = db_manager or DatabaseManager(self.locale_manager)

    def get_earliest_child_timestamp(self) -> Optional[Any]:
        """
        Retrieves the earliest timestamp (collected_at) from PostgreSQL/SQLite where maturity_stage == 'CHILD'
        (or earliest checkpoint timestamp in cloud_file_vault) to serve as the Baseline (Linha Base / Ponto Zero).
        """
        conn = self.db.engine.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            candidates = []

            # 1. Query earliest CHILD maturity sample in synapse_fluid_dynamics
            cursor.execute("SELECT MIN(collected_at) FROM synapse_fluid_dynamics WHERE maturity_stage = 'CHILD';")
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            # 2. Query earliest overall sample in synapse_fluid_dynamics
            cursor.execute("SELECT MIN(collected_at) FROM synapse_fluid_dynamics;")
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            # 3. Query earliest timestamp in synapse_edge_phase_hourly_summary
            cursor.execute("SELECT MIN(summary_hour) FROM synapse_edge_phase_hourly_summary WHERE maturity_stage = 'CHILD';")
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            cursor.execute("SELECT MIN(summary_hour) FROM synapse_edge_phase_hourly_summary;")
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            # 4. Fallback: Query earliest checkpoint timestamp in cloud_file_vault
            cursor.execute("SELECT MIN(last_updated) FROM cloud_file_vault WHERE relative_path LIKE '%checkpoints/%.pth' OR relative_path LIKE '%.pth';")
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            if candidates:
                parsed_candidates = []
                for c in candidates:
                    if isinstance(c, str):
                        try:
                            from datetime import datetime
                            parsed_candidates.append(datetime.fromisoformat(c))
                        except Exception:
                            parsed_candidates.append(c)
                    else:
                        parsed_candidates.append(c)
                return min(parsed_candidates)

            return None
        except Exception as e:
            logging.warning(f"[MFDHistoryReconstructor] Failed to query earliest CHILD timestamp: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def reconstruct_from_db(self, batch_size: int = 50000) -> dict:
        """
        Reconstructs the MFD history and peak stats directly from the database (synapse_fluid_dynamics)
        using memory-efficient batch streaming, anchored to the earliest Infância (CHILD / Baseline) timestamp.
        Falls back to synapse_edge_phase_hourly_summary if synapse_fluid_dynamics is empty.
        """
        # 1. Locate static SUMO network XML file to map incoming edges EXCLUSIVELY to traffic_light junctions
        net_file = None
        maps_dir = os.path.join(self.scenario_results_dir, "maps")
        if os.path.exists(maps_dir):
            for f in os.listdir(maps_dir):
                if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                    net_file = os.path.join(maps_dir, f)
                    break

        if not net_file:
            try:
                from utils.paths import get_base_output_dir
                results_dir = os.path.join(get_base_output_dir(), "results")
                if os.path.exists(results_dir):
                    for root, dirs, files in os.walk(results_dir):
                        for f in files:
                            if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                                net_file = os.path.join(root, f)
                                break
                        if net_file:
                            break
            except Exception:
                pass
        
        edge_lengths = {}
        edge_to_tl = {}
        tls_junctions = set()
        
        if net_file:
            try:
                opener = gzip.open if net_file.endswith('.gz') else open
                with opener(net_file, 'rb') as f:
                    tree = ET.parse(f)
                root = tree.getroot()

                # Pass 1: Extract ONLY junctions with type='traffic_light' (ignore all unsignalized nodes)
                for junction in root.findall("junction"):
                    j_type = junction.get("type")
                    j_id = junction.get("id")
                    if j_type == "traffic_light" and j_id:
                        tls_junctions.add(j_id)

                # Pass 2: Map incoming edges ONLY if the target junction is a traffic_light
                for edge in root.findall("edge"):
                    edge_id = edge.get("id")
                    to_junction = edge.get("to")
                    func = edge.get("function", "")
                    if func == "internal" or (edge_id and edge_id.startswith(":")):
                        continue
                    
                    length = 0.0
                    for lane in edge.findall("lane"):
                        l_len = lane.get("length")
                        if l_len:
                            length = float(l_len)
                            break
                    if length <= 0.0:
                        l_len = edge.get("length")
                        if l_len:
                            length = float(l_len)
                            
                    if edge_id:
                        if length > 0:
                            edge_lengths[edge_id] = length
                        if to_junction and to_junction in tls_junctions:
                            edge_to_tl[edge_id] = to_junction
            except Exception as e:
                logging.error(f"[MFDHistoryReconstructor] Error parsing static network file {net_file}: {e}")

        # 2. Query database rows starting from the earliest Infância (CHILD / Baseline) timestamp
        conn = self.db.engine.get_connection()
        if not conn:
            return {"peak_production": 0.0, "peak_accumulation": 0.0, "history": []}

        t_child = self.get_earliest_child_timestamp()
        if t_child:
            logging.info(f"[MFDHistoryReconstructor] Ancorando análise MFD no início da Fase Infância (CHILD / Linha Base) em {t_child}.")
            if self.db.engine.db_type == "postgres":
                where_clause = "WHERE collected_at >= %s"
                where_clause_summary = "WHERE summary_hour >= %s"
                params = (t_child,)
            else:
                where_clause = "WHERE collected_at >= ?"
                where_clause_summary = "WHERE summary_hour >= ?"
                params = (str(t_child),)
        else:
            where_clause = ""
            where_clause_summary = ""
            params = ()
            
        history = []
        peak_production = 0.0
        peak_accumulation = 0.0
        
        try:
            cursor = conn.cursor()
            if where_clause:
                query = (
                    f"SELECT collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length, maturity_stage "
                    f"FROM ("
                    f"  SELECT collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length, maturity_stage "
                    f"  FROM synapse_fluid_dynamics {where_clause} "
                    f"  ORDER BY collected_at DESC LIMIT 50000"
                    f") SUB "
                    f"ORDER BY collected_at ASC;"
                )
                cursor.execute(query, params)
            else:
                query = (
                    "SELECT collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length, maturity_stage "
                    "FROM ("
                    "  SELECT collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length, maturity_stage "
                    "  FROM synapse_fluid_dynamics "
                    "  ORDER BY collected_at DESC LIMIT 50000"
                    ") SUB "
                    "ORDER BY collected_at ASC;"
                )
                cursor.execute(query)
            
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
                        # Process the accumulated step
                        step_data = self._process_mfd_step_data(
                            current_timestamp, current_edges, edge_lengths, edge_to_tl
                        )
                        if step_data:
                            history.append(step_data)
                            if step_data["production"] > peak_production:
                                peak_production = step_data["production"]
                                peak_accumulation = step_data["accumulation"]
                                
                        # Reset for next timestamp
                        current_timestamp = timestamp_key
                        current_edges = {}
                        
                    density = float(density) if density is not None else 0.0
                    mean_speed = float(mean_speed) if mean_speed is not None else 0.0
                    queue_length = float(queue_length) if queue_length is not None else 0.0
                    occupancy = float(occupancy) if occupancy is not None else 0.0
                    edge_length = float(edge_length) if edge_length is not None else 100.0

                    current_edges[edge_id] = {
                        "density": density,
                        "mean_speed": mean_speed,
                        "queue_length": queue_length,
                        "occupancy": occupancy,
                        "edge_length": edge_length,
                        "maturity_stage": maturity_stage
                    }

            # Fallback to synapse_edge_phase_hourly_summary if no raw rows found
            if not has_rows:
                logging.info("[MFDHistoryReconstructor] synapse_fluid_dynamics is empty. Reconstructing MFD from synapse_edge_phase_hourly_summary.")
                if where_clause_summary:
                    query = (
                        f"SELECT summary_hour AS collected_at, edge_id, avg_density AS density, avg_speed AS mean_speed, "
                        f"       avg_queue AS queue_length, avg_occupancy AS occupancy, 100.0 AS edge_length, maturity_stage "
                        f"FROM ("
                        f"  SELECT summary_hour, edge_id, avg_density, avg_speed, avg_queue, avg_occupancy, maturity_stage "
                        f"  FROM synapse_edge_phase_hourly_summary {where_clause_summary} "
                        f"  ORDER BY summary_hour DESC LIMIT 50000"
                        f") SUB "
                        f"ORDER BY summary_hour ASC;"
                    )
                    cursor.execute(query, params)
                else:
                    query = (
                        "SELECT summary_hour AS collected_at, edge_id, avg_density AS density, avg_speed AS mean_speed, "
                        "       avg_queue AS queue_length, avg_occupancy AS occupancy, 100.0 AS edge_length, maturity_stage "
                        "FROM ("
                        "  SELECT summary_hour, edge_id, avg_density, avg_speed, avg_queue, avg_occupancy, maturity_stage "
                        "  FROM synapse_edge_phase_hourly_summary "
                        "  ORDER BY summary_hour DESC LIMIT 50000"
                        ") SUB "
                        "ORDER BY summary_hour ASC;"
                    )
                    cursor.execute(query)

                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    for row in rows:
                        collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length, maturity_stage = row[:8]
                        density = float(density) if density is not None else 0.0
                        mean_speed = float(mean_speed) if mean_speed is not None else 0.0
                        queue_length = float(queue_length) if queue_length is not None else 0.0
                        occupancy = float(occupancy) if occupancy is not None else 0.0
                        edge_length = float(edge_length) if edge_length is not None else 100.0

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
                            "density": density,
                            "mean_speed": mean_speed,
                            "queue_length": queue_length,
                            "occupancy": occupancy,
                            "edge_length": edge_length,
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
            
        # 3. Post-process history to compute efficiency and congestion ratio using peak values
        for snapshot in history:
            if peak_production > 0:
                snapshot["efficiency"] = min(snapshot["production"] / peak_production, 1.0)
            else:
                snapshot["efficiency"] = 1.0
                
            if peak_accumulation > 0:
                snapshot["congestion_ratio"] = snapshot["accumulation"] / peak_accumulation
            else:
                snapshot["congestion_ratio"] = 0.0
                
        return {
            "peak_production": peak_production,
            "peak_accumulation": peak_accumulation,
            "history": history
        }

    def _process_mfd_step_data(self, timestamp: str, edges_data: dict, edge_lengths: dict, edge_to_tl: dict) -> dict:
        """Helper to calculate MFD metrics for a single simulation step."""
        # Determine actual edge lengths
        lengths_dict = {
            edge_id: data.get("edge_length") or edge_lengths.get(edge_id, 100.0)
            for edge_id, data in edges_data.items()
        }
        
        production, accumulation, mean_speed, mean_density, mean_flow, active_edges = (
            MFDCalculator.compute_network_metrics(edges_data, lengths_dict, topology_loaded=True)
        )
        
        # Calculate intersection metrics
        # Group incoming edges of each traffic light
        tl_groups = {}
        for edge_id, data in edges_data.items():
            tl_id = edge_to_tl.get(edge_id)
            if tl_id:
                if tl_id not in tl_groups:
                    tl_groups[tl_id] = []
                tl_groups[tl_id].append((edge_id, data))
                
        intersections = {}
        for tl_id, edges_list in tl_groups.items():
            local_prod = 0.0
            local_accum = 0.0
            local_weighted_speed = 0.0
            local_total_len = 0.0
            local_queue = 0.0
            
            for edge_id, data in edges_list:
                length = lengths_dict.get(edge_id, 100.0)
                density = data.get("density", 0.0)
                speed = data.get("mean_speed", 0.0)
                occupancy = data.get("occupancy", 0.0)
                queue = data.get("queue_length", 0.0)
                
                if density <= 0 and occupancy > 0:
                    density = occupancy
                    
                flow = density * speed
                local_prod += flow * length
                local_accum += density * length
                local_weighted_speed += speed * length
                local_total_len += length
                local_queue += queue
                
            avg_speed = (local_weighted_speed / local_total_len) if local_total_len > 0 else 0.0
            first_edge_data = edges_list[0][1] if edges_list else {}
            mat_stage = first_edge_data.get("maturity_stage", "CHILD")
            intersections[tl_id] = {
                "production": round(local_prod, 4),
                "accumulation": round(local_accum, 4),
                "mean_speed": round(avg_speed, 2),
                "queue_length": int(local_queue),
                "maturity_stage": mat_stage
            }
            
        try:
            timestamp_val = float(timestamp)
        except ValueError:
            timestamp_val = timestamp
            
        return {
            "timestamp": timestamp_val,
            "accumulation": accumulation,
            "production": production,
            "mean_speed": mean_speed,
            "mean_density": mean_density,
            "mean_flow": mean_flow,
            "active_edges": active_edges,
            "intersections": intersections
        }
