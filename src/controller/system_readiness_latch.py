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

# File: src/controller/system_readiness_latch.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import logging

class SystemReadinessLatch:
    """
    Manages the two-stage readiness process (UI and Backend).
    Unlocks the AI engine for decision making when both are ready.
    """
    def __init__(self, traffic_frame_processor):
        self.traffic_frame_processor = traffic_frame_processor
        self.is_ui_ready = False
        self.is_backend_ready = False

    def set_ui_ready(self):
        self.is_ui_ready = True
        self.check_system_readiness()

    def set_backend_ready(self):
        self.is_backend_ready = True
        self.check_system_readiness()

    def check_system_readiness(self):
        if self.is_ui_ready and self.is_backend_ready:
            logging.info("✅ [LATCH] Fronte-end and API fully loaded. Unlocking AI Engine for decision making.")
            self.traffic_frame_processor.set_system_ready(True)
        else:
            if not self.is_ui_ready:
                logging.warning("⚠️ [LATCH] AI Engine paused: waiting for Front-End (UI) readiness ('carina_ready'). Frames will be dropped.")
            if not self.is_backend_ready:
                logging.warning("⚠️ [LATCH] AI Engine paused: waiting for Backend components to finish loading.")
