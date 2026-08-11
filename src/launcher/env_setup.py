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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/launcher/env_setup.py
# Author: Gabriel Moraes
# Date: August 6, 2026

import sys
import os

def setup_environment():
    """
    Configures sys.path directories and required environment variables for CARINA.
    Returns a tuple of (project_root, bundle_root, IS_FROZEN).
    """
    IS_FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    if IS_FROZEN:
        project_root = os.path.dirname(sys.executable)
        bundle_root = sys._MEIPASS
    else:
        # When executed from src/launcher/env_setup.py, project_root is 2 levels up
        launcher_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(launcher_dir, "..", ".."))
        bundle_root = project_root

    # Add critical paths to sys.path (src, proto, ui)
    paths_to_add = [
        os.path.join(bundle_root, 'src'),
        os.path.join(bundle_root, 'proto'),
        os.path.join(bundle_root, 'ui')
    ]

    for p in paths_to_add:
        if p not in sys.path:
            sys.path.insert(0, p)

    # Environment settings & thread limiting
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    if sys.platform == 'win32':
        try:
            os.system('chcp 65001 > nul')
        except Exception:
            pass

    return project_root, bundle_root, IS_FROZEN
