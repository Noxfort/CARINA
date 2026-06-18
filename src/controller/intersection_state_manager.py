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

# File: src/controller/intersection_state_manager.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Intersection State Manager
--------------------------
Handles the state management for individual intersections in the fixed-time controller.

This component is responsible for:
- Managing the current state of each intersection (GREEN, YELLOW, ALL_RED)
- Tracking phase transitions and timing
- Handling the state machine logic for phase advancement
"""

import time
import logging
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from src.controller.common_types import SignalState, StageDefinition

logger = logging.getLogger(__name__)


@dataclass
class IntersectionState:
    """Runtime state for a single intersection's fixed-time cycle."""
    tls_id: str
    phases: List[StageDefinition]
    current_phase_index: int = 0
    current_signal_state: SignalState = field(default=SignalState.ALL_RED)
    state_start_time: float = 0.0
    total_phase_changes: int = 0


class IntersectionStateManager:
    """
    Manages the state of intersections for the Fixed-Time Controller.
    
    This class encapsulates all the logic related to managing intersection states,
    including state transitions, timing calculations, and phase advancement.
    """
    
    # Valid SUMO signal characters
    _VALID_SIGNAL_CHARS = frozenset({'G', 'g', 'r', 'y', 'o', 's', 'u'})

    def __init__(self, green_duration: float = 15.0, yellow_duration: float = 4.0,
                 all_red_duration: float = 2.0):
        """
        Args:
            green_duration: Seconds each phase stays GREEN.
            yellow_duration: Seconds of YELLOW before transitioning.
            all_red_duration: Seconds of ALL_RED clearance between phases.
        """
        if green_duration <= 0 or yellow_duration <= 0 or all_red_duration <= 0:
            raise ValueError("Timing parameters must be greater than zero.")
            
        self.green_duration = green_duration
        self.yellow_duration = yellow_duration
        self.all_red_duration = all_red_duration
        
        self._intersections: Dict[str, IntersectionState] = {}

    def add_intersection(self, intersection: IntersectionState):
        """
        Add an intersection to be managed.
        
        Args:
            intersection: The IntersectionState to manage
        """
        self._intersections[intersection.tls_id] = intersection

    def remove_intersection(self, tls_id: str):
        """
        Remove an intersection from management.
        
        Args:
            tls_id: The ID of the intersection to remove
        """
        if tls_id in self._intersections:
            del self._intersections[tls_id]

    def get_intersection(self, tls_id: str) -> Optional[IntersectionState]:
        """
        Get the state of a specific intersection.
        
        Args:
            tls_id: The ID of the intersection
            
        Returns:
            The IntersectionState if found, None otherwise
        """
        return self._intersections.get(tls_id)

    def get_all_intersections(self) -> Dict[str, IntersectionState]:
        """
        Get all managed intersections.
        
        Returns:
            Dictionary of all intersections
        """
        return self._intersections.copy()

    def tick(self, now: float) -> Dict[str, str]:
        """
        Advance all intersection state machines based on elapsed time.
        
        Args:
            now: Current time in seconds
            
        Returns:
            Dict mapping tls_id → new state_string for intersections
            that changed state in this tick. Empty dict if no changes.
        """
        changes = {}
        
        for tls_id, intersection in self._intersections.items():
            new_state = self._tick_intersection(intersection, now)
            if new_state is not None:
                # FINAL SAFETY CHECK before output
                if self._final_safety_check(tls_id, new_state):
                    changes[tls_id] = new_state
                else:
                    # Safety violation — force ALL_RED
                    all_red = 'r' * len(new_state)
                    changes[tls_id] = all_red
                    logger.critical(
                        f"[IntersectionStateManager] 🚨 SAFETY VIOLATION PREVENTED in '{tls_id}'! "
                        f"Forcing ALL_RED. Rejected state: {new_state}"
                    )
        
        return changes

    def _tick_intersection(self, intersection: IntersectionState, now: float) -> Optional[str]:
        """
        Advance a single intersection's state machine.
        
        State Machine:
            ALL_RED (2s) → GREEN (15s) → YELLOW (4s) → ALL_RED (2s) → next phase GREEN → ...
        
        Returns the new state string if a transition occurred, None otherwise.
        """
        if not intersection.phases:
            return None

        elapsed = now - intersection.state_start_time
        phase = intersection.phases[intersection.current_phase_index]

        if intersection.current_signal_state == SignalState.ALL_RED:
            if elapsed >= self.all_red_duration:
                intersection.current_signal_state = SignalState.GREEN
                intersection.state_start_time = now
                intersection.total_phase_changes += 1
                logger.info(
                    f"[FixedTime] {intersection.tls_id} → GREEN "
                    f"(Phase {intersection.current_phase_index}/{len(intersection.phases) - 1})"
                )
                return phase.state_string

        elif intersection.current_signal_state == SignalState.GREEN:
            if elapsed >= self.green_duration:
                intersection.current_signal_state = SignalState.YELLOW
                intersection.state_start_time = now
                intersection.total_phase_changes += 1
                logger.info(
                    f"[FixedTime] {intersection.tls_id} → YELLOW "
                    f"(Phase {intersection.current_phase_index}/{len(intersection.phases) - 1})"
                )
                return phase.yellow_string

        elif intersection.current_signal_state == SignalState.YELLOW:
            if elapsed >= self.yellow_duration:
                intersection.current_signal_state = SignalState.ALL_RED
                intersection.state_start_time = now
                intersection.total_phase_changes += 1
                # Advance to next phase (wraps around)
                intersection.current_phase_index = (
                    (intersection.current_phase_index + 1) % len(intersection.phases)
                )
                next_phase = intersection.phases[intersection.current_phase_index]
                logger.info(
                    f"[FixedTime] {intersection.tls_id} → ALL_RED "
                    f"(clearing for Phase {intersection.current_phase_index})"
                )
                return next_phase.all_red_string

        return None  # No state change this tick

    def _final_safety_check(self, tls_id: str, state: str) -> bool:
        """
        Last line of defense. Validates the outgoing state string.
        
        Returns True if the state is safe to output, False otherwise.
        """
        # Verify all characters are valid
        if not all(c in self._VALID_SIGNAL_CHARS for c in state):
            logger.error(f"[IntersectionStateManager] Invalid characters in state for '{tls_id}': {state}")
            return False

        return True

    def reset_all_intersections(self, now: float):
        """
        Reset all intersections to their initial state.
        
        Args:
            now: Current time to set as the start time for all intersections
        """
        for intersection in self._intersections.values():
            intersection.current_phase_index = 0
            intersection.current_signal_state = SignalState.ALL_RED
            intersection.state_start_time = now
            intersection.total_phase_changes = 0

    def set_all_red(self):
        """
        Set all intersections to ALL_RED state for safe handoff.
        """
        for intersection in self._intersections.values():
            intersection.current_signal_state = SignalState.ALL_RED
