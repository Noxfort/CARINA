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

# File: src/repositories/fluid_dynamics_repo.py
# Author: Gabriel Moraes
# Date: May 31, 2026

import os
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Dict, Optional, Tuple

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend

class FluidDynamicsRepository:
    """
    Repository for managing synapse fluid dynamics samples (Traffic Monitoring).
    Loads SQL statements dynamically from config/fluid_dynamics_queries.json.
    """
    SAMPLE_COLUMNS = [
        'edge_id', 'density', 'mean_speed', 'queue_length', 'occupancy',
        'edge_length', 'num_lanes', 'speed_limit', 'collected_at'
    ]
    AGGREGATED_COLUMNS = [
        'edge_id', 'volume_sum', 'volume_cnt', 'delay_sum', 'delay_cnt',
        'avg_queue', 'max_queue', 'edge_length', 'num_lanes', 'speed_limit', 'total_samples'
    ]

    _queries_cache = None

    def __init__(self, engine: 'DatabaseEngine', locale_manager: 'LocaleManagerBackend'):
        self.engine = engine
        self.locale_manager = locale_manager
        self._load_queries()

    @classmethod
    def _load_queries(cls):
        if cls._queries_cache is not None:
            return
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            json_path = os.path.join(base_dir, "config", "fluid_dynamics_queries.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    cls._queries_cache = json.load(f)
            else:
                logging.warning(f"[FluidDynamicsRepository] Query config file not found at: {json_path}")
                cls._queries_cache = {}
        except Exception as e:
            logging.error(f"[FluidDynamicsRepository] Failed to load fluid_dynamics_queries.json: {e}")
            cls._queries_cache = {}

    def _get_query(self, query_key: str, key_suffix: str = None) -> str:
        if self._queries_cache is None:
            self._load_queries()
        
        q_dict = self._queries_cache.get(query_key, {})
        if isinstance(q_dict, str):
            return q_dict
        
        db_type = getattr(self.engine, "db_type", "sqlite")
        
        if key_suffix:
            lookup_key = f"{db_type}_{key_suffix}"
            if lookup_key in q_dict:
                return q_dict[lookup_key]
            if key_suffix in q_dict:
                return q_dict[key_suffix]

        if db_type in q_dict:
            return q_dict[db_type]
        if "all" in q_dict:
            return q_dict["all"]
        return ""

    def insert_synapse_fluid_dynamics(self, samples: List[Dict]):
        """
        Batch-inserts a list of fluid dynamics sample dicts into the synapse_fluid_dynamics table.
        """
        if not samples:
            return
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            sql = self._get_query("insert_sample")
            now = datetime.now()
            rows = []
            for s in samples:
                rows.append((
                    s.get('collected_at', now),
                    s.get('scenario_name', 'default'),
                    s.get('intersection_id'),
                    s['edge_id'],
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
                ))
            cursor.executemany(sql, rows)
            conn.commit()
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error inserting fluid dynamics samples: {e}")
        finally:
            if conn:
                conn.close()

    def consolidate_and_purge_old_data(self, keep_hours: int = 48, batch_days: int = 1):
        """
        Consolidates raw fluid dynamics data older than keep_hours into hourly summary tables
        (synapse_edge_phase_hourly_summary and synapse_intersection_phase_hourly_summary)
        and purges raw rows from synapse_fluid_dynamics in memory-safe, non-blocking daily chunks.
        """
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.engine.db_type == "postgres":
                cursor.execute("SELECT MIN(collected_at) FROM synapse_fluid_dynamics WHERE collected_at < NOW() - INTERVAL '%s hours';", (keep_hours,))
                row = cursor.fetchone()
                if not row or not row[0]:
                    return
                min_ts = row[0]
                
                cursor.execute("SELECT (NOW() - INTERVAL '%s hours')::timestamp;", (keep_hours,))
                cutoff_ts = cursor.fetchone()[0]

                current_start = min_ts
                while current_start < cutoff_ts:
                    cursor.execute("SELECT (%s::timestamp + INTERVAL '%s days')::timestamp;", (current_start, batch_days))
                    current_end = min(cursor.fetchone()[0], cutoff_ts)

                    # 1. Consolidate into Edge Hourly Summary
                    cursor.execute("""
                        INSERT INTO synapse_edge_phase_hourly_summary 
                        (edge_id, maturity_stage, summary_hour, scenario_name, sample_count, avg_speed, min_speed, avg_density, avg_queue, max_queue, total_production, avg_occupancy)
                        SELECT 
                            edge_id,
                            maturity_stage,
                            date_trunc('hour', collected_at) AS summary_hour,
                            scenario_name,
                            COUNT(*) AS sample_count,
                            AVG(mean_speed) AS avg_speed,
                            MIN(COALESCE(min_speed, mean_speed)) AS min_speed,
                            AVG(density) AS avg_density,
                            AVG(queue_length) AS avg_queue,
                            MAX(COALESCE(max_queue, queue_length)) AS max_queue,
                            SUM(density * mean_speed * COALESCE(edge_length, 100.0)) AS total_production,
                            AVG(occupancy) AS avg_occupancy
                        FROM synapse_fluid_dynamics
                        WHERE collected_at >= %s AND collected_at < %s
                        GROUP BY edge_id, maturity_stage, date_trunc('hour', collected_at), scenario_name
                        ON CONFLICT (edge_id, maturity_stage, summary_hour) DO UPDATE SET
                            sample_count = EXCLUDED.sample_count,
                            avg_speed = EXCLUDED.avg_speed,
                            min_speed = EXCLUDED.min_speed,
                            avg_density = EXCLUDED.avg_density,
                            avg_queue = EXCLUDED.avg_queue,
                            max_queue = EXCLUDED.max_queue,
                            total_production = EXCLUDED.total_production,
                            avg_occupancy = EXCLUDED.avg_occupancy;
                    """, (current_start, current_end))

                    # 2. Consolidate into Intersection Hourly Summary
                    cursor.execute("""
                        INSERT INTO synapse_intersection_phase_hourly_summary 
                        (intersection_id, maturity_stage, summary_hour, scenario_name, sample_count, avg_speed, min_speed, avg_queue, max_queue, total_production, total_delay)
                        SELECT 
                            COALESCE(intersection_id, 'unassigned') AS intersection_id,
                            maturity_stage,
                            date_trunc('hour', collected_at) AS summary_hour,
                            scenario_name,
                            COUNT(*) AS sample_count,
                            AVG(mean_speed) AS avg_speed,
                            MIN(COALESCE(min_speed, mean_speed)) AS min_speed,
                            AVG(queue_length) AS avg_queue,
                            MAX(COALESCE(max_queue, queue_length)) AS max_queue,
                            SUM(density * mean_speed * COALESCE(edge_length, 100.0)) AS total_production,
                            SUM(CASE WHEN mean_speed > 0.1 THEN GREATEST(0.0, (COALESCE(edge_length, 100.0) / mean_speed) - (COALESCE(edge_length, 100.0) / COALESCE(NULLIF(speed_limit, 0), 13.89))) ELSE 0.0 END) AS total_delay
                        FROM synapse_fluid_dynamics
                        WHERE collected_at >= %s AND collected_at < %s
                        GROUP BY COALESCE(intersection_id, 'unassigned'), maturity_stage, date_trunc('hour', collected_at), scenario_name
                        ON CONFLICT (intersection_id, maturity_stage, summary_hour) DO UPDATE SET
                            sample_count = EXCLUDED.sample_count,
                            avg_speed = EXCLUDED.avg_speed,
                            min_speed = EXCLUDED.min_speed,
                            avg_queue = EXCLUDED.avg_queue,
                            max_queue = EXCLUDED.max_queue,
                            total_production = EXCLUDED.total_production,
                            total_delay = EXCLUDED.total_delay;
                    """, (current_start, current_end))

                    # 3. Purge consolidated raw rows for this window
                    cursor.execute("DELETE FROM synapse_fluid_dynamics WHERE collected_at >= %s AND collected_at < %s;", (current_start, current_end))
                    conn.commit()
                    logging.info(f"[DB_MANAGER] Consolidated and purged raw fluid dynamics window {current_start} to {current_end}.")
                    
                    if current_end >= cutoff_ts:
                        break
                    current_start = current_end
            else:
                cutoff_sql = f"datetime('now', '-{keep_hours} hours')"
                cursor.execute(f"""
                    INSERT OR REPLACE INTO synapse_edge_phase_hourly_summary 
                    (edge_id, maturity_stage, summary_hour, scenario_name, sample_count, avg_speed, min_speed, avg_density, avg_queue, max_queue, total_production, avg_occupancy)
                    SELECT 
                        edge_id,
                        maturity_stage,
                        strftime('%Y-%m-%d %H:00:00', collected_at) AS summary_hour,
                        scenario_name,
                        COUNT(*) AS sample_count,
                        AVG(mean_speed) AS avg_speed,
                        MIN(COALESCE(min_speed, mean_speed)) AS min_speed,
                        AVG(density) AS avg_density,
                        AVG(queue_length) AS avg_queue,
                        MAX(COALESCE(max_queue, queue_length)) AS max_queue,
                        SUM(density * mean_speed * COALESCE(edge_length, 100.0)) AS total_production,
                        AVG(occupancy) AS avg_occupancy
                    FROM synapse_fluid_dynamics
                    WHERE collected_at < {cutoff_sql}
                    GROUP BY edge_id, maturity_stage, strftime('%Y-%m-%d %H:00:00', collected_at), scenario_name;
                """)
                cursor.execute(f"""
                    INSERT OR REPLACE INTO synapse_intersection_phase_hourly_summary 
                    (intersection_id, maturity_stage, summary_hour, scenario_name, sample_count, avg_speed, min_speed, avg_queue, max_queue, total_production, total_delay)
                    SELECT 
                        COALESCE(intersection_id, 'unassigned') AS intersection_id,
                        maturity_stage,
                        strftime('%Y-%m-%d %H:00:00', collected_at) AS summary_hour,
                        scenario_name,
                        COUNT(*) AS sample_count,
                        AVG(mean_speed) AS avg_speed,
                        MIN(COALESCE(min_speed, mean_speed)) AS min_speed,
                        AVG(queue_length) AS avg_queue,
                        MAX(COALESCE(max_queue, queue_length)) AS max_queue,
                        SUM(density * mean_speed * COALESCE(edge_length, 100.0)) AS total_production,
                        SUM(0.0) AS total_delay
                    FROM synapse_fluid_dynamics
                    WHERE collected_at < {cutoff_sql}
                    GROUP BY COALESCE(intersection_id, 'unassigned'), maturity_stage, strftime('%Y-%m-%d %H:00:00', collected_at), scenario_name;
                """)
                cursor.execute(f"DELETE FROM synapse_fluid_dynamics WHERE collected_at < {cutoff_sql};")
                conn.commit()
                logging.info(f"[DB_MANAGER] Consolidated and purged raw fluid dynamics older than {keep_hours} hours.")
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error consolidating and purging old fluid dynamics: {e}")
        finally:
            if conn:
                conn.close()

    def _get_cutoff_timestamp(self, conn, limit_seconds: int):
        """
        Computes the cutoff timestamp anchored to the MAX timestamp present in the DB
        across both synapse_fluid_dynamics and synapse_edge_phase_hourly_summary.
        """
        try:
            cursor = conn.cursor()
            sql = self._get_query("get_max_collected_at")
            cursor.execute(sql)
            row = cursor.fetchone()
            max_dt = None
            if row and row[0]:
                val = row[0]
                max_dt = self._parse_timestamp(val)

            # Fallback to hourly summary table if synapse_fluid_dynamics is empty
            if max_dt is None:
                try:
                    cursor.execute("SELECT MAX(summary_hour) FROM synapse_edge_phase_hourly_summary;")
                    s_row = cursor.fetchone()
                    if s_row and s_row[0]:
                        max_dt = self._parse_timestamp(s_row[0])
                except Exception:
                    pass

            if max_dt is None:
                max_dt = datetime.now()

            return max_dt - timedelta(seconds=limit_seconds)
        except Exception as e:
            logging.warning(f"[DB_MANAGER] Could not fetch MAX timestamp, fallback to datetime.now(): {e}")
            return datetime.now() - timedelta(seconds=limit_seconds)

    @staticmethod
    def _parse_timestamp(val) -> Optional[datetime]:
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                pass
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    continue
        return None

    def query_fluid_dynamics_history(self, limit_seconds: int = None) -> List[Dict]:
        """
        Retrieves fluid dynamics samples currently stored in the database.
        """
        conn = self.engine.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            if limit_seconds is not None:
                cutoff_dt = self._get_cutoff_timestamp(conn, limit_seconds)
                sql = self._get_query("query_history")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self._get_query("query_history", "all")
                cursor.execute(sql)

            return [dict(zip(self.SAMPLE_COLUMNS, row)) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error querying fluid dynamics history: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def query_fluid_dynamics_history_batches(self, limit_seconds: int = None, batch_size: int = 50000):
        """
        Yields batches of fluid dynamics samples from the database.
        Falls back to synapse_edge_phase_hourly_summary if synapse_fluid_dynamics is empty.
        """
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            if self.engine.db_type == "postgres":
                cursor = conn.cursor(name='sas_server_cursor')
                cursor.itersize = batch_size
            else:
                cursor = conn.cursor()

            if limit_seconds is not None:
                cutoff_dt = self._get_cutoff_timestamp(conn, limit_seconds)
                sql = self._get_query("query_history")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self._get_query("query_history", "all")
                cursor.execute(sql)

            has_data = False
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                has_data = True
                yield [dict(zip(self.SAMPLE_COLUMNS, row)) for row in rows]

            # Fallback to consolidated summary table if no raw data returned
            if not has_data:
                logging.info("[DB_MANAGER] synapse_fluid_dynamics empty. Falling back to synapse_edge_phase_hourly_summary for history batches.")
                if self.engine.db_type == "postgres" and hasattr(cursor, 'close'):
                    cursor.close()
                cursor = conn.cursor()
                if limit_seconds is not None:
                    cutoff_dt = self._get_cutoff_timestamp(conn, limit_seconds)
                    query = """
                        SELECT edge_id, avg_density AS density, avg_speed AS mean_speed, 
                               avg_queue AS queue_length, avg_occupancy AS occupancy,
                               100.0 AS edge_length, 1 AS num_lanes, 50.0 AS speed_limit, summary_hour AS collected_at
                        FROM synapse_edge_phase_hourly_summary
                        WHERE summary_hour >= %s
                        ORDER BY summary_hour ASC;
                    """ if self.engine.db_type == "postgres" else """
                        SELECT edge_id, avg_density AS density, avg_speed AS mean_speed, 
                               avg_queue AS queue_length, avg_occupancy AS occupancy,
                               100.0 AS edge_length, 1 AS num_lanes, 50.0 AS speed_limit, summary_hour AS collected_at
                        FROM synapse_edge_phase_hourly_summary
                        WHERE summary_hour >= ?
                        ORDER BY summary_hour ASC;
                    """
                    param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                    cursor.execute(query, (param,))
                else:
                    query = """
                        SELECT edge_id, avg_density AS density, avg_speed AS mean_speed, 
                               avg_queue AS queue_length, avg_occupancy AS occupancy,
                               100.0 AS edge_length, 1 AS num_lanes, 50.0 AS speed_limit, summary_hour AS collected_at
                        FROM synapse_edge_phase_hourly_summary
                        ORDER BY summary_hour ASC;
                    """
                    cursor.execute(query)
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    yield [dict(zip(self.SAMPLE_COLUMNS, row)) for row in rows]
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error querying fluid dynamics history in batches: {e}")
        finally:
            if conn:
                conn.close()

    def query_aggregated_fluid_dynamics(self, limit_seconds: int = None) -> List[Dict]:
        """
        Executes a Pushdown Aggregation Query directly on PostgreSQL/SQLite via GROUP BY edge_id.
        Falls back to synapse_edge_phase_hourly_summary if synapse_fluid_dynamics is empty.
        """
        conn = self.engine.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            if limit_seconds is not None:
                cutoff_dt = self._get_cutoff_timestamp(conn, limit_seconds)
                sql = self._get_query("query_aggregated")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self._get_query("query_aggregated", "all")
                cursor.execute(sql)

            results = [dict(zip(self.AGGREGATED_COLUMNS, row)) for row in cursor.fetchall()]
            if not results:
                logging.info("[DB_MANAGER] synapse_fluid_dynamics empty. Falling back to synapse_edge_phase_hourly_summary for aggregated pushdown query.")
                if limit_seconds is not None:
                    cutoff_dt = self._get_cutoff_timestamp(conn, limit_seconds)
                    query = """
                        SELECT 
                            edge_id,
                            SUM(avg_density * avg_speed * sample_count) AS volume_sum,
                            SUM(sample_count) AS volume_cnt,
                            0.0 AS delay_sum,
                            SUM(sample_count) AS delay_cnt,
                            AVG(avg_queue) AS avg_queue,
                            MAX(max_queue) AS max_queue,
                            100.0 AS edge_length,
                            1 AS num_lanes,
                            50.0 AS speed_limit,
                            SUM(sample_count) AS total_samples
                        FROM synapse_edge_phase_hourly_summary
                        WHERE summary_hour >= %s
                        GROUP BY edge_id;
                    """ if self.engine.db_type == "postgres" else """
                        SELECT 
                            edge_id,
                            SUM(avg_density * avg_speed * sample_count) AS volume_sum,
                            SUM(sample_count) AS volume_cnt,
                            0.0 AS delay_sum,
                            SUM(sample_count) AS delay_cnt,
                            AVG(avg_queue) AS avg_queue,
                            MAX(max_queue) AS max_queue,
                            100.0 AS edge_length,
                            1 AS num_lanes,
                            50.0 AS speed_limit,
                            SUM(sample_count) AS total_samples
                        FROM synapse_edge_phase_hourly_summary
                        WHERE summary_hour >= ?
                        GROUP BY edge_id;
                    """
                    param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                    cursor.execute(query, (param,))
                else:
                    query = """
                        SELECT 
                            edge_id,
                            SUM(avg_density * avg_speed * sample_count) AS volume_sum,
                            SUM(sample_count) AS volume_cnt,
                            0.0 AS delay_sum,
                            SUM(sample_count) AS delay_cnt,
                            AVG(avg_queue) AS avg_queue,
                            MAX(max_queue) AS max_queue,
                            100.0 AS edge_length,
                            1 AS num_lanes,
                            50.0 AS speed_limit,
                            SUM(sample_count) AS total_samples
                        FROM synapse_edge_phase_hourly_summary
                        GROUP BY edge_id;
                    """
                    cursor.execute(query)
                results = [dict(zip(self.AGGREGATED_COLUMNS, row)) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error querying aggregated fluid dynamics: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def purge_old_fluid_dynamics(self, keep_minutes: int = 1440):
        """
        Deletes fluid dynamics samples older than `keep_minutes` minutes.
        """
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            sql = self._get_query("purge_old")
            param = keep_minutes if self.engine.db_type == "postgres" else f"-{keep_minutes}"
            cursor.execute(sql, (param,))
            deleted = cursor.rowcount
            conn.commit()
            if deleted > 0:
                logging.info(f"[DB_MANAGER] Purged {deleted} old fluid dynamics samples (>{keep_minutes}min).")
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error purging old fluid dynamics samples: {e}")
        finally:
            if conn:
                conn.close()

    def get_fluid_dynamics_count(self) -> int:
        """Returns the total number of fluid dynamics samples in the database."""
        conn = self.engine.get_connection()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            sql = self._get_query("get_count")
            cursor.execute(sql)
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute("SELECT COUNT(*) FROM synapse_edge_phase_hourly_summary;")
                count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error counting fluid dynamics samples: {e}")
            return 0
        finally:
            if conn:
                conn.close()

    def get_fluid_dynamics_time_range(self) -> float:
        """
        Calculates the difference in seconds between the oldest and newest sample across both
        synapse_fluid_dynamics and synapse_edge_phase_hourly_summary tables.
        """
        min_dt, max_dt = self.get_fluid_dynamics_min_max_timestamps()
        if min_dt and max_dt:
            return (max_dt - min_dt).total_seconds()
        return 0.0

    def get_fluid_dynamics_min_max_timestamps(self, limit_seconds: Optional[int] = None) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Queries the MIN and MAX timestamps across synapse_fluid_dynamics and synapse_edge_phase_hourly_summary tables.
        """
        conn = self.engine.get_connection()
        if not conn:
            return None, None
        try:
            cursor = conn.cursor()
            candidates_min = []
            candidates_max = []

            # 1. Query synapse_fluid_dynamics
            if limit_seconds is not None:
                cutoff_dt = self._get_cutoff_timestamp(conn, limit_seconds)
                sql = self._get_query("get_min_max_time")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self._get_query("get_min_max_time", "all")
                cursor.execute(sql)
            
            row = cursor.fetchone()
            if row and row[0] and row[1]:
                min_dt = self._parse_timestamp(row[0])
                max_dt = self._parse_timestamp(row[1])
                if min_dt and max_dt:
                    candidates_min.append(min_dt)
                    candidates_max.append(max_dt)

            # 2. Query synapse_edge_phase_hourly_summary
            try:
                cursor.execute("SELECT MIN(summary_hour), MAX(summary_hour) FROM synapse_edge_phase_hourly_summary;")
                row = cursor.fetchone()
                if row and row[0] and row[1]:
                    min_dt = self._parse_timestamp(row[0])
                    max_dt = self._parse_timestamp(row[1])
                    if min_dt and max_dt:
                        candidates_min.append(min_dt)
                        candidates_max.append(max_dt)
            except Exception:
                pass

            if candidates_min and candidates_max:
                return min(candidates_min), max(candidates_max)

            return None, None
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error querying fluid dynamics min/max timestamps: {e}")
            return None, None
        finally:
            if conn:
                conn.close()
