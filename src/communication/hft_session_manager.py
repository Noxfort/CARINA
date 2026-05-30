# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
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
#
# File: src/communication/hft_session_manager.py
# Author: Gabriel Moraes
# Date: 2026-04-17

import os
import logging

class HFTSessionManager:
    """
    Handles local file system I/O for saving map and schedule scenarios.
    Ensures correct directory structures are used outside of the networking code.
    """

    @staticmethod
    def save_map_and_schedule(map_file_content: bytes, map_file_name: str, peak_schedule_json: str) -> tuple[bool, str, str | None, str | None]:
        """
        Saves the topology map and optional peak schedule.
        Returns (success, message, map_path, maps_dir)
        """
        try:
            session_name = "hft_live_session"
            from src.utils.paths import get_base_output_dir
            session_dir = os.path.join(get_base_output_dir(), "results", session_name)
            maps_dir = os.path.join(session_dir, "maps")
            
            os.makedirs(maps_dir, exist_ok=True)
            
            if peak_schedule_json:
                peak_schedule_path = os.path.join(session_dir, "peak_schedule.json")
                with open(peak_schedule_path, "w", encoding="utf-8") as f:
                    f.write(peak_schedule_json)
                logging.info(f"[HFT] Peak Schedule JSON saved successfully at: {peak_schedule_path}")
            
            original_filename = map_file_name
            if not original_filename:
                original_filename = f"{session_name}.net.xml"
                logging.warning(f"[HFT] map_file_name not provided by Synapse. Falling back to {original_filename}")
            
            map_path = os.path.join(maps_dir, original_filename)
            
            with open(map_path, "wb") as f:
                f.write(map_file_content)
            
            logging.info(f"[HFT] Map saved successfully at: {map_path}")
            return True, "Map processed", map_path, maps_dir
            
        except Exception as e:
            logging.error(f"[HFT] Error saving/processing map: {e}", exc_info=True)
            return False, str(e), None, None
