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

# File: tests/debug_imports.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import sys
import os
import time
import importlib

print("[SANITY] Preparing to trace imports...")

# Fake the UI so it doesn't even try to load PyQt or PySide
sys.modules['PyQt5'] = type('Mock', (object,), {})()
sys.modules['PyQt6'] = type('Mock', (object,), {})()
sys.modules['PySide6'] = type('Mock', (object,), {})()

# Fake heavy libraries
sys.modules['torch'] = type('MockTorch', (object,), {'cuda': type('MockCuda', (object,), {'is_available': lambda: False}), 'Tensor': type('MockTensor', (object,), {}), 'nn': type('MockNN', (object,), {'Module': object})})()
sys.modules['torchvision'] = type('Mock', (object,), {})()
sys.modules['psutil'] = type('Mock', (object,), {})()

print("[SANITY] Fakes injected. Now trying to import CentralController...")

try:
    # Add root to path as done in carina.py
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)
    sys.path.insert(0, os.path.join(project_root, 'src'))

    from src.central_controller import CentralController
    print("[SANITY] SUCCESSFULLY IMPORTED CENTRAL CONTROLLER!")
except Exception as e:
    print(f"[SANITY] Import failed with exception: {e}")
    import traceback
    traceback.print_exc()

print("[SANITY] Done.")
