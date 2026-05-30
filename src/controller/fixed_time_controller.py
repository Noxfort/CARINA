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

# File: src/controller/fixed_time_controller.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Deterministic Fixed-Time Traffic Signal Controller
---------------------------------------------------
Activated during Watchdog failsafe mode when SYNAPSE connection is lost.

Extracts TLS (Traffic Light Signal) programs directly from the loaded SUMO
.net.xml topology to build per-intersection phase cyclers. This ensures the
controller works with ANY intersection geometry (2-phase, 3-phase, 4-phase,
etc.) without hardcoding assumptions.

SAFETY GUARANTEES (Non-Negotiable):
    1. ALL_RED clearance is MANDATORY between every phase transition
    2. YELLOW time is MANDATORY before any GREEN→RED transition
    3. Conflicting approaches are NEVER simultaneously GREEN
    4. If any conflict is detected at runtime → immediate ALL_RED
    5. Minimum green time is always respected
    6. The system starts in ALL_RED and ends in ALL_RED

Architecture Note:
    The HWI (Hardware Interface) controller has its own built-in fixed-time
    plans and will independently switch to them when it loses connection.
    This controller models the expected behavior internally for:
        - Dashboard visualization
        - MQTT telemetry / incident reporting
        - Audit logging
        - Smooth recovery coordination when AI resumes
