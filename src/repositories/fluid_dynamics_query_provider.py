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

# File: src/repositories/fluid_dynamics_query_provider.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import os
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine


class FluidDynamicsQueryProvider:
    """
    Manages loading and resolving SQL query templates for fluid dynamics operations.
    Handles DB engine dialect resolution (SQLite / PostgreSQL) and timestamp helpers.
    """
    _queries_cache = None

    def __init__(self, engine: 'DatabaseEngine'):
        self.engine = engine
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
                logging.warning(f"[FluidDynamicsQueryProvider] Query config file not found at: {json_path}")
                cls._queries_cache = {}
        except Exception as e:
            logging.error(f"[FluidDynamicsQueryProvider] Failed to load fluid_dynamics_queries.json: {e}")
            cls._queries_cache = {}

    def get_query(self, query_key: str, key_suffix: str = None) -> str:
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

    def get_cutoff_timestamp(self, conn, limit_seconds: int) -> datetime:
        """
        Computes the cutoff timestamp anchored to the MAX timestamp present in the DB
        across both synapse_fluid_dynamics and synapse_edge_phase_hourly_summary.
        """
        try:
            cursor = conn.cursor()
            sql = self.get_query("get_max_collected_at")
            cursor.execute(sql)
            row = cursor.fetchone()
            max_dt = None
            if row and row[0]:
                val = row[0]
                max_dt = self.parse_timestamp(val)

            # Fallback to hourly summary table if synapse_fluid_dynamics is empty
            if max_dt is None:
                try:
                    cursor.execute("SELECT MAX(summary_hour) FROM synapse_edge_phase_hourly_summary;")
                    s_row = cursor.fetchone()
                    if s_row and s_row[0]:
                        max_dt = self.parse_timestamp(s_row[0])
                except Exception:
                    pass

            if max_dt is None:
                max_dt = datetime.now()

            return max_dt - timedelta(seconds=limit_seconds)
        except Exception as e:
            logging.warning(f"[DB_MANAGER] Could not fetch MAX timestamp, fallback to datetime.now(): {e}")
            return datetime.now() - timedelta(seconds=limit_seconds)

    @staticmethod
    def parse_timestamp(val) -> Optional[datetime]:
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
