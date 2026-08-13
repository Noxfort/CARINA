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

# File: src/mfd/mfd_db_fetcher.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import logging
from typing import TYPE_CHECKING, Optional, Any, Tuple
from repositories.fluid_dynamics_query_provider import FluidDynamicsQueryProvider

if TYPE_CHECKING:
    from database.database_manager import DatabaseManager


class MFDDataFetcher:
    """
    Handles database queries for retrieving baseline timestamps and batch streaming
    fluid dynamics rows for MFD reconstruction.
    Queries are loaded dynamically via FluidDynamicsQueryProvider from config/fluid_dynamics_queries.json.
    """

    def __init__(self, db_manager: 'DatabaseManager'):
        self.db = db_manager
        self.query_provider = FluidDynamicsQueryProvider(db_manager.engine)

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
            cursor.execute(self.query_provider.get_query("get_earliest_child_sfd"))
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            # 2. Query earliest overall sample in synapse_fluid_dynamics
            cursor.execute(self.query_provider.get_query("get_earliest_sfd"))
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            # 3. Query earliest timestamp in synapse_edge_phase_hourly_summary
            cursor.execute(self.query_provider.get_query("get_earliest_child_summary"))
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            cursor.execute(self.query_provider.get_query("get_earliest_summary"))
            row = cursor.fetchone()
            if row and row[0] is not None:
                candidates.append(row[0])

            # 4. Fallback: Query earliest checkpoint timestamp in cloud_file_vault
            cursor.execute(self.query_provider.get_query("get_earliest_checkpoint"))
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
            logging.warning(f"[MFDDataFetcher] Failed to query earliest CHILD timestamp: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_query_and_params(self, t_child: Optional[Any], table: str) -> Tuple[str, Tuple]:
        """Constructs SQL query and parameters based on baseline timestamp and database engine from JSON config."""
        query_key = "mfd_reconstruct_sfd" if table == "synapse_fluid_dynamics" else "mfd_reconstruct_summary"

        if t_child:
            query = self.query_provider.get_query(query_key)
            param = t_child if self.db.engine.db_type == "postgres" else str(t_child)
            params = (param,)
        else:
            query = self.query_provider.get_query(query_key, "all")
            params = ()

        return query, params
