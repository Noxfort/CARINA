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

# File: ui/handlers/account_settings_handler.py
# Author: Gabriel Moraes
# Date: 2026-06-10

class AccountSettingsHandler:
    """
    SRP: Manages all Authentication and Accounts business logic, delegating
    actions to the real-time data provider.
    """
    def __init__(self, settings_client):
        self.settings_client = settings_client

    def on_add_user(self, username, password, role):
        if self.settings_client and self.settings_client.live_data_provider:
            self.settings_client.live_data_provider.send_command_to_backend({
                "type": "add_user",
                "payload": {"username": username, "password": password, "role": role}
            })

    def on_remove_user(self, username):
        if self.settings_client and self.settings_client.live_data_provider:
            self.settings_client.live_data_provider.send_command_to_backend({
                "type": "remove_user",
                "payload": {"username": username}
            })

    def on_request_users_list(self):
        if self.settings_client and self.settings_client.live_data_provider:
            self.settings_client.live_data_provider.send_command_to_backend({
                "type": "list_users"
            })
