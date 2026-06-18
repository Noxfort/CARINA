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

# File: ui/handlers/monitor_settings_handler.py
# Author: Gabriel Moraes
# Date: 2026-06-10

class MonitorSettingsHandler:
    """
    SRP: Manages all business logic related to the connection with the external Monitor system.
    """
    def __init__(self, settings_client):
        self.settings_client = settings_client

    def on_monitor_toggle(self, enabled: bool, host: str):
        if self.settings_client and self.settings_client.live_data_provider:
            command = {
                "type": "set_monitor_connection",
                "payload": {"enabled": enabled, "host": host}
            }
            self.settings_client.live_data_provider.send_command_to_backend(command)
