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

# File: src/watchdog/watchdog_logic.py
# Author: Gabriel Moraes
# Date: 2026-06-11

import time
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class Watchdog:
    """
    Monitors the 'heartbeat' of the input data stream.
    If the time since the last heartbeat exceeds the threshold, it triggers a safety fallback.
    """

    def __init__(self, timeout_ms: int = 300, grace_period_sec: float = 10.0, locale_manager=None):
        """
        Initialize the Watchdog.

        Args:
            timeout_ms (int): The maximum allowed silence from Synapse in milliseconds before
                               triggering fail-safe mode.
            grace_period_sec (float): The initial grace period in seconds during startup.
            locale_manager: Optional LocaleManagerBackend instance.
        """
        if timeout_ms <= 300:
            timeout_ms = 300

        self._timeout_seconds = timeout_ms / 1000.0
        self._grace_period_seconds = grace_period_sec
        self._startup_time = time.perf_counter()
        self._last_heartbeat_time = None
        self._is_fail_safe_active = False
        self.locale_manager = locale_manager
        
        # Callbacks for state transitions
        self._on_fallback_activate: Optional[Callable[[], None]] = None
        self._on_fallback_deactivate: Optional[Callable[[], None]] = None

        # --- Flapping Detection ---
        self._consecutive_triggers = 0
        self._total_triggers = 0
        self._total_recoveries = 0
        self._FLAPPING_THRESHOLD = 5  # Triggers within short succession = systemic issue

        logger.info(self._get_string("watchdog.init", default="Watchdog Logic initialized with {timeout}ms timeout threshold and {grace}s grace period.", timeout=timeout_ms, grace=grace_period_sec))

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def set_callbacks(self, on_activate: Callable[[], None], on_deactivate: Callable[[], None]):
        """
        Register callback functions to be triggered when state changes.
        """
        self._on_fallback_activate = on_activate
        self._on_fallback_deactivate = on_deactivate

    def register_heartbeat(self):
        """
        Called whenever a valid data packet is received from Synapse.
        Resets the timer and recovers from Fail-Safe if currently active.
        """
        self._last_heartbeat_time = time.perf_counter()

        if self._is_fail_safe_active:
            self._recover_system()

    def check_system_health(self) -> bool:
        """
        Evaluates the current state against the timer.
        Returns True if system is healthy, False if in Fail-Safe mode.
        """
        current_time = time.perf_counter()
        
        # If we are within the initial startup grace period, we are healthy
        if current_time - self._startup_time <= self._grace_period_seconds:
            return True
            
        if self._last_heartbeat_time is None:
            # Grace period expired and no heartbeat received yet
            if not self._is_fail_safe_active:
                self._trigger_failsafe(current_time - self._startup_time)
            return False
            
        elapsed_time = current_time - self._last_heartbeat_time

        if elapsed_time > self._timeout_seconds:
            if not self._is_fail_safe_active:
                self._trigger_failsafe(elapsed_time)
            return False
        
        return True

    def _trigger_failsafe(self, elapsed_time: float):
        self._is_fail_safe_active = True
        self._consecutive_triggers += 1
        self._total_triggers += 1
        
        logger.critical(
            self._get_string(
                "watchdog.triggered",
                default="WATCHDOG TRIGGERED: Synapse silence detected ({elapsed:.1f}ms > {threshold:.0f}ms). Switching to FIXED-TIME mode. [triggers: {consecutive} consecutive, {total} total]",
                elapsed=elapsed_time*1000,
                threshold=self._timeout_seconds*1000,
                consecutive=self._consecutive_triggers,
                total=self._total_triggers
            )
        )
        
        # Flapping detection: if we keep triggering and recovering rapidly, something is wrong
        if self._consecutive_triggers >= self._FLAPPING_THRESHOLD:
            logger.critical(
                self._get_string(
                    "watchdog.flapping",
                    default="WATCHDOG FLAPPING DETECTED: {consecutive} consecutive triggers. This indicates a SYSTEMIC latency issue. Check HFT diagnostics log.",
                    consecutive=self._consecutive_triggers
                )
            )
        
        if self._on_fallback_activate:
            try:
                self._on_fallback_activate()
            except Exception as e:
                logger.error(self._get_string("watchdog.activation_error", default="Error executing Watchdog activation callback: {error}", error=e))

    def _recover_system(self):
        self._is_fail_safe_active = False
        self._total_recoveries += 1
        
        logger.info(
            self._get_string(
                "watchdog.recovery",
                default="WATCHDOG RECOVERY: Signal restored. Resuming Neural Network control. [was {consecutive} consecutive trigger(s)]",
                consecutive=self._consecutive_triggers
            )
        )
        
        # Reset consecutive counter on recovery
        self._consecutive_triggers = 0
        
        if self._on_fallback_deactivate:
            try:
                self._on_fallback_deactivate()
            except Exception as e:
                logger.error(self._get_string("watchdog.deactivation_error", default="Error executing Watchdog deactivation callback: {error}", error=e))

    @property
    def is_in_failsafe(self) -> bool:
        return self._is_fail_safe_active
