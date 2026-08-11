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

# File: src/launcher/single_instance.py
# Author: Gabriel Moraes
# Date: August 6, 2026

import socket
import sys
import time
import logging
import threading

class SingleInstanceLock:
    """
    Manages single-instance lock via TCP Socket (127.0.0.1:42123).
    Allows triggering a UI restore on an active instance when launching a second one.
    """
    def __init__(self, port: int = 42123, host: str = '127.0.0.1'):
        self.host = host
        self.port = port
        self.server_socket = None
        self.listener_thread = None

    def acquire(self) -> bool:
        """
        Attempts to bind to the single instance port.
        If port binding fails, notifies the active instance to restore UI and returns False.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            return True
        except socket.error:
            # Second instance detected
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.host, self.port))
                s.sendall(b"restore_ui")
                s.close()
            except Exception as e:
                print(f"Error communicating UI restore request: {e}")
            print("Another instance of CARINA is already running! Requesting UI restore...")
            return False

    def start_restore_listener(self, shutdown_requested: threading.Event, restore_requested: threading.Event):
        """
        Launches a background thread listening for UI restore requests from secondary instances.
        """
        def listener_loop():
            while not shutdown_requested.is_set():
                try:
                    self.server_socket.settimeout(1.0)
                    try:
                        conn, addr = self.server_socket.accept()
                    except socket.timeout:
                        continue
                    data = conn.recv(1024)
                    if data == b"restore_ui":
                        logging.info("[SingleInstance] Received UI restore request from another instance.")
                        restore_requested.set()
                    conn.close()
                except Exception as e:
                    if not shutdown_requested.is_set():
                        logging.error(f"[SingleInstance] Error in single instance listener: {e}")
                    time.sleep(0.5)

        self.listener_thread = threading.Thread(
            target=listener_loop,
            name="SingleInstanceListenerThread",
            daemon=True
        )
        self.listener_thread.start()

    def release(self):
        """
        Closes the single instance socket gracefully.
        """
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None
