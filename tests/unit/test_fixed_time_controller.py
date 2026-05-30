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
#
# File: tests/unit/test_fixed_time_controller.py
# Author: Gabriel Moraes
# Date: 2026-04-21

"""
Unit tests for the FixedTimeController safety-critical state machine.

Uses mocked time.perf_counter() to avoid OS scheduler issues in CI.

Validates:
    - Correct state transitions: ALL_RED → GREEN → YELLOW → ALL_RED → next phase
    - No conflicting green signals at any point
    - Phase validation and error handling
    - Activation/deactivation lifecycle
    - Status reporting
"""

import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from controller.fixed_time_controller import (
    FixedTimeController, SignalState, PhaseDefinition, IntersectionState
)


# ---------------------------------------------------------------------------
# Mock Time Helper
# ---------------------------------------------------------------------------

class MockClock:
    """Deterministic clock for testing time-based state machines."""
    def __init__(self, start=1000.0):
        self._now = start
    
    def __call__(self):
        return self._now
    
    def advance(self, seconds: float):
        self._now += seconds


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clock():
    return MockClock()


@pytest.fixture
def controller(clock):
    """Create a controller with real production timings and mocked clock."""
    with patch('controller.fixed_time_controller.time.perf_counter', clock):
        ctrl = FixedTimeController(
            green_duration=15.0,
            yellow_duration=4.0,
            all_red_duration=2.0
        )
        yield ctrl


@pytest.fixture
def two_phase_intersection():
    """A simple 2-phase intersection (North-South vs East-West)."""
    return IntersectionState(
        tls_id="tls_intersection_1",
        phases=[
            PhaseDefinition(
                state_string="GGrrGGrr",  # NS green, EW red
                yellow_string="yyrryyrr",
                all_red_string="rrrrrrrr"
            ),
            PhaseDefinition(
                state_string="rrGGrrGG",  # NS red, EW green
                yellow_string="rryyrryy",
                all_red_string="rrrrrrrr"
            ),
        ]
    )


