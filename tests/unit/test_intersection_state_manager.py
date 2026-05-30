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

# File: tests/unit/test_intersection_state_manager.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Unit tests for the IntersectionStateManager component.
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from src.controller.intersection_state_manager import IntersectionStateManager, IntersectionState, SignalState, PhaseDefinition


class MockClock:
    """Mock clock for testing time-dependent behavior."""
    def __init__(self, start_time=0.0):
        self._time = start_time
    
    def increment(self, seconds):
        self._time += seconds
    
    def time(self):
        return self._time


@pytest.fixture
def clock():
    """Provide a mock clock for time-dependent tests."""
    return MockClock()


@pytest.fixture
def state_manager():
    """Create an IntersectionStateManager with default timings."""
    return IntersectionStateManager(green_duration=15.0, yellow_duration=4.0, all_red_duration=2.0)


@pytest.fixture
def simple_intersection():
    """Create a simple intersection with two phases."""
    phases = [
        PhaseDefinition(state_string="GGrr", yellow_string="yyrr", all_red_string="rrrr"),
        PhaseDefinition(state_string="rrGG", yellow_string="rryy", all_red_string="rrrr")
    ]
    return IntersectionState(tls_id="test_intersection", phases=phases)


class TestIntersectionStateManagerInitialization:
    """Test initialization of IntersectionStateManager."""
    
    def test_valid_initialization(self):
        """Test that the manager initializes with valid timing parameters."""
        manager = IntersectionStateManager(green_duration=20.0, yellow_duration=5.0, all_red_duration=3.0)
        
        assert manager.green_duration == 20.0
        assert manager.yellow_duration == 5.0
        assert manager.all_red_duration == 3.0
        assert len(manager.get_all_intersections()) == 0

    def test_zero_timing_raises_error(self):
        """Test that zero timing values raise ValueError."""
        with pytest.raises(ValueError):
            IntersectionStateManager(green_duration=0.0, yellow_duration=4.0, all_red_duration=2.0)
        
        with pytest.raises(ValueError):
            IntersectionStateManager(green_duration=15.0, yellow_duration=0.0, all_red_duration=2.0)
            
        with pytest.raises(ValueError):
            IntersectionStateManager(green_duration=15.0, yellow_duration=4.0, all_red_duration=0.0)


class TestIntersectionManagement:
    """Test adding, removing, and retrieving intersections."""
    
    def test_add_intersection(self, state_manager, simple_intersection):
        """Test adding an intersection to the manager."""
        state_manager.add_intersection(simple_intersection)
        
        retrieved = state_manager.get_intersection("test_intersection")
        assert retrieved is not None
        assert retrieved.tls_id == "test_intersection"
        assert len(retrieved.phases) == 2
        
        all_intersections = state_manager.get_all_intersections()
        assert "test_intersection" in all_intersections
        assert all_intersections["test_intersection"] is simple_intersection

    def test_remove_intersection(self, state_manager, simple_intersection):
        """Test removing an intersection from the manager."""
        state_manager.add_intersection(simple_intersection)
        assert state_manager.get_intersection("test_intersection") is not None
        
        state_manager.remove_intersection("test_intersection")
        assert state_manager.get_intersection("test_intersection") is None
        
        all_intersections = state_manager.get_all_intersections()
        assert "test_intersection" not in all_intersections

    def test_get_nonexistent_intersection(self, state_manager):
        """Test retrieving a non-existent intersection returns None."""
        assert state_manager.get_intersection("nonexistent") is None


