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

# File: src/repositories/fluid_dynamics_reader.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import logging
from typing import TYPE_CHECKING, List, Dict, Optional

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.repositories.fluid_dynamics_query_provider import FluidDynamicsQueryProvider


class FluidDynamicsReader:
    """
    Handles read queries, streaming batch queries, and pushdown aggregations for fluid dynamics data.
    Queries are loaded dynamically via FluidDynamicsQueryProvider from config/fluid_dynamics_queries.json.
    """

    def __init__(
        self,
        engine: 'DatabaseEngine',
        query_provider: 'FluidDynamicsQueryProvider',
        sample_columns: List[str],
        aggregated_columns: List[str]
    ):
        self.engine = engine
        self.query_provider = query_provider
        self.sample_columns = sample_columns
        self.aggregated_columns = aggregated_columns

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
                cutoff_dt = self.query_provider.get_cutoff_timestamp(conn, limit_seconds)
                sql = self.query_provider.get_query("query_history")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self.query_provider.get_query("query_history", "all")
                cursor.execute(sql)

            return [dict(zip(self.sample_columns, row)) for row in cursor.fetchall()]
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
                cutoff_dt = self.query_provider.get_cutoff_timestamp(conn, limit_seconds)
                sql = self.query_provider.get_query("query_history")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self.query_provider.get_query("query_history", "all")
                cursor.execute(sql)

            has_data = False
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                has_data = True
                yield [dict(zip(self.sample_columns, row)) for row in rows]

            # Fallback to consolidated summary table if no raw data returned
            if not has_data:
                logging.info("[DB_MANAGER] synapse_fluid_dynamics empty. Falling back to synapse_edge_phase_hourly_summary for history batches.")
                if self.engine.db_type == "postgres" and hasattr(cursor, 'close'):
                    cursor.close()
                cursor = conn.cursor()
                if limit_seconds is not None:
                    cutoff_dt = self.query_provider.get_cutoff_timestamp(conn, limit_seconds)
                    query = self.query_provider.get_query("fallback_history_batches")
                    param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                    cursor.execute(query, (param,))
                else:
                    query = self.query_provider.get_query("fallback_history_batches", "all")
                    cursor.execute(query)
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    yield [dict(zip(self.sample_columns, row)) for row in rows]
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
                cutoff_dt = self.query_provider.get_cutoff_timestamp(conn, limit_seconds)
                sql = self.query_provider.get_query("query_aggregated")
                param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                cursor.execute(sql, (param,))
            else:
                sql = self.query_provider.get_query("query_aggregated", "all")
                cursor.execute(sql)

            results = [dict(zip(self.aggregated_columns, row)) for row in cursor.fetchall()]
            if not results:
                logging.info("[DB_MANAGER] synapse_fluid_dynamics empty. Falling back to synapse_edge_phase_hourly_summary for aggregated pushdown query.")
                if limit_seconds is not None:
                    cutoff_dt = self.query_provider.get_cutoff_timestamp(conn, limit_seconds)
                    query = self.query_provider.get_query("fallback_aggregated")
                    param = cutoff_dt if self.engine.db_type == "postgres" else cutoff_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                    cursor.execute(query, (param,))
                else:
                    query = self.query_provider.get_query("fallback_aggregated", "all")
                    cursor.execute(query)
                results = [dict(zip(self.aggregated_columns, row)) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error querying aggregated fluid dynamics: {e}")
            return []
        finally:
            if conn:
                conn.close()
