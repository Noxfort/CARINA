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

# File: src/sds/dashboard_worker.py (MODIFIED FOR TRANSLATION)
# Author: Gabriel Moraes
# Date: October 2, 2025

import logging
import os
import sys
from multiprocessing import Queue
import configparser
import threading
import time
import psutil

# Adds the 'src' directory to the path to allow imports from other modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sds.dashboard_orchestrator import Orchestrator
from utils.logging_setup import setup_logging
from utils.metrics_manager import MetricsManager
from utils.locale_manager_backend import LocaleManagerBackend

def run_sds_worker(sds_data_queue: Queue, settings: configparser.ConfigParser, ui_command_queue: Queue):
    """
    Entry point for the Simulation Data Service (SDS) process.
    """
    # --- CHANGE 1: Create translator instance for this process ---
    locale_manager = LocaleManagerBackend()
    lm = locale_manager

    def monitor_loop(metrics: MetricsManager, process: psutil.Process, queues: dict, interval: int = 5):
        while True:
            metrics.update_metric('process_cpu_usage_percent', process.cpu_percent())
            metrics.update_metric('process_memory_usage_percent', process.memory_percent())
            metrics.update_metric('sds_data_queue_size', queues['sds_data'].qsize())
            metrics.update_metric('ui_command_queue_size', queues['ui_command'].qsize())
            time.sleep(interval)

    metrics_manager = MetricsManager(process_name="DashboardService", port=8003)
    metrics_manager.register_metric('process_cpu_usage_percent', 'Uso de CPU do processo (%)')
    metrics_manager.register_metric('process_memory_usage_percent', 'Uso de Memória do processo (%)')
    metrics_manager.register_metric('sds_data_queue_size', 'Tamanho da fila de dados da simulação para o SDS')
    metrics_manager.register_metric('ui_command_queue_size', 'Tamanho da fila de comandos da UI para o Controller')

    current_process = psutil.Process()
    monitor_thread = threading.Thread(
        target=monitor_loop,
        args=(metrics_manager, current_process, {'sds_data': sds_data_queue, 'ui_command': ui_command_queue}),
        daemon=True
    )
    monitor_thread.start()

    try:
        from src.utils.paths import get_base_output_dir
        log_dir = os.path.join(get_base_output_dir(), "logs", "sds_worker")
        os.makedirs(log_dir, exist_ok=True)
        setup_logging(log_dir=log_dir)

        # --- CHANGE 2: Move the translator to Orchestrator ---
        orchestrator = Orchestrator(sds_data_queue, settings, ui_command_queue, locale_manager)
        
        orchestrator.run()

    # --- CHANGE 3: Translate the exception and termination logs ---
    except KeyboardInterrupt:
        logging.info(lm.get_string("sds_worker.run.user_interrupt"))
    except Exception as e:
        logging.critical(lm.get_string("sds_worker.run.fatal_error", error=e), exc_info=True)
    finally:
        logging.info(lm.get_string("sds_worker.run.worker_finished"))