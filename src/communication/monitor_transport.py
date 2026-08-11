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

# File: src/communication/monitor_transport.py
# Author: Gabriel Moraes
# Date: 2026-07-31

"""
MonitorMqttTransport handles lower-level MQTT connection lifecycle,
reconnection, network loop management, and raw message publishing.
"""

import os
import time
import logging
import threading
import paho.mqtt.client as mqtt
from typing import Callable, Optional


def _log_monitor_healthcheck(status_msg: str, is_connected: bool, enabled: bool, host: str = "127.0.0.1", port: int = 1883):
    """Disabled temporary healthcheck file logging."""
    pass


class MonitorMqttTransport:
    """Manages low-level MQTT connection, network loops, and publishing for Monitor integration."""

    def __init__(self, host: str = "localhost", port: int = 1883, on_connect_cb: Optional[Callable] = None):
        self.host = host
        self.port = port
        self.client: Optional[mqtt.Client] = None
        self._is_connected = False
        self.enabled = True
        self._on_connect_user_cb = on_connect_cb

    @staticmethod
    def parse_host_port(host_str: str, default_port: int = 1883) -> tuple[str, int]:
        """Parses host string in format 'host:port' or returns default port."""
        if ":" in host_str:
            parts = host_str.split(":", 1)
            try:
                return parts[0], int(parts[1])
            except ValueError:
                return parts[0], default_port
        return host_str, default_port

    def configure_endpoint(self, host_str: str):
        """Updates host and port from a string representation."""
        self.host, self.port = self.parse_host_port(host_str)

    def setup_mqtt(self):
        """Initializes MQTT client and connects to the broker with a process-unique client ID."""
        try:
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass

            client_id = f"carina_monitor_client_{os.getpid()}"
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            logging.info(f"[{self.__class__.__name__}] Connecting to MQTT Broker at {self.host}:{self.port} (ID: {client_id})")
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Connection attempt to MQTT Broker failed: {e}")
            self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Returns True if MQTT client is active and connected."""
        if not self.enabled or not self.client:
            return False
        try:
            return bool(self.client.is_connected())
        except Exception:
            return False

    def ensure_connected(self) -> bool:
        """Verifies active connection, waiting or re-establishing if necessary."""
        if not self.enabled:
            return False

        if self.is_connected:
            return True

        # Wait up to 1.5s for any background connection to complete
        for _ in range(15):
            if self.is_connected:
                return True
            time.sleep(0.1)

        logging.info(f"[{self.__class__.__name__}] MQTT client disconnected or uninitialized. Re-establishing connection...")
        self.setup_mqtt()

        for _ in range(15):
            if self.is_connected:
                return True
            time.sleep(0.1)

        return self.is_connected

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self._is_connected = True
            logging.info(f"[{self.__class__.__name__}] Connected successfully to MQTT Broker.")
            _log_monitor_healthcheck("MQTT CONNECTED SUCCESS", True, self.enabled, self.host, self.port)
            if self._on_connect_user_cb:
                threading.Thread(target=self._on_connect_user_cb, daemon=True).start()
        else:
            self._is_connected = False
            logging.error(f"[{self.__class__.__name__}] Connection to MQTT failed with result code {reason_code}")
            _log_monitor_healthcheck(f"MQTT CONNECT FAILED (code: {reason_code})", False, self.enabled, self.host, self.port)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        self._is_connected = False
        _log_monitor_healthcheck(f"MQTT DISCONNECTED (code: {reason_code})", False, self.enabled, self.host, self.port)
        if reason_code != 0 and self.enabled:
            logging.warning(f"[{self.__class__.__name__}] Unexpected disconnect from MQTT Broker (code: {reason_code}). Triggering auto-reconnect...")
            threading.Thread(target=self.ensure_connected, daemon=True).start()

    def publish(self, topic: str, payload: str, qos: int = 1, timeout: float = 2.0) -> bool:
        """Publishes a payload to the given topic."""
        if not self.enabled or not self.client or not self.is_connected:
            return False
        try:
            info = self.client.publish(topic, payload, qos=qos)
            info.wait_for_publish(timeout=timeout)
            return True
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Failed to publish to topic {topic}: {e}")
            return False

    def disconnect(self):
        """Stops network loop and disconnects client."""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
        self._is_connected = False
