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

# File: src/repositories/simulation_repo.py
# Author: Gabriel Moraes
# Date: May 31, 2026

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend

class SimulationRepository:
    """
    Repository for managing simulation runs, episodes, and analysis reports.
    """
    def __init__(self, engine: 'DatabaseEngine', locale_manager: 'LocaleManagerBackend'):
        self.engine = engine
        self.locale_manager = locale_manager

    def create_simulation_run(self, scenario_name: str) -> Optional[int]:
        """
        Registers a new execution using parameterized queries based on the dialect.
        """
        lm = self.locale_manager
        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            start_time = datetime.now()
            
            if self.engine.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO simulation_runs (start_time, scenario_name) VALUES (%s, %s) RETURNING run_id;",
                    (start_time, scenario_name)
                )
                run_id = cursor.fetchone()[0]
            else:
                cursor.execute(
                    "INSERT INTO simulation_runs (start_time, scenario_name) VALUES (?, ?);",
                    (start_time, scenario_name)
                )
                run_id = cursor.lastrowid
                
            conn.commit()
            logging.info(lm.get_string("db_manager.create_run.success", scenario=scenario_name))
            return run_id
        except Exception as e:
            logging.error(lm.get_string("db_manager.create_run.error", error=e))
            return None
        finally:
            if conn:
                conn.close()

    def log_episode(self, run_id: int, episode_number: int, total_reward: float):
        """Saves the metrics for a completed episode to the database."""
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            end_time = datetime.now()
            
            if self.engine.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO episodes (run_id, episode_number, total_reward, end_time) VALUES (%s, %s, %s, %s);",
                    (run_id, episode_number, total_reward, end_time)
                )
            else:
                cursor.execute(
                    "INSERT INTO episodes (run_id, episode_number, total_reward, end_time) VALUES (?, ?, ?, ?);",
                    (run_id, episode_number, total_reward, end_time)
                )
            conn.commit()
        except Exception as e:
            logging.error(self.locale_manager.get_string("db_manager.log_episode.error", episode=episode_number, error=e))
        finally:
            if conn:
                conn.close()
                
    def log_analysis_report(self, run_id: int, summary: str, report_content: str):
        """Saves an infrastructure analysis report."""
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            timestamp = datetime.now()
            
            if self.engine.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO analysis_reports (run_id, timestamp, summary, report_content) VALUES (%s, %s, %s, %s);",
                    (run_id, timestamp, summary, report_content)
                )
            else:
                cursor.execute(
                    "INSERT INTO analysis_reports (run_id, timestamp, summary, report_content) VALUES (?, ?, ?, ?);",
                    (run_id, timestamp, summary, report_content)
                )
            conn.commit()
        except Exception as e:
            logging.error(self.locale_manager.get_string("db_manager.log_report.error", error=e))
        finally:
            if conn:
                conn.close()
