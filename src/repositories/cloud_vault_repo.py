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

# File: src/repositories/cloud_vault_repo.py
# Author: Gabriel Moraes
# Date: May 31, 2026

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend

class CloudVaultRepository:
    """
    Repository for managing file synchronization and backup in the cloud (Cloud Vault).
    """
    def __init__(self, engine: 'DatabaseEngine', locale_manager: 'LocaleManagerBackend'):
        self.engine = engine
        self.locale_manager = locale_manager

    def sync_file_to_vault(self, filepath: str, base_dir: str) -> bool:
        """
        Reads a local file and upserts it into the cloud_file_vault if it's <= 50MB.
        Returns True if successful, False otherwise.
        """
        try:
            # Check file size (limit: 50MB)
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > 50:
                logging.debug(f"[CLOUD_VAULT] Skipped {filepath} - Exceeds 50MB limit ({file_size_mb:.1f}MB)")
                return False

            with open(filepath, 'rb') as f:
                content = f.read()

            rel_path = os.path.relpath(filepath, base_dir)
            filename = os.path.basename(filepath)
            now = datetime.now()

            conn = self.engine.get_connection()
            if not conn:
                return False
            try:
                cursor = conn.cursor()
                if self.engine.db_type == "postgres":
                    import psycopg2
                    cursor.execute("""
                        INSERT INTO cloud_file_vault (filename, relative_path, file_content, last_updated)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (relative_path) 
                        DO UPDATE SET file_content = EXCLUDED.file_content, last_updated = EXCLUDED.last_updated;
                    """, (filename, rel_path, psycopg2.Binary(content), now))
                else:
                    cursor.execute("""
                        INSERT INTO cloud_file_vault (filename, relative_path, file_content, last_updated)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(relative_path) 
                        DO UPDATE SET file_content=excluded.file_content, last_updated=excluded.last_updated;
                    """, (filename, rel_path, content, now))
                
                conn.commit()
                return True
            except Exception as e:
                logging.error(f"[CLOUD_VAULT] Failed to insert file {filename} in vault: {e}")
                return False
            finally:
                if conn:
                    conn.close()
        except Exception as general_err:
            logging.error(f"[CLOUD_VAULT] Vault File Read Error for {filepath}: {general_err}")
            return False

    def sync_all_files_to_vault(self, base_dir: str):
        """
        Recursively scans the base_dir and attempts to sync all files to the cloud_file_vault. 
        Skips .db files to prevent nesting conflicts.
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
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 50*1024*1024:
                        skipped += 1
                    else:
                        errors += 1
                        
        if synced > 0 or errors > 0:
            logging.info(f"[CLOUD_VAULT] Sync completed. {synced} synced, {skipped} skipped (>50MB), {errors} errors.")
