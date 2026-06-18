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
