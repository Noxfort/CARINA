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

# File: tests/unit/test_mfd_processor.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import pytest
from unittest.mock import MagicMock, patch
from mfd.mfd_processor import MFDProcessor

def test_mfd_processor_no_mfd():
    processor = MFDProcessor(mfd=None, state_extractor=None)
    res = processor.process_step(edges_data={}, sim_time=1.0, agents_keys=[], step_counter=1, episode_steps=100)
    assert res is None

def test_mfd_processor_no_edges():
    mfd = MagicMock()
    processor = MFDProcessor(mfd=mfd, state_extractor=None)
    res = processor.process_step(edges_data={}, sim_time=1.0, agents_keys=[], step_counter=1, episode_steps=100)
    assert res is None

def test_mfd_processor_compute_step():
    mfd = MagicMock()
    mfd_snapshot = MagicMock()
    mfd_snapshot.to_dict.return_value = {"efficiency": 0.9}
    mfd.compute_step.return_value = mfd_snapshot
    mfd._edge_lengths = {"edge_1": 150.0}
    
    state_extractor = MagicMock()
    state_extractor.tl_incoming_edges = {"tl_1": ["edge_1"]}
    
    processor = MFDProcessor(mfd=mfd, state_extractor=state_extractor)
    
    edges_data = {
        "edge_1": {
            "density": 0.05,
            "mean_speed": 10.0,
            "occupancy": 0.1,
            "queue_length": 5
        }
    }
    
    res = processor.process_step(
        edges_data=edges_data,
        sim_time=1.0,
        agents_keys=["tl_1"],
        step_counter=1,
        episode_steps=100
    )
    
    assert res == {"efficiency": 0.9}
    mfd.compute_step.assert_called_once()
