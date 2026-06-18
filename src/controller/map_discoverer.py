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

# File: src/controller/map_discoverer.py
# Author: Gabriel Moraes
# Date: 2026-06-16

"""
Description:
Responsible for discovering intersection IDs and stage information from SUMO network map files.
Helps satisfy Single Responsibility Principle (SRP) for Connection Manager.
"""

import glob
import gzip
import logging
import os
import xml.etree.ElementTree as ET
from typing import List

from src.utils.paths import get_base_output_dir

logger = logging.getLogger(__name__)

class MapTopologyDiscoverer:
    """
    Helper class responsible for parsing network map files and extracting topology information.
    """

    @staticmethod
    def get_map_file() -> str:
        """
        Locates the SUMO network map file (.net.xml or .net.xml.gz).
        """
        maps_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session", "maps")
        search_gz = os.path.join(maps_dir, "*.net.xml.gz")
        search_xml = os.path.join(maps_dir, "*.net.xml")
        files = glob.glob(search_gz) + glob.glob(search_xml)
        return files[0] if files else ""

    @classmethod
    def discover_intersections(cls) -> List[str]:
        """
        Scans the map file and extracts all valid traffic light intersection IDs.
        """
        target_file = cls.get_map_file()
        if not target_file:
            logger.warning("No network map found. Intersections list will be empty.")
            return []

        tl_ids = set()
        try:
            opener = gzip.open if target_file.endswith('.gz') else open
            with opener(target_file, 'rt', encoding='utf-8') as f:
                tree = ET.parse(f)
                
            root = tree.getroot()
            for tl in root.findall('tlLogic'):
                tl_id = tl.get('id')
                if tl_id:
                    tl_ids.add(tl_id)
                    
            logger.info(f"Discovered {len(tl_ids)} intersections from {os.path.basename(target_file)}.")
            return sorted(list(tl_ids))
        except Exception as e:
            logger.error(f"Failed to parse network file {target_file} for intersections: {e}")
            return []

    @classmethod
    def get_green_stages(cls, intersection_id: str) -> List[int]:
        """
        Parses the map file to extract all stage indices for a specific intersection (no filtering).
        """
        target_file = cls.get_map_file()
        if not target_file:
            return []

        try:
            opener = gzip.open if target_file.endswith('.gz') else open
            with opener(target_file, 'rt', encoding='utf-8') as f:
                tree = ET.parse(f)
                
            root = tree.getroot()
            for tl_logic in root.findall('tlLogic'):
                if tl_logic.get('id') == intersection_id:
                    return list(range(len(tl_logic.findall('phase'))))
        except Exception as e:
            logger.error(f"Failed to parse stages for intersection {intersection_id}: {e}")
        return []
