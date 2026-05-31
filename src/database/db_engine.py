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

# File: src/database/db_engine.py
# Author: Gabriel Moraes
# Date: May 31, 2026

import sqlite3
import logging
import os
import configparser
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend

class DatabaseEngine:
    """
    Central engine for managing database connections (SQLite or PostgreSQL).
    Responsible only for connecting, initializing the schema, and providing the active connection.
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend', db_name: str = "carina_data.db"):
        self.locale_manager = locale_manager
        self._fatal_db_error = False
        
        project_root_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        # Parse settings directly
        self.config = configparser.ConfigParser()
        settings_path = os.path.join(project_root_local, "config", "settings.ini")
        if os.path.exists(settings_path):
            self.config.read(settings_path)
            
        self.db_type = self.config.get("DATABASE", "db_type", fallback="sqlite")
        self.db_host = self.config.get("DATABASE", "db_host", fallback="localhost")
        self.db_port = self.config.get("DATABASE", "db_port", fallback="5432")
        self.db_user = self.config.get("DATABASE", "db_user", fallback="postgres")
        self.db_password = self.config.get("DATABASE", "db_password", fallback="")
        self.db_name_pg = self.config.get("DATABASE", "db_name", fallback="carina_data")
        self.db_schema = self.config.get("DATABASE", "db_schema", fallback="schema_carina")
        
        # SQLite local path
        from src.utils.paths import get_base_output_dir
        db_dir = os.path.join(get_base_output_dir(), "results", "database")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, db_name)
        
        self._initialize_db()
        logging.info(f"[DB_ENGINE] Central Engine Initialized. DB: {self.db_type}")

    def get_connection(self) -> Any:
        """Returns a connection (psycopg2 or sqlite3) depending on the configuration."""
        if getattr(self, '_fatal_db_error', False):
            return None
            
        try:
            if self.db_type == "postgres":
                import psycopg2
                return psycopg2.connect(
                    host=self.db_host,
                    port=self.db_port,
                    user=self.db_user,
                    password=self.db_password,
                    dbname=self.db_name_pg,
                    options=f"-c search_path={self.db_schema},public"
                )
            else:
                return sqlite3.connect(self.db_path)
        except Exception as e:
            error_msg = str(e).lower()
            if "password authentication failed" in error_msg or "fatal:" in error_msg or "fe_sendauth" in error_msg:
                self._fatal_db_error = True
                logging.critical(f"[DB_ENGINE] CRITICAL: Fatal PostgreSQL connection error for user '{self.db_user}' / db '{self.db_name_pg}'. Connection disabled to prevent spam. Details: {e}")
                print(f"\n[CARINA FATAL ERROR] Invalid database credentials or database does not exist.")
                print(f"User: '{self.db_user}', DB: '{self.db_name_pg}'. Please update your settings and restart the application.\n")
            else:
                logging.error(f"[DB_ENGINE] Failed to connect to the database ({self.db_type}): {e}")
            return None

    def _initialize_db(self):
        """
        Creates the necessary tables in the database with a specific SQL dialect.
        """
        conn = self.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            
            if self.db_type == "postgres":
                # Ensure each isolated block can commit successfully
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_runs (
                    run_id SERIAL PRIMARY KEY,
                    start_time TIMESTAMP NOT NULL,
                    scenario_name TEXT
                );
                """)
                conn.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id SERIAL PRIMARY KEY,
                    run_id INTEGER NOT NULL REFERENCES simulation_runs(run_id),
                    episode_number INTEGER NOT NULL,
                    total_reward REAL,
                    end_time TIMESTAMP
                );
                """)
                conn.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    report_id SERIAL PRIMARY KEY,
                    run_id INTEGER NOT NULL REFERENCES simulation_runs(run_id),
                    timestamp TIMESTAMP NOT NULL,
                    summary TEXT,
                    report_content TEXT
                );
                """)
                conn.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS synapse_fluid_dynamics (
                    id SERIAL PRIMARY KEY,
                    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    edge_id TEXT NOT NULL,
                    density REAL NOT NULL,
                    mean_speed REAL NOT NULL,
                    queue_length INTEGER NOT NULL,
                    occupancy REAL NOT NULL,
                    edge_length REAL,
                    num_lanes INTEGER,
                    speed_limit REAL
                );
                """)
                conn.commit()

                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sfd_collected_at ON synapse_fluid_dynamics(collected_at);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sfd_edge_id ON synapse_fluid_dynamics(edge_id);")
                conn.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_file_vault (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    relative_path TEXT NOT NULL UNIQUE,
                    file_content BYTEA,
                    last_updated TIMESTAMP NOT NULL DEFAULT NOW()
                );
                """)
                conn.commit()

            else:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    scenario_name TEXT
                );
                """)
                conn.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    episode_number INTEGER NOT NULL,
                    total_reward REAL,
                    end_time TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
                );
                """)
                conn.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    summary TEXT,
                    report_content TEXT,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
                );
                """)
                conn.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS synapse_fluid_dynamics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    edge_id TEXT NOT NULL,
                    density REAL NOT NULL,
                    mean_speed REAL NOT NULL,
                    queue_length INTEGER NOT NULL,
                    occupancy REAL NOT NULL,
                    edge_length REAL,
                    num_lanes INTEGER,
                    speed_limit REAL
                );
                """)
                conn.commit()

                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sfd_collected_at ON synapse_fluid_dynamics(collected_at);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sfd_edge_id ON synapse_fluid_dynamics(edge_id);")
                conn.commit()

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS cloud_file_vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    relative_path TEXT NOT NULL UNIQUE,
                    file_content BLOB,
                    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """)
                conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"[DB_ENGINE] Error during _initialize_db: {e}")
            try:
                logging.error(self.locale_manager.get_string("db_manager.init.db_error", error=e))
            except Exception:
                pass
        finally:
            if conn:
                conn.close()
