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

# File: src/utils/process_monitor.py
# Author: Gabriel Moraes
# Date: August 10, 2026

import time
import threading
import logging
from typing import Optional

import psutil
from utils.metrics_manager import MetricsManager


class ProcessMonitor:
    """
    Manages process resource utilization monitoring (CPU, memory) in a background
    daemon thread and registers gauges via MetricsManager.
    """

    @staticmethod
    def start_background_monitor(
        process_name: str = "AI_Process",
        port: int = 8002,
        interval: int = 5
    ) -> MetricsManager:
        """
        Initializes MetricsManager, registers system resource gauges, and starts
        a background daemon thread monitoring CPU and Memory percentages.

        Args:
            process_name (str): Process identifier label for metrics.
            port (int): TCP port for Prometheus HTTP exporter.
            interval (int): Monitoring polling interval in seconds.

        Returns:
            MetricsManager: Configured metrics manager instance.
        """
        metrics_manager = MetricsManager(process_name=process_name, port=port)
        metrics_manager.register_metric('process_cpu_usage_percent', 'CPU %')
        metrics_manager.register_metric('process_memory_usage_percent', 'Mem %')

        try:
            current_process = psutil.Process()
        except Exception as e:
            logging.warning(f"[PROCESS_MONITOR] Failed to obtain current process handle: {e}")
            return metrics_manager

        def monitor_loop():
            while True:
                try:
                    cpu = current_process.cpu_percent(interval=None)
                    mem = current_process.memory_percent()
                    metrics_manager.update_metric(
                        'process_cpu_usage_percent', cpu if cpu is not None else 0.0
                    )
                    metrics_manager.update_metric('process_memory_usage_percent', mem)
                except Exception as ex:
                    logging.debug(f"[PROCESS_MONITOR] Monitor loop exception: {ex}")
                    break
                time.sleep(interval)

        monitor_thread = threading.Thread(
            target=monitor_loop,
            daemon=True
        )
        monitor_thread.start()
        logging.info(f"[PROCESS_MONITOR] Started background resource monitoring for {process_name}.")
        return metrics_manager
