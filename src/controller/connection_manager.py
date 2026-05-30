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
Handles state tracking, bulk import/export, and dynamic intersection discovery.
"""

import csv
import logging
import os
import glob
import gzip
import xml.etree.ElementTree as ET
from typing import List, Dict

from src.drivers.traffic_light_driver import TrafficLightDriver

logger = logging.getLogger(__name__)

class HardwareConnectionManager:
    """
    Centralized manager for all active hardware driver instances.
    Dynamically fetches real Intersection IDs from the deployed map.
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
        Scans the HFT Live Session map folder for the .net.xml.gz file 
        and extracts all valid traffic light intersection IDs.
        """
        from src.utils.paths import get_base_output_dir
        maps_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session", "maps")
        
        search_gz = os.path.join(maps_dir, "*.net.xml.gz")
        search_xml = os.path.join(maps_dir, "*.net.xml")
        
        files = glob.glob(search_gz) + glob.glob(search_xml)
        if not files:
            logger.warning(f"No network map found in {maps_dir}. Intersections list will be empty.")
            return []
            
        target_file = files[0]
        tl_ids = set()
        
        try:
            if target_file.endswith('.gz'):
                with gzip.open(target_file, 'rt', encoding='utf-8') as f:
                    tree = ET.parse(f)
            else:
                with open(target_file, 'r', encoding='utf-8') as f:
                    tree = ET.parse(f)
                    
            root = tree.getroot()
            for tl in root.findall('tlLogic'):
                tl_id = tl.get('id')
                if tl_id:
                    tl_ids.add(tl_id)
                    
            logger.info(f"Discovered {len(tl_ids)} intersections from {os.path.basename(target_file)}.")
            return sorted(list(tl_ids))
            
        except Exception as e:
            logger.error(f"Failed to parse network file {target_file}: {e}")
            return []

    def get_ui_status_list(self) -> List[Dict[str, str]]:
        """
        Builds the status list expected by the HardwareConnectionCard UI.
        Now includes the specific saved IP address for the inline text field.
        """
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

            driver = TrafficLightDriver(
                intersection_id=intersection_id, 
                ip_address=connect_ip, 
                port=connect_port
            )
            
            if driver.is_connected:
                self.active_connections[intersection_id] = driver
                return True
            else:
                return False

    def export_csv_template(self, filepath: str) -> bool:
        """
        Generates a CSV file containing all discovered intersections.
        """
        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Intersection ID", "IP Address"])
                
                for tl_id in self.known_intersections:
                    ip = self.saved_ips.get(tl_id, "")
                    writer.writerow([tl_id, ip])
                    
            logger.info(f"Hardware template exported successfully to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export hardware template: {e}")
            return False

    def import_csv_config(self, filepath: str) -> tuple[int, int]:
        """
        Reads a CSV file, updates internal IPs, and AUTOMATICALLY attempts 
        to connect to all of them (Bulk Connect).
        Returns a tuple: (success_count, total_attempted)
        """
        success_count = 0
        total_attempted = 0
        
        try:
            with open(filepath, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tl_id = row.get("Intersection ID", "").strip()
                    ip = row.get("IP Address", "").strip()
                    
                    if tl_id and ip:
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
            
        except Exception as e:
            logger.error(f"Failed to import and connect hardware configuration: {e}")
            return 0, 0

    def shutdown_all(self) -> None:
        """Safely severs all active hardware connections."""
        logger.info("Shutting down all active hardware connections...")
        for tl_id, driver in self.active_connections.items():
            driver.shutdown()
        self.active_connections.clear()