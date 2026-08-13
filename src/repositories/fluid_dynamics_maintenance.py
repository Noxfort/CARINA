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

# File: src/repositories/fluid_dynamics_maintenance.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.repositories.fluid_dynamics_query_provider import FluidDynamicsQueryProvider


class FluidDynamicsMaintenance:
    """
    Handles data retention, hourly consolidation, and table purging for fluid dynamics tables.
    Queries are loaded dynamically via FluidDynamicsQueryProvider from config/fluid_dynamics_queries.json.
    """

    def __init__(self, engine: 'DatabaseEngine', query_provider: 'FluidDynamicsQueryProvider'):
        self.engine = engine
        self.query_provider = query_provider

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
                sql_min = self.query_provider.get_query("get_min_collected_before")
                cursor.execute(sql_min, (keep_hours,))
                row = cursor.fetchone()
                if not row or not row[0]:
                    return
                min_ts = row[0]
                
                sql_cutoff = self.query_provider.get_query("get_cutoff_timestamp_interval")
                cursor.execute(sql_cutoff, (keep_hours,))
                cutoff_ts = cursor.fetchone()[0]

                sql_next_batch = self.query_provider.get_query("get_next_batch_timestamp")
                sql_edge = self.query_provider.get_query("consolidate_edge_summary")
                sql_intersection = self.query_provider.get_query("consolidate_intersection_summary")
                sql_purge = self.query_provider.get_query("purge_consolidated_window")

                current_start = min_ts
                while current_start < cutoff_ts:
                    cursor.execute(sql_next_batch, (current_start, batch_days))
                    current_end = min(cursor.fetchone()[0], cutoff_ts)

                    # 1. Consolidate into Edge Hourly Summary
                    cursor.execute(sql_edge, (current_start, current_end))

                    # 2. Consolidate into Intersection Hourly Summary
                    cursor.execute(sql_intersection, (current_start, current_end))

                    # 3. Purge consolidated raw rows for this window
                    cursor.execute(sql_purge, (current_start, current_end))
                    conn.commit()
                    logging.info(f"[DB_MANAGER] Consolidated and purged raw fluid dynamics window {current_start} to {current_end}.")
                    
                    if current_end >= cutoff_ts:
                        break
                    current_start = current_end
            else:
                sql_edge = self.query_provider.get_query("consolidate_edge_summary")
                sql_intersection = self.query_provider.get_query("consolidate_intersection_summary")
                sql_purge = self.query_provider.get_query("purge_consolidated_window")

                param = f"-{keep_hours}"
                cursor.execute(sql_edge, (param,))
                cursor.execute(sql_intersection, (param,))
                cursor.execute(sql_purge, (param,))
                conn.commit()
                logging.info(f"[DB_MANAGER] Consolidated and purged raw fluid dynamics older than {keep_hours} hours.")
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error consolidating and purging old fluid dynamics: {e}")
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
            sql = self.query_provider.get_query("purge_old")
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
