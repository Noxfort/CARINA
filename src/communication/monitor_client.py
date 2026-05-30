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

# File: src/clients/monitor_client.py
# Author: Gabriel Moraes
# Date: 2026-03-03

"""
MonitorClient is responsible for integrating CARINA with the external 'Monitor' 
system via MQTT, publishing Heartbeats and Incident Notifications.
"""

import json
import time
import threading
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from typing import Dict, Any

from utils.settings_manager import SettingsManager

class MonitorClient:
    def __init__(self, settings_manager: SettingsManager):
        self.settings = settings_manager.load_settings()
        self.enabled = str(self.settings.get("monitor_enabled", "False")).lower() == "true"
        
        host_str = self.settings.get("monitor_mqtt_host", "localhost")
        self.port = 1883
        if ":" in host_str:
            parts = host_str.split(":", 1)
            self.host = parts[0]
            try:
                self.port = int(parts[1])
            except ValueError:
                pass
        else:
            self.host = host_str
            
        self.topic_telemetry = "noxfort/telemetry/"
        
        self.client = None
        self._running = False
        self._heartbeat_thread = None
        self._heartbeat_interval = 30 # seconds

        if self.enabled:
            self._setup_mqtt()
            self.start()

    def _setup_mqtt(self):
        """Initializes the MQTT client and connects to the broker."""
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="carina_monitor_client")
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            logging.info(f"[{self.__class__.__name__}] Connecting to MQTT Broker at {self.host}:{self.port}")
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start() # Run the network loop in the background
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Failed to connect to MQTT Broker: {e}")
            self.enabled = False # Disable if connection fails internally

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logging.info(f"[{self.__class__.__name__}] Connected successfully to MQTT Broker.")
        else:
            logging.error(f"[{self.__class__.__name__}] Connection to MQTT failed with result code {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        if reason_code != 0:
            logging.warning(f"[{self.__class__.__name__}] Unexpected disconnection from MQTT Broker.")

    def _create_payload(self, category: str, level: str, message: str) -> str:
        """Constructs the strict JSON payload expected by the Monitor."""
        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        payload = {
            "category": category, # HARDWARE or SOFTWARE
            "origin": "Carina",
            "level": level, # INFO, WARNING, or CRITICAL
            "message": str(message),
            "occurred_at": current_time
        }
        return json.dumps(payload)

    def start(self):
        """Starts the periodic heartbeat loop."""
        if not self.enabled or not self.client:
            return

        self._running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logging.info(f"[{self.__class__.__name__}] Heartbeat loop started (Interval: {self._heartbeat_interval}s)")

    def stop(self, shutdown_message: str = None):
        """
        Stops the heartbeat loop and disconnects from MQTT.
        
        Args:
            shutdown_message: Optional message to send as a final incident report before disconnecting.
        """
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
            
        if shutdown_message and self.enabled and self.client:
            try:
                self.report_incident(
                    category="SOFTWARE",
                    level="INFO",
                    message=shutdown_message
                )
                # Give MQTT a brief moment to flush the QoS 1 packet
                time.sleep(0.5)
            except Exception as e:
                logging.error(f"[{self.__class__.__name__}] Failed to send shutdown message: {e}")
        
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass

    def connect_manual(self, host_str: str):
        """Called by the UI to force a new live connection."""
        self.stop()
        
        self.enabled = True
        self.port = 1883
        if ":" in host_str:
            parts = host_str.split(":", 1)
            self.host = parts[0]
            try:
                self.port = int(parts[1])
            except ValueError:
                pass
        else:
            self.host = host_str
            
        self._setup_mqtt()
        self.start()

    def disconnect_manual(self):
        """Called by the UI to explicitly disconnect immediately."""
        self.enabled = False
        self.stop(shutdown_message="Operator explicitly disconnected CARINA from Monitor.")

    def _heartbeat_loop(self):
        """Periodically publishes the heartbeat message."""
        while self._running:
            self.send_instant_heartbeat()
            # Wait for the interval, checking running state periodically to allow quick shutdown
            for _ in range(self._heartbeat_interval):
                if not self._running:
                    break
                time.sleep(1)

    def send_instant_heartbeat(self):
        """Sends the strict heartbeat JSON payload."""
        if not self.enabled or not self.client:
            return
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            payload = {
                "origin": "Carina",
                "level": "info",
                "message": "heartbeat",
                "timestamp": current_time
            }
            self.client.publish(self.topic_telemetry, json.dumps(payload), qos=0)
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Failed to send heartbeat: {e}")

    def report_incident(self, category: str, level: str, message: str):
        """
        Immediately publishes an incident notification.
        
        Args:
            category (str): "HARDWARE" or "SOFTWARE"
            level (str): "WARNING" or "CRITICAL" (or "INFO")
            message (str): Descriptive text of the error.
        """
        if not self.enabled or not self.client:
            return

        try:
            # Enforce constraints
            category = category.upper() if category.upper() in ["HARDWARE", "SOFTWARE"] else "SOFTWARE"
            level = level.upper() if level.upper() in ["INFO", "WARNING", "CRITICAL"] else "CRITICAL"
            
            payload = self._create_payload(category, level, message)
            
            # Send incident with QoS 1 to guarantee delivery at least once
            info = self.client.publish(self.topic_telemetry, payload, qos=1)
            info.wait_for_publish()
            logging.info(f"[{self.__class__.__name__}] Sent Incident ({level}): {message}")
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Failed to send incident report: {e}")
