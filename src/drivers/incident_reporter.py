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

# File: src/drivers/incident_reporter.py
# Author: Gabriel Moraes
# Date: 2026-06-16

"""
Publishes hardware incidents and connection state changes to MQTT.
Extracts monitoring and reporting concerns to satisfy SRP.
"""

import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class IncidentReporter:
    """
    Handles publishing traffic signal events and incidents to external systems (e.g. MQTT).
    """
    @staticmethod
    def report(intersection_id: str, level: str, message: str) -> None:
        """Publishes an incident to the Monitor MQTT topic dynamically if enabled."""
        try:
            import paho.mqtt.client as mqtt
            from src.utils.settings_manager import SettingsManager
            
            settings = SettingsManager().load_settings()
            if str(settings.get("monitor_enabled", "False")).lower() == "true":
                host_str = settings.get("monitor_mqtt_host", "localhost")
                host = host_str.split(":")[0] if ":" in host_str else host_str
                port = int(host_str.split(":")[1]) if ":" in host_str else 1883
                
                client = mqtt.Client()
                client.connect(host, port, 2)
                payload = {
                    "category": "HARDWARE",
                    "origin": "Carina-Driver",
                    "level": level,
                    "message": message,
                    "occurred_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                }
                client.publish("noxfort/telemetry/", json.dumps(payload), qos=1)
                client.disconnect()
        except Exception as e:
            logger.error(f"[{intersection_id}] Failed to emit incident: {e}")
