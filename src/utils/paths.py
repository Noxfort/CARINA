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

# File: src/utils/paths.py (NEW FILE)
# Author: Gabriel Moraes
# Date: October 22, 2025

"""
Defines utility functions to handle file paths,
ensuring compatibility with PyInstaller (--onefile).
"""

import sys
import os
import subprocess

def resource_path(relative_path: str) -> str:
    """
    Returns the absolute path to a resource (data file),
    working both in development mode and in the executable
    created by PyInstaller.

    Args:
        relative_path (str): The relative path to the resource from the
                             project root (or bundle).

    Returns:
        str: The absolute path to the resource.
    """
    try:
        # PyInstaller creates a temporary folder and stores the path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If _MEIPASS does not exist, we are in development mode.
        # We use abspath(".") to get the root of the project where the script/command is executed.
        # We set it to go up two levels from src/utils to get to the root.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    return os.path.join(base_path, relative_path)

def get_base_output_dir() -> str:
    """
    Returns the base directory (OS Documents/Carina) where output files (logs, results) should be written.
    Resolves the OS Documents folder dynamically (Linux).

    Returns:
        str: The absolute path to the output base directory.
    """
    documents_dir = None
    try:
        # Try to get the official XDG Documents folder on Linux
        output = subprocess.check_output(['xdg-user-dir', 'DOCUMENTS'], stderr=subprocess.DEVNULL)
        documents_dir = output.decode('utf-8').strip()
    except Exception:
        pass
    
    if not documents_dir or not os.path.isdir(documents_dir):
        # Fallback 1: ~/Documents
        fallback_en = os.path.expanduser("~/Documents")
        if os.path.isdir(fallback_en):
            documents_dir = fallback_en
        else:
            # Fallback 2: ~/Documentos
            fallback_pt = os.path.expanduser("~/Documentos")
            if os.path.isdir(fallback_pt):
                documents_dir = fallback_pt
            else:
                # Last generic fallback
                documents_dir = os.path.expanduser("~")

    # The Carina subfolder will be in /Documents/Carina
    carina_dir = os.path.join(documents_dir, "Carina")
    os.makedirs(carina_dir, exist_ok=True)
    return carina_dir

def get_user_config_dir() -> str:
    """
    Returns the standard directory for user configuration and data,
    which is persistent and hidden, following OS standards (e.g. XDG on Linux).
    """
    import sys
    if sys.platform.startswith('win'):
        base_dir = os.environ.get('APPDATA') or os.path.expanduser('~/AppData/Roaming')
    elif sys.platform.startswith('darwin'):
        base_dir = os.path.expanduser('~/Library/Application Support')
    else:
        # Linux / Unix XDG standard
        base_dir = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    
    config_dir = os.path.join(base_dir, 'carina')
    os.makedirs(config_dir, exist_ok=True)
    return config_dir