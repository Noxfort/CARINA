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

# File: ui/managers/override_state_manager.py
# Author: Gabriel Moraes
# Date: June 13, 2026

import queue
from typing import Dict, Tuple

class OverrideStateManager:
    """
    Responsible for managing manual command queues and tracking the override
    state for map elements (streets and traffic lights).
    """
    def __init__(self):
        self.command_queue = queue.Queue()
        self.semaphore_overrides: Dict[str, str] = {}
        self.street_overrides: Dict[str, str] = {}
        
    def enqueue_command(self, command: dict):
        self.command_queue.put(command)
        
    def process_queue(self):
        """Empties the queue and updates the override dictionaries."""
        while not self.command_queue.empty():
            try:
                cmd = self.command_queue.get_nowait()
                cmd_type = cmd.get("type", "semaphore")
                cmd_id = cmd.get("id")
                cmd_state = cmd.get("state")
                
                if cmd_type == "street":
                    if cmd_state == "NORMAL":
                        self.street_overrides.pop(cmd_id, None)
                    else:
                        self.street_overrides[cmd_id] = cmd_state
                else:
                    if cmd_state == "NORMAL":
                        self.semaphore_overrides.pop(cmd_id, None)
                    else:
                        self.semaphore_overrides[cmd_id] = cmd_state
            except queue.Empty:
                break

    def get_semaphore_overrides(self) -> Dict[str, str]:
        return self.semaphore_overrides

    def get_street_overrides(self) -> Dict[str, str]:
        return self.street_overrides
