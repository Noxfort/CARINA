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

# File: src/controller/connection_manager.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
Manages the hardware connections between CARINA's logical logic and 
the physical traffic light controllers (via SNMP NTCIP/UTMC2).
Acts as a clean orchestrator delegate, delegating map parsing and 
CSV serialization to separate utility classes to satisfy SRP and OCP.
"""

import logging
import os
from typing import List, Dict

from src.drivers.traffic_light_driver import TrafficLightDriver
from src.controller.map_discoverer import MapTopologyDiscoverer
from src.controller.connection_config_repo import ConnectionConfigRepository

# --- Set up dedicated hardware log file ---
from src.utils.paths import get_base_output_dir
log_dir = os.path.join(get_base_output_dir(), "logs")
os.makedirs(log_dir, exist_ok=True)

hw_log_path = os.path.abspath(os.path.join(log_dir, "hardware_connections.log"))
hw_handler = logging.FileHandler(hw_log_path, encoding='utf-8')
hw_handler.setFormatter(logging.Formatter('%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s'))

logger = logging.getLogger(__name__)
if not any(isinstance(h, logging.FileHandler) and h.baseFilename == hw_log_path for h in logger.handlers):
    logger.addHandler(hw_handler)

# --- Dedicated Commands Logger ---
cmd_log_path = os.path.abspath(os.path.join(log_dir, "commands.log"))
cmd_logger = logging.getLogger("carina_commands")
cmd_logger.setLevel(logging.INFO)
cmd_logger.propagate = False

if not any(isinstance(h, logging.FileHandler) and h.baseFilename == cmd_log_path for h in cmd_logger.handlers):
    cmd_handler = logging.FileHandler(cmd_log_path, encoding='utf-8')
    cmd_handler.setFormatter(logging.Formatter('%(asctime)s - [CARINA_CORE] - %(message)s'))
    cmd_logger.addHandler(cmd_handler)

import src.drivers.traffic_light_driver
if not any(isinstance(h, logging.FileHandler) and h.baseFilename == hw_log_path for h in src.drivers.traffic_light_driver.logger.handlers):
    src.drivers.traffic_light_driver.logger.addHandler(hw_handler)
src.drivers.traffic_light_driver.cmd_logger = cmd_logger

import src.drivers.driver_factory
if not any(isinstance(h, logging.FileHandler) and h.baseFilename == hw_log_path for h in src.drivers.driver_factory.logger.handlers):
    src.drivers.driver_factory.logger.addHandler(hw_handler)
# -----------------------------------------------

class HardwareConnectionManager:
    """
    Centralized manager for all active hardware driver instances.
    Delegates discovery and CSV persistence to MapTopologyDiscoverer and ConnectionConfigRepository.
    """

    def __init__(self):
        # Maps intersection_id to its active TrafficLightDriver instance
        self.active_connections: Dict[str, TrafficLightDriver] = {}
        
        # Maps intersection_id to its configured IP Address
        self.saved_ips: Dict[str, str] = {} 

        # Automatically discover the real intersections from the live map
        self.known_intersections = self._discover_intersections()

    def _discover_intersections(self) -> List[str]:
        """
        Delegates map scanning and parsing to MapTopologyDiscoverer.
        """
        return MapTopologyDiscoverer.discover_intersections()

    def get_green_stages_for_intersection(self, intersection_id: str) -> List[int]:
        """
        Delegates phase parsing to MapTopologyDiscoverer.
        """
        return MapTopologyDiscoverer.get_green_stages(intersection_id)

    def get_ui_status_list(self) -> List[Dict[str, str]]:
        """
        Builds the status list expected by the HardwareConnectionCard UI.
        Now includes the specific saved IP address for the inline text field.
        """
        # Dynamically refresh known intersections
        current_intersections = self._discover_intersections()
        for tl_id in current_intersections:
            if tl_id not in self.known_intersections:
                self.known_intersections.append(tl_id)
        self.known_intersections = sorted(self.known_intersections)

        ui_data = []
        for tl_id in self.known_intersections:
            if tl_id in self.active_connections and self.active_connections[tl_id].is_connected:
                driver_instance = self.active_connections[tl_id].hardware_driver
                status = driver_instance.get_protocol_name() if driver_instance else "online"
            else:
                status = "disconnected"
            
            ui_data.append({
                "agent_id": tl_id, 
                "ip_address": self.saved_ips.get(tl_id, ""),
                "status": status
            })
            
        return ui_data

    def toggle_connection(self, intersection_id: str, ip_address: str = None) -> bool:
        """
        Attempts to connect using SNMP (Port 161) or safely shuts down.
        If ip_address is provided, updates the internal record before connecting.
        """
        if intersection_id in self.active_connections and self.active_connections[intersection_id].is_connected:
            # Action: Disconnect
            logger.info(f"[{intersection_id}] Disconnecting hardware control...")
            self.active_connections[intersection_id].shutdown()
            del self.active_connections[intersection_id]
            return False
            
        else:
            # Action: Connect
            # Update the saved IP if the user typed a new one in the UI
            if ip_address:
                self.saved_ips[intersection_id] = ip_address.strip()
                
            target_ip = self.saved_ips.get(intersection_id)
            if not target_ip:
                logger.error(f"[{intersection_id}] Cannot connect: No IP address provided.")
                return False

            # Robust extraction: find the first valid IPv4 address (and optional port)
            # from any input format, even if garbage text was pasted into the field.
            import re
            import ipaddress as ipmod
            
            ip_port_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d{1,5}))?', target_ip)
            
            if not ip_port_match:
                logger.error(f"[{intersection_id}] Invalid IP address: no valid IPv4 found in input.")
                return False
            
            connect_ip = ip_port_match.group(1)
            connect_port = int(ip_port_match.group(2)) if ip_port_match.group(2) else 161
            
            # Final validation: ensure octets are within 0-255
            try:
                ipmod.ip_address(connect_ip)
            except ValueError:
                logger.error(f"[{intersection_id}] Invalid IP address: '{connect_ip}' is not a valid IPv4.")
                return False

            # Update saved_ips with the clean value so the UI shows the correct IP
            self.saved_ips[intersection_id] = f"{connect_ip}:{connect_port}" if connect_port != 161 else connect_ip

            logger.info(f"[{intersection_id}] Attempting to connect hardware at IP {connect_ip} (Port {connect_port})...")

            # Parse green stages list dynamically from the map topology discoverer
            green_stages = self.get_green_stages_for_intersection(intersection_id)

            driver = TrafficLightDriver(
                intersection_id=intersection_id, 
                ip_address=connect_ip, 
                port=connect_port,
                green_stages=green_stages
            )
            
            if driver.is_connected:
                self.active_connections[intersection_id] = driver
                return True
            else:
                return False

    def export_csv_template(self, filepath: str) -> bool:
        """
        Generates a CSV file template. Delegates to ConnectionConfigRepository.
        """
        return ConnectionConfigRepository.export_csv_template(
            filepath, self.saved_ips, self.known_intersections
        )

    def import_csv_config(self, filepath: str) -> tuple[int, int]:
        """
        Reads a CSV file, updates internal IPs, and AUTOMATICALLY attempts 
        to connect to all of them (Bulk Connect).
        Delegates CSV parsing to ConnectionConfigRepository.
        """
        success_count = 0
        total_attempted = 0
        
        configs = ConnectionConfigRepository.import_csv_config(filepath)
        for tl_id, ip in configs.items():
            self.saved_ips[tl_id] = ip
            if tl_id not in self.known_intersections:
                self.known_intersections.append(tl_id)
                
            # Automatically attempt to connect/ping this intersection
            total_attempted += 1
            logger.info(f"[Bulk Import] Testing connection for {tl_id} at {ip}...")
            
            # Disconnect if already connected before testing new IP
            if tl_id in self.active_connections:
                self.active_connections[tl_id].shutdown()
                del self.active_connections[tl_id]
                
            is_connected = self.toggle_connection(tl_id, ip)
            if is_connected:
                success_count += 1
                
        logger.info(f"Bulk connection finished: {success_count}/{total_attempted} connected successfully.")
        return success_count, total_attempted

    def shutdown_all(self) -> None:
        """Safely severs all active hardware connections."""
        logger.info("Shutting down all active hardware connections...")
        for tl_id, driver in self.active_connections.items():
            driver.shutdown()
        self.active_connections.clear()