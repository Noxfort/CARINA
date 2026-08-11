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

# File: src/communication/hft_diagnostics.py
# Author: Gabriel Moraes
# Date: 2026-06-09

# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
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
#
# File: src/communication/hft_diagnostics.py
# Author: Gabriel Moraes
# Date: 2026-04-17

import logging
import os
from datetime import datetime
from typing import Optional

class HFTDiagnostics:
    """
    Handles logging sub-systems and metrics recording for the HFT Link.
    This class ensures all diagnostic logic is decoupled from the main networking layer.
    """
class HFTDiagnostics:
    """
    Handles logging sub-systems and metrics recording for the HFT Link.
    This class ensures all diagnostic logic is decoupled from the main networking layer.
    """
    def __init__(self, locale_manager=None):
        self.locale_manager = locale_manager
        self.interval_logger = self._setup_interval_logger()
        self.diagnostics_logger = self._setup_diagnostics_logger()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _setup_interval_logger(self) -> Optional[logging.Logger]:
        """
        Configures a specific logger to write ONLY the inter-arrival times
        to 'logs/hft/hft_inter_arrival.log'.
        """
        try:
            from src.utils.paths import get_base_output_dir
            log_dir = os.path.join(get_base_output_dir(), 'logs', 'hft')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'hft_inter_arrival.log')
            
            logger = logging.getLogger('HFT_Interval_Logger')
            logger.setLevel(logging.INFO)
            logger.propagate = False  # Prevent propagation to root logger (console)
            
            if not logger.handlers:
                handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
                formatter = logging.Formatter('%(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            
            return logger
        except Exception as e:
            logging.error(self._get_string("hft_diagnostics.interval_setup_error", default="[HFT] Failed to setup interval logger: {error}", error=e))
            return None

    def _setup_diagnostics_logger(self) -> Optional[logging.Logger]:
        """
        Configures a dedicated logger for HFT pipeline diagnostics.
        Writes to 'logs/hft/hft_diagnostics.log'.
        """
        try:
            from src.utils.paths import get_base_output_dir
            log_dir = os.path.join(get_base_output_dir(), 'logs', 'hft')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'hft_diagnostics.log')
            
            logger = logging.getLogger('HFT_Diagnostics_Logger')
            logger.setLevel(logging.INFO)
            logger.propagate = False
            
            if not logger.handlers:
                handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
                formatter = logging.Formatter('%(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            
            return logger
        except Exception as e:
            logging.error(self._get_string("hft_diagnostics.setup_error", default="[HFT] Failed to setup diagnostics logger: {error}", error=e))
            return None

    def log_recv_delta(self, current_recv_time: float, delta_ms: float, queue_depth: int):
        """Logs the time taken to receive a frame from Synapse along with diagnostics info."""
        if self.interval_logger:
            ts_str = datetime.fromtimestamp(current_recv_time).strftime('%H:%M:%S.%f')[:-3]
            self.interval_logger.info(f"[{ts_str}] Delta: {delta_ms:.2f} ms")
        
        if self.diagnostics_logger:
            ts_str = datetime.fromtimestamp(current_recv_time).strftime('%H:%M:%S.%f')[:-3]
            self.diagnostics_logger.info(f"[{ts_str}] recv_delta={delta_ms:.1f}ms | queue_depth={queue_depth}")
        
        if delta_ms > 300000:
            logging.warning(
                self._get_string("hft_diagnostics.delay_warning", default="[HFT] 🔴 Synapse delivery delay: recv_delta={delta:.1f}ms (>300000ms). The delay is on the SYNAPSE/network side.", delta=delta_ms)
            )

    def log_processing(self, recv_time: float, proc_delta_ms: float, queue_depth: int, backpressure_threshold: int):
        """Logs internal controller processing performance and backpressure warnings."""
        if self.diagnostics_logger:
            ts_str = datetime.fromtimestamp(recv_time).strftime('%H:%M:%S.%f')[:-3]
            self.diagnostics_logger.info(
                f"[{ts_str}] proc_delta={proc_delta_ms:.1f}ms | queue_depth={queue_depth}"
            )
        
        if queue_depth > backpressure_threshold:
            logging.warning(
                self._get_string("hft_diagnostics.backpressure_warning", default="[HFT] ⚠️ Backpressure detected! queue_depth={depth} (>{thresh}). CARINA processing can't keep up.", depth=queue_depth, thresh=backpressure_threshold)
            )
            
        if proc_delta_ms > 100:
            logging.warning(
                self._get_string("hft_diagnostics.slow_processing_warning", default="[HFT] ⏱️ Slow frame processing: {delta:.1f}ms (>100ms threshold). CARINA-side bottleneck.", delta=proc_delta_ms)
            )
