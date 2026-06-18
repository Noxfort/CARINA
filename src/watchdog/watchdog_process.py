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

# File: src/watchdog/watchdog_process.py
# Author: Gabriel Moraes
# Date: 2026-06-11

import time
import logging
import os
import sys
import configparser
import queue
from multiprocessing import Queue
from watchdog.watchdog_logic import Watchdog

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

logger = logging.getLogger(__name__)

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
