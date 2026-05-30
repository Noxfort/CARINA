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

# File: src/utils/map_generator.py (MODIFIED FOR FULL TRANSLATION)
# Author: Gabriel Moraes
# Date: October 4, 2025

import subprocess
import os
import logging
import shutil
import sys
from typing import TYPE_CHECKING

# --- CHANGE 1: Add imports ---
if TYPE_CHECKING:
    from .locale_manager_backend import LocaleManagerBackend

# --- CHANGE 2: Modify function signature ---
def generate_map_data_files(net_file_path: str, output_dir: str, lm: 'LocaleManagerBackend') -> str | None:
    """
    Executes netconvert to generate the plain XML data files.
    """
    if not os.path.exists(net_file_path):
        # --- CHANGE 3 ---
        logging.error(lm.get_string("map_generator.run.net_file_not_found", path=net_file_path))
        return None

    netconvert_exe = "netconvert.exe" if sys.platform == "win32" else "netconvert"
    sumo_home = os.environ.get("SUMO_HOME")
    
    netconvert_path = shutil.which(netconvert_exe)
    if not netconvert_path and sumo_home:
        path_try = os.path.join(sumo_home, "bin", netconvert_exe)
        if os.path.exists(path_try):
            netconvert_path = path_try

    if not netconvert_path:
        # --- CHANGE 4 ---
        logging.critical(lm.get_string("map_generator.run.netconvert_not_found"))
        return None

    map_output_dir = os.path.join(output_dir, "maps")
    os.makedirs(map_output_dir, exist_ok=True)
    
    scenario_name = os.path.basename(output_dir)
    output_prefix_path = os.path.join(map_output_dir, f"{scenario_name}_map")
    
    command = [
        netconvert_path,
        "--sumo-net-file", net_file_path,
        "--plain-output-prefix", output_prefix_path,
        "--junctions.join",
    ]

    # --- CHANGE 5 ---
    logging.info(lm.get_string("map_generator.run.generating_files"))
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        
        if os.path.exists(output_prefix_path + ".nod.xml"):
            # --- CHANGE 6 ---
            logging.info(lm.get_string("map_generator.run.success", prefix=output_prefix_path))
            return output_prefix_path
        else:
            # --- CHANGE 7 ---
            logging.error(lm.get_string("map_generator.run.files_not_found_after_run"))
            return None

    except subprocess.CalledProcessError as e:
        # --- CHANGE 8 ---
        logging.error(lm.get_string("map_generator.run.netconvert_error"))
        # --- CHANGE 9 ---
        logging.error(lm.get_string("map_generator.run.stderr_output", stderr=e.stderr))
        return None
    except Exception as e:
        # --- CHANGE 10 ---
        logging.error(lm.get_string("map_generator.run.unexpected_error", error=e), exc_info=True)
        return None