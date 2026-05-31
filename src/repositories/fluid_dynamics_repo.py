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

import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend

class FluidDynamicsRepository:
    """
    Repository for managing synapse fluid dynamics samples (Traffic Monitoring).
    """
    def __init__(self, engine: 'DatabaseEngine', locale_manager: 'LocaleManagerBackend'):
        self.engine = engine
        self.locale_manager = locale_manager

    def insert_synapse_fluid_dynamics(self, samples: List[Dict]):
        """
        Batch-inserts a list of fluid dynamics sample dicts into the synapse_fluid_dynamics table.
        Each dict must contain: edge_id, density, mean_speed, queue_length, occupancy,
        and optionally: edge_length, num_lanes, speed_limit, collected_at.
        """
        if not samples:
            return
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            ph = "%s" if self.engine.db_type == "postgres" else "?"
            sql = (
                f"INSERT INTO synapse_fluid_dynamics "
                f"(collected_at, edge_id, density, mean_speed, queue_length, occupancy, edge_length, num_lanes, speed_limit) "
                f"VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph});"
            )
            now = datetime.now()
            rows = []
            for s in samples:
                rows.append((
                    s.get('collected_at', now),
                    s['edge_id'],
                    s['density'],
                    s['mean_speed'],
                    s['queue_length'],
                    s['occupancy'],
                    s.get('edge_length'),
                    s.get('num_lanes'),
                    s.get('speed_limit'),
                ))
            cursor.executemany(sql, rows)
            conn.commit()
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error inserting fluid dynamics samples: {e}")
        finally:
            if conn:
                conn.close()

    def query_fluid_dynamics_history(self) -> List[Dict]:
        """
        Retrieves ALL fluid dynamics samples currently stored in the database.
        Returns a list of dicts with all sample columns.
        """
        conn = self.engine.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT edge_id, density, mean_speed, queue_length, occupancy, "
                "edge_length, num_lanes, speed_limit, collected_at "
                "FROM synapse_fluid_dynamics ORDER BY collected_at;"
            )
            columns = ['edge_id', 'density', 'mean_speed', 'queue_length', 'occupancy',
                       'edge_length', 'num_lanes', 'speed_limit', 'collected_at']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error querying fluid dynamics history: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def purge_old_fluid_dynamics(self, keep_minutes: int = 1440):
        """
        Deletes fluid dynamics samples older than `keep_minutes` minutes.
        Default: 24 hours.
        """
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.engine.db_type == "postgres":
                cursor.execute(
                    "DELETE FROM synapse_fluid_dynamics WHERE collected_at < NOW() - INTERVAL '%s minutes';",
                    (keep_minutes,)
                )
            else:
                cursor.execute(
                    "DELETE FROM synapse_fluid_dynamics WHERE collected_at < datetime('now', ? || ' minutes');",
                    (f"-{keep_minutes}",)
                )
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
            cursor.execute("SELECT COUNT(*) FROM synapse_fluid_dynamics;")
            return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error counting fluid dynamics samples: {e}")
            return 0
        finally:
            if conn:
                conn.close()
