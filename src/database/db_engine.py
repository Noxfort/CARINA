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

import os
import json
import sqlite3
import logging
import configparser
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend


class DatabaseEngine:
    """
    Central engine for managing database connections (SQLite or PostgreSQL).
    Responsible for connecting, initializing the schema dynamically from config/schema_queries.json,
    and providing active database connections.
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

    def _load_schema_config(self) -> dict:
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            json_path = os.path.join(base_dir, "config", "schema_queries.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"[DB_ENGINE] Failed to load schema_queries.json: {e}")
        return {}

    def _initialize_db(self):
        """
        Creates the necessary tables, migrations, and indexes in the database dynamically from JSON.
        """
        conn = self.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            schema_config = self._load_schema_config()
            dialect_config = schema_config.get(self.db_type, schema_config.get("sqlite", {}))

            # 1. Create Tables
            for table_sql in dialect_config.get("tables", []):
                cursor.execute(table_sql)
                conn.commit()

            # 2. Migrations
            migrations = dialect_config.get("migrations", [])
            if self.db_type == "postgres":
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'synapse_fluid_dynamics';
                """)
                existing_cols = {row[0] for row in cursor.fetchall()}
                for m in migrations:
                    if isinstance(m, dict) and m.get("column") not in existing_cols:
                        try:
                            cursor.execute(m["sql"])
                            conn.commit()
                        except Exception:
                            pass
            else:
                for migration_sql in migrations:
                    sql_stmt = migration_sql if isinstance(migration_sql, str) else migration_sql.get("sql")
                    try:
                        cursor.execute(sql_stmt)
                        conn.commit()
                    except Exception:
                        pass

            # 3. Create Indexes
            for index_sql in dialect_config.get("indexes", []):
                cursor.execute(index_sql)
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
