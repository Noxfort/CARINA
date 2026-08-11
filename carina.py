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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: carina.py (SOLID Orchestrator Edition)
# Author: Gabriel Moraes
# Date: August 6, 2026

import sys
import os
import signal
import atexit
import logging
import multiprocessing
from multiprocessing import set_start_method

# 1. Environment and sys.path setup prior to any project imports
from src.launcher.env_setup import setup_environment
project_root, bundle_root, IS_FROZEN = setup_environment()

from utils.paths import get_base_output_dir
from launcher.single_instance import SingleInstanceLock
from launcher.process_manager import ProcessManager
from launcher.ui_tray_manager import UITrayManager

# Global single instance lock
single_instance_lock = SingleInstanceLock(port=42123)


def setup_launcher_logging():
    """Configures the logging system for the launcher."""
    log_base_dir = get_base_output_dir()
    launcher_log_dir = os.path.join(log_base_dir, "logs", "launcher")
    os.makedirs(launcher_log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [LAUNCHER] %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(launcher_log_dir, "launcher.log"), mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main orchestration function for CARINA."""
    # Process Group isolation on Linux so all child processes share the same PGID
    if sys.platform != 'win32':
        try:
            os.setpgrp()
        except Exception:
            pass

    setup_launcher_logging()
    logging.info("--- CARINA SYSTEM STARTING (HFT - SOLID Architecture) ---")

    process_mgr = ProcessManager()
    ui_mgr = UITrayManager(process_manager=process_mgr, bundle_root=bundle_root)

    # Register emergency cleanup with atexit
    def emergency_cleanup():
        try:
            process_mgr.shutdown_all()
        except Exception:
            pass
        try:
            single_instance_lock.release()
        except Exception:
            pass

    atexit.register(emergency_cleanup)

    # Attach signal handlers for SIGTERM/SIGINT
    def signal_handler(signum, frame):
        logging.info(f"Signal {signum} received. Triggering system shutdown...")
        ui_mgr.shutdown_requested.set()
        process_mgr.shutdown_all()
        single_instance_lock.release()
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    except Exception:
        pass

    # Start listener to restore UI if another instance is triggered
    single_instance_lock.start_restore_listener(
        shutdown_requested=ui_mgr.shutdown_requested,
        restore_requested=ui_mgr.restore_requested
    )

    try:
        # Launch all backend subprocesses
        process_mgr.start_all_backend_services()

        # Run the main UI/Tray loop on the main thread
        ui_mgr.run()

    except KeyboardInterrupt:
        logging.info("Interrupt (Ctrl+C).")
    finally:
        # Execute graceful shutdown and total cleanup
        ui_mgr.shutdown_requested.set()
        process_mgr.shutdown_all()
        single_instance_lock.release()

        # Secondary fallback: terminate any lingering child process tree of launcher
        try:
            import psutil
            current_proc = psutil.Process(os.getpid())
            children = current_proc.children(recursive=True)
            for child in children:
                try:
                    if child.is_running():
                        cmdline = " ".join(child.cmdline()) if hasattr(child, 'cmdline') else ""
                        if "resource_tracker" not in cmdline:
                            child.kill()
                except Exception:
                    pass
        except Exception:
            pass

        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)


if __name__ == "__main__":
    # --- 1. Multiprocessing Protection (Windows/PyInstaller) ---
    multiprocessing.freeze_support()
    try:
        if multiprocessing.get_start_method(allow_none=True) != 'spawn':
            set_start_method('spawn', force=True)
    except Exception as e: 
        print(f"Error setting multiprocessing start method: {e}")

    # --- 2. Single Instance Lock ---
    if not single_instance_lock.acquire():
        sys.exit(0)

    print(f"[LAUNCHER STARTING] Project Root: {project_root}")
    main()