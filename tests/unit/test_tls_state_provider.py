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

# File: tests/unit/test_tls_state_provider.py
# Author: Gabriel Moraes
# Date: 2026-06-19

import os
import sys
import pytest

# Ensure src is in sys.path so we import 'sds' identically to the backend layers
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sds.tls_state_provider import TlsStateProvider
from sds.tls_map_extractor import TlsMapExtractor

@pytest.mark.unit
def test_get_live_states_for_junction_direct_mapping():
    # Setup test scenario
    tl_id = "J_TEST"
    
    # Manually populate TlsMapExtractor cached topology details
    TlsMapExtractor._tl_phases[tl_id] = {
        0: "GGggrrrr",
        1: "yyyyrrrr",
        2: "rrrrGGgg"
    }
    
    TlsMapExtractor._tl_connections[tl_id] = {
        0: {'edge': 'edge_east', 'dir': 's'},
        1: {'edge': 'edge_east', 'dir': 'l'},
        2: {'edge': 'edge_west', 'dir': 's'},
        3: {'edge': 'edge_west', 'dir': 'l'},
        4: {'edge': 'edge_north', 'dir': 's'},
        5: {'edge': 'edge_north', 'dir': 'l'},
        6: {'edge': 'edge_south', 'dir': 's'},
        7: {'edge': 'edge_south', 'dir': 'l'},
    }
    
    # 1. Test phase index 0 (Green for East/West)
    state = TlsStateProvider.get_live_states_for_junction([], tl_id, 0)
    assert state["display_state"] == "GREEN"
    assert state["lanes_state"]["edge_east (S)"] == "G"
    assert state["lanes_state"]["edge_west (S)"] == "G"
    assert state["lanes_state"]["edge_north (S)"] == "r"
    assert state["lanes_state"]["edge_south (S)"] == "r"
    
    # 2. Test phase index 1 (Yellow for East/West)
    state = TlsStateProvider.get_live_states_for_junction([], tl_id, 1)
    assert state["display_state"] == "YELLOW"
    assert state["lanes_state"]["edge_east (S)"] == "y"
    assert state["lanes_state"]["edge_north (S)"] == "r"
    
    # 3. Test phase index 2 (Green for North/South)
    state = TlsStateProvider.get_live_states_for_junction([], tl_id, 2)
    assert state["display_state"] == "GREEN"
    assert state["lanes_state"]["edge_east (S)"] == "r"
    assert state["lanes_state"]["edge_north (S)"] == "G"

    # Clean up test modifications
    TlsMapExtractor._tl_phases.pop(tl_id, None)
    TlsMapExtractor._tl_connections.pop(tl_id, None)