@pytest.fixture
def three_phase_intersection():
    """A 3-phase intersection with protected left turn."""
    return IntersectionState(
        tls_id="tls_intersection_2",
        phases=[
            PhaseDefinition(
                state_string="GGGrrrrrrr",
                yellow_string="yyyrrrrrrr",
                all_red_string="rrrrrrrrrr"
            ),
            PhaseDefinition(
                state_string="rrrGGGrrrr",
                yellow_string="rrryyyrrrr",
                all_red_string="rrrrrrrrrr"
            ),
            PhaseDefinition(
                state_string="rrrrrrGGGr",
                yellow_string="rrrrrryyyr",
                all_red_string="rrrrrrrrrr"
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Constructor Tests
# ---------------------------------------------------------------------------

class TestControllerInitialization:
    
    def test_valid_initialization(self):
        ctrl = FixedTimeController(green_duration=15.0, yellow_duration=4.0, all_red_duration=2.0)
        assert ctrl.green_duration == 15.0
        assert ctrl.yellow_duration == 4.0
        assert ctrl.all_red_duration == 2.0
        assert not ctrl.is_active
        assert not ctrl.topology_loaded

    def test_invalid_zero_duration(self):
        with pytest.raises(ValueError):
            FixedTimeController(green_duration=0, yellow_duration=4.0, all_red_duration=2.0)
    
    def test_invalid_negative_duration(self):
        with pytest.raises(ValueError):
            FixedTimeController(green_duration=15.0, yellow_duration=-1.0, all_red_duration=2.0)


# ---------------------------------------------------------------------------
# State Machine Tests
# ---------------------------------------------------------------------------

class TestStateMachine:

    def test_starts_in_all_red(self, controller, clock, two_phase_intersection):
        """SAFETY: Every intersection MUST start in ALL_RED."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        assert two_phase_intersection.current_signal_state == SignalState.ALL_RED

    def test_transition_all_red_to_green(self, controller, clock, two_phase_intersection):
        """After ALL_RED duration (2s), transition to GREEN."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        # Not enough time yet
        clock.advance(1.0)
        changes = controller.tick()
        assert changes == {}
        
        # ALL_RED expires at 2s
        clock.advance(1.5)
        changes = controller.tick()
        
        assert "tls1" in changes
        assert changes["tls1"] == "GGrrGGrr"  # Phase 0 green
        assert two_phase_intersection.current_signal_state == SignalState.GREEN

    def test_transition_green_to_yellow(self, controller, clock, two_phase_intersection):
        """After GREEN duration (15s), transition to YELLOW."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        # ALL_RED (2s) → GREEN
        clock.advance(2.5)
        controller.tick()
        assert two_phase_intersection.current_signal_state == SignalState.GREEN
        
        # GREEN (15s) → YELLOW
        clock.advance(15.5)
        changes = controller.tick()
        
        assert "tls1" in changes
        assert changes["tls1"] == "yyrryyrr"  # Phase 0 yellow
        assert two_phase_intersection.current_signal_state == SignalState.YELLOW

    def test_transition_yellow_to_all_red_advances_phase(self, controller, clock, two_phase_intersection):
        """After YELLOW (4s), go to ALL_RED and advance to next phase."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        # ALL_RED → GREEN
        clock.advance(2.5)
        controller.tick()
        
        # GREEN → YELLOW
        clock.advance(15.5)
        controller.tick()
        
        # YELLOW → ALL_RED (phase advances to 1)
        clock.advance(4.5)
        changes = controller.tick()
        
        assert "tls1" in changes
        assert changes["tls1"] == "rrrrrrrr"  # ALL_RED
        assert two_phase_intersection.current_phase_index == 1
        assert two_phase_intersection.current_signal_state == SignalState.ALL_RED

    def test_full_cycle_wraps_around(self, controller, clock, two_phase_intersection):
        """Complete cycle through both phases wraps back to phase 0."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        # Phase 0: ALL_RED(2s) → GREEN(15s) → YELLOW(4s) → ALL_RED(2s)
        clock.advance(2.5); controller.tick()   # → GREEN phase 0
        clock.advance(15.5); controller.tick()  # → YELLOW phase 0
        clock.advance(4.5); controller.tick()   # → ALL_RED, advance to phase 1
        
        assert two_phase_intersection.current_phase_index == 1
        
        # Phase 1: ALL_RED(2s) → GREEN(15s) → YELLOW(4s) → ALL_RED(2s)
        clock.advance(2.5); controller.tick()   # → GREEN phase 1
        
        assert controller.tick()  # Should be empty (no transition yet)
        changes = controller.tick()
        
        # Verify phase 1 GREEN state
        assert two_phase_intersection.current_signal_state == SignalState.GREEN
        
        clock.advance(15.5); controller.tick()  # → YELLOW phase 1
        clock.advance(4.5); controller.tick()   # → ALL_RED, advance to phase 0
        
        # Should wrap back to phase 0
        assert two_phase_intersection.current_phase_index == 0

    def test_three_phase_cycle(self, controller, clock, three_phase_intersection):
        """3-phase intersection cycles correctly through all phases."""
        controller._intersections = {"tls1": three_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        for expected_phase in [0, 1, 2, 0]:
            clock.advance(2.5)   # ALL_RED
            changes = controller.tick()
            assert "tls1" in changes
            assert three_phase_intersection.current_phase_index == expected_phase
            
            clock.advance(15.5)  # GREEN
            controller.tick()
            
            clock.advance(4.5)   # YELLOW → ALL_RED + advance
            controller.tick()

    def test_no_changes_when_inactive(self, controller, clock, two_phase_intersection):
        """Tick should return empty dict when not active."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        # Don't activate
        
        clock.advance(100.0)
        changes = controller.tick()
        assert changes == {}


# ---------------------------------------------------------------------------
# Safety Invariant Tests
# ---------------------------------------------------------------------------

class TestSafetyInvariants:

    def test_all_red_clearance_always_present(self, controller, clock, two_phase_intersection):
        """SAFETY: ALL_RED must appear between every GREEN phase transition."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        state_sequence = []
        
        # Run 3 full cycles (42s each = 126s total)
        for _ in range(1260):
            clock.advance(0.1)
            changes = controller.tick()
            if "tls1" in changes:
                state = changes["tls1"]
                has_green = any(c in ('G', 'g') for c in state)
                has_yellow = any(c == 'y' for c in state)
                all_red = all(c == 'r' for c in state)
                
                if has_green:
                    state_sequence.append("GREEN")
                elif has_yellow:
                    state_sequence.append("YELLOW")
                elif all_red:
                    state_sequence.append("ALL_RED")
        
        # Verify the sequence pattern: every GREEN must be preceded by ALL_RED
        for i in range(1, len(state_sequence)):
            if state_sequence[i] == "GREEN":
                assert state_sequence[i - 1] == "ALL_RED", \
                    f"GREEN at position {i} was NOT preceded by ALL_RED! " \
                    f"Sequence around: {state_sequence[max(0, i-2):i+2]}"

    def test_yellow_always_follows_green(self, controller, clock, two_phase_intersection):
        """SAFETY: GREEN must ALWAYS be followed by YELLOW (never jump to ALL_RED)."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        state_sequence = []
        
        for _ in range(1260):
            clock.advance(0.1)
            changes = controller.tick()
            if "tls1" in changes:
                state = changes["tls1"]
                has_green = any(c in ('G', 'g') for c in state)
                has_yellow = any(c == 'y' for c in state)
                all_red = all(c == 'r' for c in state)
                
                if has_green:
                    state_sequence.append("GREEN")
                elif has_yellow:
                    state_sequence.append("YELLOW")
                elif all_red:
                    state_sequence.append("ALL_RED")
        
        # Verify: GREEN → YELLOW (mandatory)
        for i in range(len(state_sequence) - 1):
            if state_sequence[i] == "GREEN":
                assert state_sequence[i + 1] == "YELLOW", \
                    f"GREEN at position {i} was followed by {state_sequence[i+1]}, not YELLOW!"

    def test_expected_sequence_pattern(self, controller, clock, two_phase_intersection):
        """The full expected pattern is: ALL_RED → GREEN → YELLOW → ALL_RED → GREEN → ..."""
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        state_sequence = []
        
        for _ in range(500):
            clock.advance(0.1)
            changes = controller.tick()
            if "tls1" in changes:
                state = changes["tls1"]
                has_green = any(c in ('G', 'g') for c in state)
                has_yellow = any(c == 'y' for c in state)
                all_red = all(c == 'r' for c in state)
                
                if has_green:
                    state_sequence.append("GREEN")
                elif has_yellow:
                    state_sequence.append("YELLOW")
                elif all_red:
                    state_sequence.append("ALL_RED")
        
        # Expected pattern repeats: ALL_RED, GREEN, YELLOW, ALL_RED, GREEN, YELLOW, ...
        expected_cycle = ["ALL_RED", "GREEN", "YELLOW"]
        for i, actual in enumerate(state_sequence):
            expected = expected_cycle[i % 3]
            assert actual == expected, \
                f"Position {i}: expected {expected}, got {actual}. " \
                f"Full sequence: {state_sequence[:i+3]}"

    def test_invalid_character_rejected(self, controller):
        """States with invalid characters must be caught by final safety check."""
        assert controller._final_safety_check("test", "GGrrGGrr") is True
        assert controller._final_safety_check("test", "GGrrXXrr") is False
        assert controller._final_safety_check("test", "GGrr GGrr") is False


# ---------------------------------------------------------------------------
# Phase Validation Tests
# ---------------------------------------------------------------------------

class TestPhaseValidation:

    def test_valid_phases_pass(self, controller):
        phases = [
            PhaseDefinition("GGrr", "yyrr", "rrrr"),
            PhaseDefinition("rrGG", "rryy", "rrrr"),
        ]
        assert controller._validate_phases("test", phases) is True

    def test_mismatched_lengths_fail(self, controller):
        phases = [
            PhaseDefinition("GGrr", "yyrr", "rrrr"),
            PhaseDefinition("rrGGG", "rryyy", "rrrrr"),  # Different length!
        ]
        assert controller._validate_phases("test", phases) is False

    def test_invalid_characters_fail(self, controller):
        phases = [
            PhaseDefinition("GGXr", "yyrr", "rrrr"),  # 'X' is invalid
        ]
        assert controller._validate_phases("test", phases) is False

    def test_empty_phases_pass(self, controller):
        assert controller._validate_phases("test", []) is True


# ---------------------------------------------------------------------------
# Activation / Deactivation Tests
# ---------------------------------------------------------------------------

class TestLifecycle:

    def test_activate_without_topology_does_nothing(self, controller):
        controller.activate()
        assert not controller.is_active

    def test_activate_with_topology(self, controller, two_phase_intersection):
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        assert controller.is_active

    def test_deactivate_sets_all_red(self, controller, clock, two_phase_intersection):
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        # Advance to GREEN
        clock.advance(2.5)
        controller.tick()
        assert two_phase_intersection.current_signal_state == SignalState.GREEN
        
        # Deactivate
        controller.deactivate()
        assert not controller.is_active
        assert two_phase_intersection.current_signal_state == SignalState.ALL_RED

    def test_deactivate_when_inactive_is_noop(self, controller):
        controller.deactivate()  # Should not raise
        assert not controller.is_active


# ---------------------------------------------------------------------------
# Status Reporting Tests
# ---------------------------------------------------------------------------

class TestStatusReporting:

    def test_inactive_status(self, controller):
        status = controller.get_status_summary()
        assert status["active"] is False

    def test_active_status(self, controller, two_phase_intersection):
        controller._intersections = {"tls1": two_phase_intersection}
        controller._topology_loaded = True
        controller.activate()
        
        status = controller.get_status_summary()
        assert status["active"] is True
        assert status["total_intersections"] == 1
        assert "timing" in status
        assert status["timing"]["green_s"] == 15.0
        assert status["timing"]["yellow_s"] == 4.0
        assert status["timing"]["all_red_s"] == 2.0
        assert "tls1" in status["intersections"]


# ---------------------------------------------------------------------------
# Helper Method Tests
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_derive_yellow(self):
        assert FixedTimeController._derive_yellow("GGrrGGrr") == "yyrryyrr"
        assert FixedTimeController._derive_yellow("gGrrrr") == "yyrrrr"
        assert FixedTimeController._derive_yellow("rrrrrr") == "rrrrrr"
        assert FixedTimeController._derive_yellow("GgGgGg") == "yyyyyy"

    def test_extract_green_phases_filters_yellow(self, controller):
        """Yellow-only phases should be filtered out."""
        mock_phase_green = MagicMock()
        mock_phase_green.state = "GGrrGGrr"
        
        mock_phase_yellow = MagicMock()
        mock_phase_yellow.state = "yyrryyrr"
        
        mock_phase_all_red = MagicMock()
        mock_phase_all_red.state = "rrrrrrrr"
        
        result = controller._extract_green_phases("test", [mock_phase_green, mock_phase_yellow, mock_phase_all_red])
        assert len(result) == 1
        assert result[0] == "GGrrGGrr"
