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

# File: src/database/database_worker.py (FIXED FOR CORRECT LOGGING INITIALIZATION)
# Author: Gabriel Moraes
# Date: October 5, 2025

import logging
import os
import sys
from multiprocessing import Queue
import threading
import time
import psutil

# Adds the 'src' directory to the path to allow imports from other modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.logging_setup import setup_logging
from database.database_manager import DatabaseManager
from utils.metrics_manager import MetricsManager
from utils.locale_manager_backend import LocaleManagerBackend

def run_database_worker(db_queue: Queue):
    """
    Entry point for the Database Worker process.
    """
    # --- FIX APPLIED HERE: Boot order has been reversed ---

    # 1. Configure FIRST logging.
    from src.utils.paths import get_base_output_dir
    log_dir = os.path.join(get_base_output_dir(), "logs", "db_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    # 2. With logging active, create the LocaleManager AFTER.
    lm = LocaleManagerBackend()

    # --- END OF CORRECTION ---

    from database.worker_monitor import WorkerMonitor
    monitor = WorkerMonitor(process_name="DatabaseWorker", port=8005, monitered_queues={'db_data': db_queue})
    
    monitor_thread = threading.Thread(
        target=monitor.start_loop,
        args=(5,),
        daemon=True
    )
    monitor_thread.start()

    try:
        # setup_logging has already been moved to the top
        
        db_manager = DatabaseManager(locale_manager=lm)
        
        def cloud_sync_loop(db_mgr, base_dir):
            # Give the system some time to boot before first sync
            time.sleep(30)
            while True:
                try:
                    db_mgr.sync_all_files_to_vault(base_dir)
                except Exception as e:
                    logging.error(f"[CLOUD_SYNC] Error in sync loop: {e}")
                # Wait 5 minutes before next sync
                time.sleep(300)
                
        cloud_sync_thread = threading.Thread(
            target=cloud_sync_loop,
            args=(db_manager, get_base_output_dir()),
            daemon=True
        )
        cloud_sync_thread.start()
        
        logging.info(lm.get_string("db_worker.run.worker_started"))

        while True:
            data_packet = db_queue.get()

            if data_packet is None:
                logging.info(lm.get_string("db_worker.run.shutdown_signal"))
                break

            try:
                log_type = data_packet.get("type")
                payload = data_packet.get("payload", {})

                if log_type == "log_episode":
                    db_manager.log_episode(**payload)
                elif log_type == "log_report":
                    db_manager.log_analysis_report(**payload)
                elif log_type == "sync_files":
                    db_manager.sync_all_files_to_vault(get_base_output_dir())
                else:
                    logging.warning(lm.get_string("db_worker.run.unknown_log_type", type=log_type))

            except Exception as e:
                logging.error(lm.get_string("db_worker.run.processing_error", packet=data_packet), exc_info=e)

    except KeyboardInterrupt:
        logging.info(lm.get_string("db_worker.run.user_interrupt"))
    except Exception as e:
        logging.critical(lm.get_string("db_worker.run.fatal_error", error=e), exc_info=True)
    finally:
        logging.info(lm.get_string("db_worker.run.worker_finished"))