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

# File: src/controller/failsafe_manager.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import logging
import time
from multiprocessing.connection import Connection
from typing import Optional, Any, Dict

from controller.fixed_time_controller import FixedTimeController

logger = logging.getLogger(__name__)


class FailsafeManager:
    """
    Responsible for managing the global operation mode of CARINA:
        - AUTOMATIC: AI Neural Network controls traffic signals
        - WATCHDOG: Fixed-time fallback (Synapse connection lost)
        - MANUAL: Operator override (future)
    
    Owns the FixedTimeController and coordinates the transition between
    AI-controlled and fixed-time modes with strict safety guarantees.
    """

    def __init__(self, ai_pipe_conn: Connection, monitor_client: Optional[Any] = None,
                 green_duration: float = 15.0, yellow_duration: float = 4.0,
                 all_red_duration: float = 2.0):
        self.current_operation_mode = "AUTOMATIC"
        self.failsafe_active = False

        self.ai_pipe_conn = ai_pipe_conn
        self.monitor_client = monitor_client

        # --- Frame Timing Monitor ---
        # Tracks the last time a TrafficFrame was received.
        # Used by CentralController to detect Synapse silence in-process.
        self._last_frame_time: Optional[float] = None
        self._failsafe_timeout: float = 0.30  # 300ms default, overridden by settings

        # --- Fixed-Time Controller ---
        self.fixed_time_controller = FixedTimeController(
            green_duration=green_duration,
            yellow_duration=yellow_duration,
            all_red_duration=all_red_duration
        )

        # --- Failsafe Statistics ---
        self._failsafe_activation_time: Optional[float] = None
        self._total_failsafe_events: int = 0

    def set_failsafe_timeout(self, timeout_seconds: float):
        """Set the Synapse silence timeout (from settings.ini WATCHDOG section)."""
        self._failsafe_timeout = timeout_seconds

    def load_topology(self, net_file_path: str):
        """
        Pre-load the traffic light topology so the FixedTimeController
        is ready to activate instantly when failsafe triggers.
        Called when a new map is loaded or state is restored.
        """
        success = self.fixed_time_controller.load_topology(net_file_path)
        if success:
            logger.info("[FailsafeManager] Topology pre-loaded for failsafe readiness.")
        else:
            logger.warning("[FailsafeManager] Failed to pre-load topology. Failsafe will only log, not model.")

    def record_frame_received(self):
        """
        Record that a TrafficFrame was received from Synapse.
        Called by TrafficFrameProcessor on every frame.
        """
        self._last_frame_time = time.perf_counter()

    def check_synapse_health(self) -> bool:
        """
        Check if Synapse has been silent beyond the timeout threshold.
        Called periodically from CentralController main loop.
        
        Returns:
            True if healthy (frames arriving), False if timeout exceeded.
        """
        if self._last_frame_time is None:
            # No frames ever received — in grace period (startup)
            return True

        elapsed = time.perf_counter() - self._last_frame_time
        return elapsed <= self._failsafe_timeout

    def trigger_failsafe(self):
        """
        Forces the system into Fail-Safe (Watchdog) mode.
        Activates the FixedTimeController and reports the incident.
        """
        if not self.failsafe_active:
            self._total_failsafe_events += 1
            self._failsafe_activation_time = time.perf_counter()

            logger.critical(
                f"[FailsafeManager] 🚨 ENTERING WATCHDOG MODE (Fixed-Time Fallback). "
                f"AI Neural Network PAUSED. Event #{self._total_failsafe_events}."
            )

            self.failsafe_active = True
            self.current_operation_mode = "WATCHDOG"

            # Activate Fixed-Time Controller
            self.fixed_time_controller.activate()

            # Report Critical Incident to External Monitor (MQTT)
            if self.monitor_client:
                try:
                    self.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="CRITICAL",
                        message=(
                            f"Watchdog timeout triggered (>{self._failsafe_timeout * 1000:.0f}ms silence). "
                            f"Switching to Fixed-Time fallback. Event #{self._total_failsafe_events}."
                        )
                    )
                except Exception as e:
                    logger.error(f"Error reporting failsafe incident via MQTT: {e}")

    def attempt_recovery(self) -> bool:
        """
        Attempts to recover the system from Watchdog mode.
        Called when a new TrafficFrame arrives during failsafe.
        
        Returns True if recovery occurred in this call.
        """
        if self.failsafe_active:
            elapsed = time.perf_counter() - self._failsafe_activation_time if self._failsafe_activation_time else 0

            logger.info(
                f"[FailsafeManager] ✅ SYNAPSE SIGNAL RESTORED after {elapsed:.1f}s. "
                f"Resuming AI Neural Network control."
            )

            # Deactivate Fixed-Time Controller (goes to ALL_RED for safe handoff)
            self.fixed_time_controller.deactivate()

            self.failsafe_active = False
            self.current_operation_mode = "AUTOMATIC"

            # Report Recovery to External Monitor (MQTT)
            if self.monitor_client:
                try:
                    self.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="INFO",
                        message=(
                            f"Synapse signal restored after {elapsed:.1f}s. "
                            f"Watchdog mode disabled, resuming AI Neural Network."
                        )
                    )
                except Exception as e:
                    logger.error(f"Error reporting recovery incident via MQTT: {e}")

            # Wake up AI process
            try:
                self.ai_pipe_conn.send(('system', 'wakeup', (), {}))
            except Exception as e:
                logger.error(f"Error sending wakeup signal to AI: {e}")

            return True
        return False

    def tick(self) -> Dict[str, str]:
        """
        Advance the fixed-time controller (only when failsafe is active).
        Called from CentralController main loop.
        
        Returns:
            Dict of {tls_id: state_string} for intersections that changed state.
        """
        if not self.failsafe_active:
            return {}

        return self.fixed_time_controller.tick()

    def get_status(self) -> Dict:
        """Returns complete failsafe status for dashboard/telemetry."""
        return {
            "operation_mode": self.current_operation_mode,
            "failsafe_active": self.failsafe_active,
            "total_failsafe_events": self._total_failsafe_events,
            "fixed_time": self.fixed_time_controller.get_status_summary()
        }
