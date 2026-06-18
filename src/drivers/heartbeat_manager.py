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

# File: src/drivers/heartbeat_manager.py
# Author: Gabriel Moraes
# Date: 2026-06-16

"""
Background heartbeat thread lifecycle management for failsafe remote control.
Extracts heartbeat loop and thread concerns to satisfy SRP.
"""

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

class HeartbeatManager:
    """
    Manages the background heartbeat thread lifecycle for maintaining failsafe remote control.
    """
    def __init__(self, ip_address: str, port: int, send_pulse_cb: Callable[[], bool], on_loss_cb: Callable[[], None], on_restore_cb: Callable[[], None], interval: float = 2.0):
        self.ip_address = ip_address
        self.port = port
        self.send_pulse_cb = send_pulse_cb
        self.on_loss_cb = on_loss_cb
        self.on_restore_cb = on_restore_cb
        self.heartbeat_interval_seconds = interval

        self._heartbeat_thread = None
        self._stop_heartbeat_event = threading.Event()

    def start(self) -> None:
        """Starts the background heartbeat thread."""
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return

        self._stop_heartbeat_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"Heartbeat-{self.ip_address}"
        )
        self._heartbeat_thread.start()
        logger.info(f"[{self.ip_address}:{self.port}] Heartbeat thread started.")

    def stop(self) -> None:
        """Stops the background heartbeat thread cleanly."""
        if self._heartbeat_thread is not None:
            self._stop_heartbeat_event.set()
            self._heartbeat_thread.join(timeout=3.0)
            self._heartbeat_thread = None
            logger.info(f"[{self.ip_address}:{self.port}] Heartbeat thread stopped.")

    def _heartbeat_loop(self) -> None:
        consecutive_failures = 0
        while not self._stop_heartbeat_event.is_set():
            success = self.send_pulse_cb()
            if not success:
                consecutive_failures += 1
                logger.warning(f"[{self.ip_address}:{self.port}] Heartbeat pulse failed ({consecutive_failures}x).")
                if consecutive_failures == 3:
                    self.on_loss_cb()
            else:
                if consecutive_failures >= 3:
                    self.on_restore_cb()
                consecutive_failures = 0
            
            self._stop_heartbeat_event.wait(self.heartbeat_interval_seconds)
