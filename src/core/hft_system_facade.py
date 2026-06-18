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

# File: src/core/hft_system_facade.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import logging

class HftSystemFacade:
    """
    SRP/OCP: Facade to expose only the strictly necessary system functions to the external HFT Server.
    Prevents the gRPC server from being tightly coupled to the CentralController god-class.
    """
    def __init__(self, topology_manager, topology_recorder_bridge, telemetry_aggregator, watchdog_queue, ui_command_queue, traffic_frame_processor, failsafe_manager=None):
        self.topology_manager = topology_manager
        self.topology_recorder_bridge = topology_recorder_bridge
        self.telemetry_aggregator = telemetry_aggregator
        self.watchdog_queue = watchdog_queue
        self.ui_command_queue = ui_command_queue
        self.traffic_frame_processor = traffic_frame_processor
        self.failsafe_manager = failsafe_manager

    def handle_new_map(self, map_path: str, maps_output_dir: str):
        self.topology_manager.handle_new_map(map_path, maps_output_dir, self.telemetry_aggregator)
        self.topology_recorder_bridge.update_recorder_topology(map_path)

    def start_ai_session(self):
        logging.info("AI Session started.")

    def stop_ai_session(self):
        logging.info("AI Session stopped.")

    def process_traffic_frame(self, frame):
        self.traffic_frame_processor.process_traffic_frame(frame)