"""

import time
import logging
from typing import Dict, Optional

from src.controller.intersection_state_manager import IntersectionStateManager, IntersectionState
from src.controller.common_types import SignalState, PhaseDefinition
from src.controller.topology_loader import TopologyLoader

logger = logging.getLogger(__name__)


class FixedTimeController:
    """
    Deterministic Fixed-Time Traffic Controller.
    
    Generates safe, conflict-free phase commands for all traffic lights
    in the loaded topology. Operates as a pure state machine — receives
    no external input during operation, only advances with time.
    
    Usage:
        controller = FixedTimeController(green=15.0, yellow=4.0, all_red=2.0)
        controller.load_topology("/path/to/network.net.xml")
        controller.activate()
        
        while failsafe_active:
            changes = controller.tick()
            for tls_id, state_str in changes.items():
                log_or_report(tls_id, state_str)
        
        controller.deactivate()
    """

    def __init__(self, green_duration: float = 15.0, yellow_duration: float = 4.0,
                 all_red_duration: float = 2.0):
        """
        Args:
            green_duration: Seconds each phase stays GREEN. (TRAFFIC_RULES: min_green_time_seconds)
            yellow_duration: Seconds of YELLOW before transitioning. (TRAFFIC_RULES: yellow_time_seconds)
            all_red_duration: Seconds of ALL_RED clearance between phases. (TRAFFIC_RULES: all_red_time_seconds)
        """
        if green_duration <= 0 or yellow_duration <= 0 or all_red_duration <= 0:
            raise ValueError("All timing durations must be positive values.")

        # Store timing parameters for status reporting
        self.green_duration = green_duration
        self.yellow_duration = yellow_duration
        self.all_red_duration = all_red_duration
        
        self._intersection_state_manager = IntersectionStateManager(
            green_duration, yellow_duration, all_red_duration
        )
        self._topology_loader = TopologyLoader()
        self._is_active = False
        self._activation_time: Optional[float] = None
        self._topology_loaded = False

        logger.info(
            f"[FixedTimeController] Initialized. "
            f"Timing: {green_duration}s GREEN / {yellow_duration}s YELLOW / {all_red_duration}s ALL_RED"
        )

    # ------------------------------------------------------------------
    # Topology Loading
    # ------------------------------------------------------------------

    def load_topology(self, net_file_path: str) -> bool:
        """
        Extract TLS programs from the SUMO .net.xml network file.
        Builds per-intersection phase cyclers with conflict validation.
        
        This method uses the EXISTING phase definitions from the network,
        which are guaranteed to be conflict-free by SUMO's network builder.
        We add our own validation as a defense-in-depth safety measure.
        
        Args:
            net_file_path: Absolute path to the .net.xml file.
            
        Returns:
            True if at least one intersection was successfully loaded.
        """
        intersections, success = self._topology_loader.load_topology(net_file_path)
        
        if not success:
            self._topology_loaded = False
            return False

        # Add all intersections to the state manager
        for intersection_data in intersections:
            intersection_state = IntersectionState(
                tls_id=intersection_data.tls_id,
                phases=intersection_data.phase_definitions
            )
            self._intersection_state_manager.add_intersection(intersection_state)

        self._topology_loaded = True
        logger.info(f"[FixedTimeController] Topology loaded with {len(intersections)} intersections.")
        return True

    # ------------------------------------------------------------------
    # Activation / Deactivation
    # ------------------------------------------------------------------

    def activate(self):
        """
        Start the fixed-time cycle. All intersections begin in ALL_RED
        for a safe transition, then start cycling.
        """
        if not self._topology_loaded:
            logger.error("[FixedTimeController] Cannot activate — no topology loaded.")
            return

        self._is_active = True
        self._activation_time = time.perf_counter()

        # Reset all intersections to ALL_RED starting state
        now = time.perf_counter()
        self._intersection_state_manager.reset_all_intersections(now)

        logger.critical(
            f"[FixedTimeController] ⚠️  ACTIVATED — {len(self._intersection_state_manager.get_all_intersections())} intersections "
            f"switching to deterministic fixed-time control. "
            f"Cycle: {self.green_duration}s GREEN → {self.yellow_duration}s YELLOW → "
            f"{self.all_red_duration}s ALL_RED per phase."
        )

    def deactivate(self):
        """
        Stop the fixed-time cycle. All intersections snap to ALL_RED
        for a safe handoff back to AI control.
        """
        if not self._is_active:
            return

        elapsed = time.perf_counter() - self._activation_time if self._activation_time else 0
        self._is_active = False

        # Force ALL_RED on all intersections for safe handoff
        self._intersection_state_manager.set_all_red()

        intersections = self._intersection_state_manager.get_all_intersections()
        total_changes = sum(i.total_phase_changes for i in intersections.values())
        logger.info(
            f"[FixedTimeController] ✅ DEACTIVATED after {elapsed:.1f}s of fixed-time operation. "
            f"Total phase changes executed: {total_changes}. "
            f"All intersections set to ALL_RED for safe handoff to Neural Network."
        )

    # ------------------------------------------------------------------
    # Main Tick (State Machine Advance)
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, str]:
        """
        Advance all intersection state machines based on elapsed time.
        
        Must be called periodically (ideally every 50ms or faster).
        
        Returns:
            Dict mapping tls_id → new state_string for intersections
            that changed state in this tick. Empty dict if no changes.
        """
        if not self._is_active:
            return {}

        changes = {}
        now = time.perf_counter()

        # Delegate to the intersection state manager
        changes = self._intersection_state_manager.tick(now)

        return changes

    # ------------------------------------------------------------------
    # Status / Telemetry
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def topology_loaded(self) -> bool:
        return self._topology_loaded

    def get_status_summary(self) -> Dict:
        """
        Returns a comprehensive summary for dashboard and MQTT telemetry.
        """
        if not self._is_active:
            return {"active": False, "topology_loaded": self._topology_loaded}

        elapsed = time.perf_counter() - self._activation_time if self._activation_time else 0

        intersections_status = {}
        intersections = self._intersection_state_manager.get_all_intersections()
        for tls_id, intersection in intersections.items():
            phase_elapsed = time.perf_counter() - intersection.state_start_time
            intersections_status[tls_id] = {
                "phase_index": intersection.current_phase_index,
                "total_phases": len(intersection.phases),
                "signal_state": intersection.current_signal_state.value,
                "time_in_state_s": round(phase_elapsed, 1),
                "total_phase_changes": intersection.total_phase_changes,
            }

        # Calculate cycle length for a single intersection (they all share timing)
        sample_phases = len(next(iter(intersections.values())).phases) if intersections else 1
        cycle_length = (self.green_duration + self.yellow_duration + self.all_red_duration) * sample_phases

        return {
            "active": True,
            "elapsed_seconds": round(elapsed, 1),
            "total_intersections": len(intersections),
            "timing": {
                "green_s": self.green_duration,
                "yellow_s": self.yellow_duration,
                "all_red_s": self.all_red_duration,
                "cycle_length_s": cycle_length
            },
            "intersections": intersections_status
        }
