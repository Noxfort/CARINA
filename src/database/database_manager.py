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

# File: src/database/database_manager.py (MODIFIED FOR TRANSLATION)
# Author: Gabriel Moraes
# Date: October 1, 2025

import sqlite3
import logging
import os
from datetime import datetime
import sys
import configparser
from typing import TYPE_CHECKING, Any

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class DatabaseManager:
    """
    Gerencia todas as interações com o banco de dados (SQLite local ou PostgreSQL Remoto).
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend', db_name: str = "carina_data.db"):
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
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
        logging.info(f"[DB_MANAGER] Gerenciador Base Inicializado. Motor: {self.db_type}")

    def _get_connection(self) -> Any:
        """Retorna uma conexão (psycopg2 ou sqlite3) dependendo da config."""
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

    def _initialize_db(self):
        """
        Creates the necessary tables in the database with a specific SQL dialect.
        """
        conn = self._get_connection()
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
            conn.rollback()
            logging.error(f"[DB_MANAGER] Error during _initialize_db: {e}")
            try:
                logging.error(self.locale_manager.get_string("db_manager.init.db_error", error=e))
            except Exception:
                pass
        finally:
            conn.close()

    def create_simulation_run(self, scenario_name: str) -> int | None:
        """
        Registra uma nova execução usando queries parametrizadas pelo dialeto.
        """
        lm = self.locale_manager
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            start_time = datetime.now()
            
            if self.db_type == "postgres":
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
            conn.close()

    def log_episode(self, run_id: int, episode_number: int, total_reward: float):
        """Saves the metrics for a completed episode to the database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            end_time = datetime.now()
            
            if self.db_type == "postgres":
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
            conn.close()
            
    def log_analysis_report(self, run_id: int, summary: str, report_content: str):
        """Saves an infrastructure analysis report."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            timestamp = datetime.now()
            
            if self.db_type == "postgres":
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
            conn.close()

    # =========================================================================
    # SYNAPSE FLUID DYNAMICS — Used by the Optimization Analysis Engine
    # =========================================================================

    def insert_synapse_fluid_dynamics(self, samples: list):
        """
        Batch-inserts a list of fluid dynamics sample dicts into the synapse_fluid_dynamics table.
        Each dict must contain: edge_id, density, mean_speed, queue_length, occupancy,
        and optionally: edge_length, num_lanes, speed_limit, collected_at.
        """
        if not samples:
            return
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            ph = "%s" if self.db_type == "postgres" else "?"
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
            conn.close()

    def query_fluid_dynamics_history(self) -> list:
        """
        Retrieves ALL fluid dynamics samples currently stored in the database.
        Returns a list of dicts with all sample columns.
        """
        conn = self._get_connection()
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
            conn.close()

    def purge_old_fluid_dynamics(self, keep_minutes: int = 1440):
        """
        Deletes fluid dynamics samples older than `keep_minutes` minutes.
        Default: 24 hours.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if self.db_type == "postgres":
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
            conn.close()

    def get_fluid_dynamics_count(self) -> int:
        """Returns the total number of fluid dynamics samples in the database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM synapse_fluid_dynamics;")
            return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"[DB_MANAGER] Error counting fluid dynamics samples: {e}")
            return 0
        finally:
            conn.close()

    # =========================================================================
    # CLOUD FILE VAULT — File Backup System
    # =========================================================================

    def sync_file_to_vault(self, filepath: str, base_dir: str):
        """
        Reads a local file and upserts it into the cloud_file_vault if it's <= 50MB.
        Returns True if successful, False otherwise.
        """
        try:
            # Check file size (limit: 50MB)
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > 50:
                logging.debug(f"[DB_MANAGER] Skipped {filepath} - Exceeds 50MB limit ({file_size_mb:.1f}MB)")
                return False

            with open(filepath, 'rb') as f:
                content = f.read()

            rel_path = os.path.relpath(filepath, base_dir)
            filename = os.path.basename(filepath)
            now = datetime.now()

            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                if self.db_type == "postgres":
                    import psycopg2
                    # Upsert (ON CONFLICT... DO UPDATE) requires PostgreSQL 9.5+ 
                    # Note: We must have a unique constraint on relative_path, which we do.
                    cursor.execute("""
                        INSERT INTO cloud_file_vault (filename, relative_path, file_content, last_updated)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (relative_path) 
                        DO UPDATE SET file_content = EXCLUDED.file_content, last_updated = EXCLUDED.last_updated;
                    """, (filename, rel_path, psycopg2.Binary(content), now))
                else:
                    # SQLite upsert
                    cursor.execute("""
                        INSERT INTO cloud_file_vault (filename, relative_path, file_content, last_updated)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(relative_path) 
                        DO UPDATE SET file_content=excluded.file_content, last_updated=excluded.last_updated;
                    """, (filename, rel_path, content, now))
                
                conn.commit()
                return True
            except Exception as e:
                logging.error(f"[DB_MANAGER] Failed to insert file {filename} in vault: {e}")
                return False
            finally:
                conn.close()
        except Exception as general_err:
            logging.error(f"[DB_MANAGER] Vault File Read Error for {filepath}: {general_err}")
            return False

    def sync_all_files_to_vault(self, base_dir: str):
        """
        Recursively scans the base_dir (usually Documentos/Carina) and attempts
        to sync all files to the cloud_file_vault. Skips .db files to prevent nesting conflicts.
        """
        synced = 0
        skipped = 0
        errors = 0

        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.db') or file.endswith('.db-journal'):
                    continue # Do not backup the database itself
                
                filepath = os.path.join(root, file)
                success = self.sync_file_to_vault(filepath, base_dir)
                if success:
                    synced += 1
                else:
                    # Can be skipped or error
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 50*1024*1024:
                        skipped += 1
                    else:
                        errors += 1
                        
        if synced > 0 or errors > 0:
            logging.info(f"[CLOUD_VAULT] Sync completed. {synced} synced, {skipped} skipped (>50MB), {errors} errors.")