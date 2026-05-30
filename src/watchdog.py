# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# it under the terms of the GNU Affero General Public License as
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/watchdog.py
# Author: Gabriel Moraes
# Date: 09/01/2026

"""
System Watchdog Module
----------------------
Responsible for monitoring the health of the connection with the Perception Layer (Synapse).
Run as a separate process to ensure system safety even if the main thread hangs.
"""

import time
import logging
import os
import sys
import configparser
from multiprocessing import Queue
from typing import Optional, Callable
import queue

# Add parent directory to path to locate utils if necessary
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from utils.paths import get_base_output_dir, resource_path
    from utils.logging_setup import setup_logging
except ImportError:
    # Fallback if utils not found in path
    def get_base_output_dir(): return "."
    def resource_path(p): return p
    def setup_logging(log_dir): pass

# Configure module-level logger
logger = logging.getLogger(__name__)

class Watchdog:
    """
    Monitors the 'heartbeat' of the input data stream.
    If the time since the last heartbeat exceeds the threshold, it triggers a safety fallback.
    """

    def __init__(self, timeout_ms: int = 300):
        """
        Initialize the Watchdog.

        Args:
            timeout_ms (int): The maximum allowed silence from Synapse in milliseconds before
                              triggering fail-safe mode.
        """
        self._timeout_seconds = timeout_ms / 1000.0
        self._last_heartbeat_time = time.perf_counter()
        self._is_fail_safe_active = False
        
        # Callbacks for state transitions
        self._on_fallback_activate: Optional[Callable[[], None]] = None
        self._on_fallback_deactivate: Optional[Callable[[], None]] = None

        # --- Flapping Detection ---
        self._consecutive_triggers = 0
        self._total_triggers = 0
        self._total_recoveries = 0
        self._FLAPPING_THRESHOLD = 5  # Triggers within short succession = systemic issue

        logger.info(f"Watchdog Logic initialized with {timeout_ms}ms timeout threshold.")

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
            f"WATCHDOG TRIGGERED: Synapse silence detected ({elapsed_time*1000:.1f}ms > "
            f"{self._timeout_seconds*1000:.0f}ms). "
            f"Switching to FIXED-TIME mode. "
            f"[triggers: {self._consecutive_triggers} consecutive, {self._total_triggers} total]"
        )
        
        # Flapping detection: if we keep triggering and recovering rapidly, something is wrong
        if self._consecutive_triggers >= self._FLAPPING_THRESHOLD:
            logger.critical(
                f"WATCHDOG FLAPPING DETECTED: {self._consecutive_triggers} consecutive triggers. "
                f"This indicates a SYSTEMIC latency issue, not a transient glitch. "
                f"Check HFT diagnostics log at logs/hft/hft_diagnostics.log."
            )
        
        if self._on_fallback_activate:
            try:
                self._on_fallback_activate()
            except Exception as e:
                logger.error(f"Error executing Watchdog activation callback: {e}")

    def _recover_system(self):
        self._is_fail_safe_active = False
        self._total_recoveries += 1
        
        logger.info(
            f"WATCHDOG RECOVERY: Signal restored. Resuming Neural Network control. "
            f"[was {self._consecutive_triggers} consecutive trigger(s)]"
        )
        
        # Reset consecutive counter on recovery
        self._consecutive_triggers = 0
        
        if self._on_fallback_deactivate:
            try:
                self._on_fallback_deactivate()
            except Exception as e:
                logger.error(f"Error executing Watchdog deactivation callback: {e}")

    @property
    def is_in_failsafe(self) -> bool:
        return self._is_fail_safe_active


# --- ENTRY POINT FOR MULTIPROCESSING ---

def run_watchdog(com_queue: Queue, locale_manager):
    """
    Process entry point for the Watchdog system.
    
    Args:
        com_queue (Queue): Queue to receive 'HEARTBEAT' signals and potentially send status updates.
        locale_manager: Instance of locale manager (passed from main, though we might rely on logs mostly).
    """
    # 1. Setup Logging for this process
    log_base_dir = get_base_output_dir()
    log_dir = os.path.join(log_base_dir, "logs", "watchdog")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)
    
    logger.info("--- Watchdog Process Started ---")

    # 2. Load Settings to get Timeout
    settings = configparser.ConfigParser()
    settings_path = resource_path(os.path.join("config", "settings.ini"))
    timeout_ms = 300 # Default: 300ms as per CARINA real-time safety requirement
    
    try:
        if os.path.exists(settings_path):
            settings.read(settings_path, encoding='utf-8')
            # Read from [WATCHDOG] heartbeat_timeout_seconds (which is in seconds in ini, convert to ms)
            timeout_sec = settings.getfloat('WATCHDOG', 'heartbeat_timeout_seconds', fallback=0.30)
            timeout_ms = int(timeout_sec * 1000)
            logger.info(f"Loaded timeout from settings: {timeout_ms}ms")
        else:
            logger.warning(f"Settings file not found at {settings_path}. Using default timeout: {timeout_ms}ms")
    except Exception as e:
        logger.error(f"Error reading settings: {e}. Using default timeout.")

    # 3. Initialize Logic
    wd = Watchdog(timeout_ms=timeout_ms)

    # Define Actions (Defense-in-depth: log critical events for audit trail)
    # NOTE: We no longer put FAILSAFE/RECOVERY on com_queue because that is the SAME
    # queue this process reads HEARTBEAT from. Self-messaging causes noise.
    # The CentralController has its own in-process detection via FailsafeManager.
    def on_failsafe_active():
        logger.critical(
            "[Watchdog] ⚠️  FAILSAFE TRIGGERED — Synapse connection lost. "
            "HWI should activate local fixed-time plans."
        )

    def on_failsafe_recover():
        logger.info(
            "[Watchdog] ✅ RECOVERY — Synapse heartbeat restored. "
            "AI Neural Network may resume control."
        )

    wd.set_callbacks(on_failsafe_active, on_failsafe_recover)

    # 4. Main Loop
    logger.info("Watchdog monitoring loop active. Waiting for Heartbeats...")
    
    while True:
        # Phase 1: Drain ALL pending messages from queue immediately.
        # Uses get_nowait() directly instead of unreliable empty() check.
        # Python docs: "Queue.empty() is not reliable for multiprocessing".
        try:
            while True:
                msg = com_queue.get_nowait()
                
                if msg == "HEARTBEAT":
                    wd.register_heartbeat()
                elif msg == "STOP":
                    logger.info("Stop signal received. Shutting down Watchdog.")
                    return
                elif isinstance(msg, tuple) and msg[0] == "CONFIG_UPDATE":
                    # Future proofing: allow changing timeout on fly
                    pass
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error in Watchdog loop: {e}")

        # Phase 2: Check health AFTER draining all pending heartbeats
        wd.check_system_health()
        
        # Phase 3: Block-wait for next message (replaces sleep).
        # get(timeout=0.01) is both a 10ms sleep AND a message listener,
        # so the watchdog responds to heartbeats faster than sleep+poll.
        try:
            msg = com_queue.get(timeout=0.01)
            if msg == "HEARTBEAT":
                wd.register_heartbeat()
            elif msg == "STOP":
                logger.info("Stop signal received. Shutting down Watchdog.")
                return
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error in Watchdog wait phase: {e}")