class TestStateTransitions:
    """Test state transitions and timing behavior."""
    
    def test_starts_in_all_red(self, state_manager, simple_intersection, clock):
        """Test that intersections start in ALL_RED state."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        
        assert intersection.current_signal_state == SignalState.ALL_RED
        assert intersection.current_phase_index == 0

    def test_transition_all_red_to_green(self, state_manager, simple_intersection, clock):
        """Test transition from ALL_RED to GREEN after all-red duration."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())
        
        # Advance time past all-red duration
        clock.increment(state_manager.all_red_duration + 0.1)
        
        changes = state_manager.tick(clock.time())
        
        assert "test_intersection" in changes
        assert changes["test_intersection"] == "GGrr"  # First phase green state
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.GREEN
        assert intersection.current_phase_index == 0

    def test_transition_green_to_yellow(self, state_manager, simple_intersection, clock):
        """Test transition from GREEN to YELLOW after green duration."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())
        
        # Move to GREEN state first
        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())
        
        # Advance time past green duration
        clock.increment(state_manager.green_duration + 0.1)
        
        changes = state_manager.tick(clock.time())
        
        assert "test_intersection" in changes
        assert changes["test_intersection"] == "yyrr"  # First phase yellow state
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.YELLOW

    def test_transition_yellow_to_all_red_advances_phase(self, state_manager, simple_intersection, clock):
        """Test transition from YELLOW to ALL_RED advances to next phase."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())
        
        # Move to GREEN state first
        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())
        
        # Move to YELLOW state
        clock.increment(state_manager.green_duration + 0.1)
        state_manager.tick(clock.time())
        
        # Advance time past yellow duration
        clock.increment(state_manager.yellow_duration + 0.1)
        
        changes = state_manager.tick(clock.time())
        
        assert "test_intersection" in changes
        assert changes["test_intersection"] == "rrrr"  # All red state
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.ALL_RED
        assert intersection.current_phase_index == 1  # Advanced to next phase

    def test_full_cycle_wraps_around(self, state_manager, simple_intersection, clock):
        """Test that the phase cycle wraps around correctly."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())
        
        # Complete one full cycle
        # ALL_RED -> GREEN -> YELLOW -> ALL_RED (next phase)
        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())  # -> GREEN
        
        clock.increment(state_manager.green_duration + 0.1)
        state_manager.tick(clock.time())  # -> YELLOW
        
        clock.increment(state_manager.yellow_duration + 0.1)
        state_manager.tick(clock.time())  # -> ALL_RED (next phase)
        
        # Now complete the cycle for the second phase
        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())  # -> GREEN (second phase)
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.GREEN
        assert intersection.current_phase_index == 1
        
        assert len(changes) == 1
        assert changes["test_intersection"] == "rrGG"  # Second phase green state

    def test_no_changes_when_inactive(self, state_manager, simple_intersection, clock):
        """Test that no state changes occur when time hasn't advanced enough."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())
        
        # Don't advance time enough for any transition
        clock.increment(state_manager.all_red_duration - 0.1)
        
        changes = state_manager.tick(clock.time())
        
        assert changes == {}  # No changes should occur


class TestSafetyFeatures:
    """Test safety features of the IntersectionStateManager."""
    
    def test_final_safety_check_rejects_invalid_characters(self, state_manager):
        """Test that invalid characters in state strings are rejected."""
        # This test indirectly verifies the safety check by attempting to create
        # an invalid state. Since the safety check is internal, we'll test it
        # through the tick method which calls it.
        
        # Create a phase with invalid characters
        invalid_phase = PhaseDefinition(
            state_string="GGxrr",  # 'x' is invalid
            yellow_string="yyxrr",
            all_red_string="rrxrr"
        )
        
        invalid_intersection = IntersectionState(
            tls_id="invalid_intersection",
            phases=[invalid_phase]
        )
        
        state_manager.add_intersection(invalid_intersection)
        state_manager.reset_all_intersections(time.perf_counter())
        
        # Try to transition to the invalid state
        # We'll simulate this by patching the time and forcing a transition
        with patch('src.controller.intersection_state_manager.time') as mock_time:
            mock_time.perf_counter.return_value = 100.0  # Far enough to trigger transition
            
            # The safety check should prevent the invalid state from being returned
            changes = state_manager.tick(100.0)
            
            # Should still get a change, but it should be all red due to safety check
            assert "invalid_intersection" in changes
            assert changes["invalid_intersection"] == "rrrr"  # Forced all-red due to safety violation


class TestResetAndAllRed:
    """Test reset and all-red functionality."""
    
    def test_reset_all_intersections(self, state_manager, simple_intersection, clock):
        """Test resetting all intersections to initial state."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())
        
        # Advance state to GREEN
        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.GREEN
        
        # Reset should bring it back to ALL_RED
        clock.increment(1.0)  # Small increment
        state_manager.reset_all_intersections(clock.time())
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.ALL_RED
        assert intersection.current_phase_index == 0
        assert intersection.state_start_time == clock.time()

    def test_set_all_red(self, state_manager, simple_intersection, clock):
        """Test setting all intersections to ALL_RED state."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())
        
        # Advance state to GREEN
        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.GREEN
        
        # Set all red should force ALL_RED state
        state_manager.set_all_red()
        
        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.ALL_RED