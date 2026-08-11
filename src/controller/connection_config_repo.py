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

# File: src/controller/connection_config_repo.py
# Author: Gabriel Moraes
# Date: 2026-06-16

"""
Description:
Repository class responsible for CSV import/export of connection configurations.
Helps satisfy Single Responsibility Principle (SRP) for Connection Manager.
"""

import csv
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class ConnectionConfigRepository:
    """
    Manages loading, saving, importing, and exporting of intersection connection configurations.
    """

    @staticmethod
    def export_csv_template(filepath: str, saved_ips: Dict[str, str], known_intersections: List[str]) -> bool:
        """
        Generates a CSV file containing all known intersections and their configured IPs.
        """
        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Intersection ID", "IP Address"])
                for tl_id in known_intersections:
                    ip = saved_ips.get(tl_id, "")
                    writer.writerow([tl_id, ip])
            logger.info(f"Hardware template exported successfully to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export hardware template: {e}")
            return False

    @staticmethod
    def import_csv_config(filepath: str) -> Dict[str, str]:
        """
        Reads a CSV file containing intersection connection configurations.
        Returns a dictionary mapping intersection IDs to IP addresses.
        """
        configs = {}
        try:
            with open(filepath, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tl_id = row.get("Intersection ID", "").strip()
                    ip = row.get("IP Address", "").strip()
                    if tl_id and ip:
                        configs[tl_id] = ip
            logger.info(f"Imported {len(configs)} configurations from CSV: {filepath}")
        except Exception as e:
            logger.error(f"Failed to import CSV configuration: {e}")
        return configs

    @staticmethod
    def save_connection_db(intersection_id: str, ip_address: str, locale_manager=None) -> bool:
        """
        Saves or updates an intersection IP connection config in PostgreSQL/SQLite database.
        """
        try:
            from src.database.db_engine import DatabaseEngine
            engine = DatabaseEngine(locale_manager=locale_manager)
            conn = engine.get_connection()
            if not conn:
                return False
            cursor = conn.cursor()
            if engine.db_type == "postgres":
                cursor.execute("""
                    INSERT INTO hardware_controller_connections (intersection_id, ip_address, auto_connect, last_connected)
                    VALUES (%s, %s, TRUE, NOW())
                    ON CONFLICT (intersection_id) 
                    DO UPDATE SET ip_address = EXCLUDED.ip_address, auto_connect = TRUE, last_connected = NOW();
                """, (str(intersection_id), str(ip_address)))
            else:
                cursor.execute("""
                    INSERT INTO hardware_controller_connections (intersection_id, ip_address, auto_connect, last_connected)
                    VALUES (?, ?, TRUE, CURRENT_TIMESTAMP)
                    ON CONFLICT(intersection_id) 
                    DO UPDATE SET ip_address = excluded.ip_address, auto_connect = TRUE, last_connected = CURRENT_TIMESTAMP;
                """, (str(intersection_id), str(ip_address)))
            conn.commit()
            conn.close()
            logger.info(f"[DB Persistence] Saved hardware connection for '{intersection_id}' at {ip_address}")
            return True
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to save hardware connection to database: {e}")
            return False

    @staticmethod
    def remove_connection_db(intersection_id: str, locale_manager=None) -> bool:
        """
        Deletes the intersection IP connection record completely from PostgreSQL/SQLite database.
        Deletes both the raw ID and any 'tl_' prefixed variant to ensure complete cleanup.
        """
        try:
            from src.database.db_engine import DatabaseEngine
            engine = DatabaseEngine(locale_manager=locale_manager)
            conn = engine.get_connection()
            if not conn:
                return False
            cursor = conn.cursor()
            
            clean_id = str(intersection_id).strip()
            alt_id = clean_id.replace("tl_", "") if clean_id.startswith("tl_") else f"tl_{clean_id}"
            
            if engine.db_type == "postgres":
                cursor.execute(
                    "DELETE FROM hardware_controller_connections WHERE intersection_id = %s OR intersection_id = %s;",
                    (clean_id, alt_id)
                )
            else:
                cursor.execute(
                    "DELETE FROM hardware_controller_connections WHERE intersection_id = ? OR intersection_id = ?;",
                    (clean_id, alt_id)
                )
            conn.commit()
            conn.close()
            logger.info(f"[DB Persistence] Deleted connection record for '{clean_id}' and '{alt_id}' from database.")
            return True
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to delete hardware connection from database: {e}")
            return False

    @staticmethod
    def load_all_connections_db(locale_manager=None) -> Dict[str, str]:
        """
        Loads all saved auto-connect hardware connections from PostgreSQL/SQLite database.
        """
        configs = {}
        try:
            from src.database.db_engine import DatabaseEngine
            engine = DatabaseEngine(locale_manager=locale_manager)
            conn = engine.get_connection()
            if not conn:
                return configs
            cursor = conn.cursor()
            cursor.execute("SELECT intersection_id, ip_address FROM hardware_controller_connections WHERE auto_connect = TRUE;")
            rows = cursor.fetchall()
            for row in rows:
                configs[str(row[0])] = str(row[1])
            conn.close()
            logger.info(f"[DB Persistence] Loaded {len(configs)} saved hardware connection configs from database.")
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to load hardware connections from database: {e}")
        return configs

    @staticmethod
    def clear_all_connections_db(locale_manager=None) -> bool:
        """
        Deletes all hardware connection entries completely from PostgreSQL/SQLite database.
        """
        try:
            from src.database.db_engine import DatabaseEngine
            engine = DatabaseEngine(locale_manager=locale_manager)
            conn = engine.get_connection()
            if not conn:
                return False
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hardware_controller_connections;")
            conn.commit()
            conn.close()
            logger.info("[DB Persistence] Cleared (deleted) all hardware connection records from database.")
            return True
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to clear hardware connections in database: {e}")
            return False
