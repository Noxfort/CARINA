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

# File: src/repositories/fluid_dynamics_metrics.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.repositories.fluid_dynamics_query_provider import FluidDynamicsQueryProvider


class FluidDynamicsMetrics:
    """
    Handles counts, timestamp ranges, and statistical metadata for fluid dynamics tables.
    Queries are loaded dynamically via FluidDynamicsQueryProvider from config/fluid_dynamics_queries.json.
    """

    def __init__(self, engine: 'DatabaseEngine', query_provider: 'FluidDynamicsQueryProvider'):
        self.engine = engine
        self.query_provider = query_provider

    def get_fluid_dynamics_count(self) -> int:
        """Returns the total number of fluid dynamics samples in the database."""
        conn = self.engine.get_connection()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            sql = self.query_provider.get_query("get_count")
            cursor.execute(sql)
            count = cursor.fetchone()[0]
            if count == 0:
                sql_summary = self.query_provider.get_query("get_count_summary")
                cursor.execute(sql_summary)
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
                cutoff_dt = self.query_provider.get_cutoff_timestamp(conn, limit_seconds)
                sql = self.query_provider.get_query("get_min_max_time")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self.query_provider.get_query("get_min_max_time", "all")
                cursor.execute(sql)
            
            row = cursor.fetchone()
            if row and row[0] and row[1]:
                min_dt = self.query_provider.parse_timestamp(row[0])
                max_dt = self.query_provider.parse_timestamp(row[1])
                if min_dt and max_dt:
                    candidates_min.append(min_dt)
                    candidates_max.append(max_dt)

            # 2. Query synapse_edge_phase_hourly_summary
            try:
                sql_summary = self.query_provider.get_query("get_min_max_summary_hour")
                cursor.execute(sql_summary)
                row = cursor.fetchone()
                if row and row[0] and row[1]:
                    min_dt = self.query_provider.parse_timestamp(row[0])
                    max_dt = self.query_provider.parse_timestamp(row[1])
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
