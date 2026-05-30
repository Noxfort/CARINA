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

# File: src/hooks/pyi_runtime_hooks.py
# Author: Gabriel Moraes
# Date: October 25, 2025 # <-- DATE UPDATED

import sys
import os

print(f"[Runtime Hook] Initial sys.path: {sys.path}")

# sys._MEIPASS points to the _internal folder (bundle root)
bundle_dir = getattr(sys, '_MEIPASS', None)

if bundle_dir:
    # Constructs the absolute path to 'src' and 'proto' within the bundle
    src_path = os.path.abspath(os.path.join(bundle_dir, 'src'))
    proto_path = os.path.abspath(os.path.join(bundle_dir, 'proto'))

    for path_name, path_val in [('src', src_path), ('proto', proto_path)]:
        if os.path.isdir(path_val):
            if path_val not in sys.path:
                sys.path.insert(1, path_val)
                print(f"[Runtime Hook] Added bundle {path_name} path to sys.path: {path_val}")
            else:
                print(f"[Runtime Hook] Bundle {path_name} path already in sys.path: {path_val}")
        else:
            print(f"[Runtime Hook] Bundle {path_name} path NOT found: {path_val}")

    # Ensures the bundle root is also in the path (usually added automatically, but confirm)
    abs_bundle_dir = os.path.abspath(bundle_dir)
    if abs_bundle_dir not in sys.path:
        sys.path.append(abs_bundle_dir) # Add at the end
        print(f"[Runtime Hook] Added bundle root path to sys.path: {abs_bundle_dir}")

else:
     print("[Runtime Hook] Not running in frozen mode (no _MEIPASS). Hook skipping modification.")

print(f"[Runtime Hook] sys.path after hook: {sys.path}")