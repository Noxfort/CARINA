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

    def __init__(self, ai_pipe_conn: Connection, monitor_client: Optional[Any] = None, locale_manager: Optional[Any] = None):
        self.current_operation_mode = "AUTOMATIC"
        self.failsafe_active = False

        self.ai_pipe_conn = ai_pipe_conn
        self.monitor_client = monitor_client
        self.locale_manager = monitor_client.locale_manager if monitor_client else locale_manager

        # --- Frame Timing Monitor ---
        # Tracks the last time a TrafficFrame was received.
        # Used by CentralController to detect Synapse silence in-process.
        self._last_frame_time: Optional[float] = None
        self._failsafe_timeout: float = 0.30  # 300ms default, overridden by settings



        # --- Failsafe Statistics ---
        self._failsafe_activation_time: Optional[float] = None
        self._total_failsafe_events: int = 0

    def set_failsafe_timeout(self, timeout_seconds: float):
        """Set the Synapse silence timeout (from settings.ini WATCHDOG section)."""
        self._failsafe_timeout = timeout_seconds

    def load_topology(self, net_file_path: str):
        """
        No-op since local Fixed-Time control was removed to keep CARINA agnostic.
        Hardware controllers should handle their own topology for fallbacks.
        """
        pass

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

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def trigger_failsafe(self):
        """
        Forces the system into Fail-Safe (Watchdog) mode.
        Activates the FixedTimeController and reports the incident.
        """
        if not self.failsafe_active:
            self._total_failsafe_events += 1
            self._failsafe_activation_time = time.perf_counter()

            logger.critical(
                self._get_string(
                    "failsafe_manager.entering_watchdog",
                    default="[FailsafeManager] 🚨 ENTERING WATCHDOG MODE (Fixed-Time Fallback). AI Neural Network PAUSED. Event #{event}.",
                    event=self._total_failsafe_events
                )
            )

            self.failsafe_active = True
            self.current_operation_mode = "WATCHDOG"

            # TODO: Emit command to hardware controller to activate ALL_RED then local fixed-plans
            logger.critical(self._get_string("failsafe_manager.commanding_all_red", default="[FailsafeManager] ⚠️ COMMANDING LOCAL CONTROLLER: Execute ALL_RED transition followed by local fixed-time plans."))

            # Report Critical Incident to External Monitor (MQTT)
            if self.monitor_client:
                try:
                    self.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="CRITICAL",
                        message=self._get_string(
                            "monitor.watchdog_trigger",
                            default="Watchdog timeout triggered (>{timeout}ms silence). Switching to Fixed-Time fallback. Event #{event}.",
                            timeout=f"{self._failsafe_timeout * 1000:.0f}",
                            event=self._total_failsafe_events
                        )
                    )
                except Exception as e:
                    logger.error(self._get_string("failsafe_manager.mqtt_incident_error", default="Error reporting failsafe incident via MQTT: {error}", error=e))

    def attempt_recovery(self) -> bool:
        """
        Attempts to recover the system from Watchdog mode.
        Called when a new TrafficFrame arrives during failsafe.
        
        Returns True if recovery occurred in this call.
        """
        if self.failsafe_active:
            elapsed = time.perf_counter() - self._failsafe_activation_time if self._failsafe_activation_time else 0

            logger.info(
                self._get_string(
                    "failsafe_manager.signal_restored",
                    default="[FailsafeManager] ✅ SYNAPSE SIGNAL RESTORED after {elapsed:.1f}s. Resuming AI Neural Network control.",
                    elapsed=elapsed
                )
            )

            # TODO: Emit command to hardware controller to resume remote control
            logger.info(self._get_string("failsafe_manager.commanding_resume", default="[FailsafeManager] ✅ COMMANDING LOCAL CONTROLLER: Resume remote AI control."))

            self.failsafe_active = False
            self.current_operation_mode = "AUTOMATIC"

            # Report Recovery to External Monitor (MQTT)
            if self.monitor_client:
                try:
                    self.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="INFO",
                        message=self._get_string(
                            "monitor.synapse_restored",
                            default="Synapse signal restored after {elapsed}s. Watchdog mode disabled, resuming AI Neural Network.",
                            elapsed=f"{elapsed:.1f}"
                        )
                    )
                except Exception as e:
                    logger.error(self._get_string("failsafe_manager.mqtt_recovery_error", default="Error reporting recovery incident via MQTT: {error}", error=e))

            # Wake up AI process
            try:
                self.ai_pipe_conn.send(('system', 'wakeup', (), {}))
            except Exception as e:
                logger.error(self._get_string("failsafe_manager.wakeup_error", default="Error sending wakeup signal to AI: {error}", error=e))

            return True
        return False

    def tick(self) -> Dict[str, str]:
        """
        Advance the failsafe state.
        Since local fixed-time control was removed, this just returns empty.
        Hardware handles its own ticking during failsafe.
        """
        return {}

    def get_status(self) -> Dict:
        """Returns complete failsafe status for dashboard/telemetry."""
        return {
            "operation_mode": self.current_operation_mode,
            "failsafe_active": self.failsafe_active,
            "total_failsafe_events": self._total_failsafe_events,
            "fixed_time": {} # Kept for dashboard compatibility
        }
