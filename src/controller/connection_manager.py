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
from logging.handlers import RotatingFileHandler
import os
from typing import List, Dict, Optional, Any

from src.utils.logging_setup import gzip_namer, gzip_rotator
from src.drivers.traffic_light_driver import TrafficLightDriver
from src.controller.map_discoverer import MapTopologyDiscoverer
from src.controller.connection_config_repo import ConnectionConfigRepository

# --- Set up dedicated hardware log file ---
from src.utils.paths import get_base_output_dir
log_dir = os.path.join(get_base_output_dir(), "logs")
os.makedirs(log_dir, exist_ok=True)

hw_log_path = os.path.abspath(os.path.join(log_dir, "hardware_connections.log"))
hw_handler = RotatingFileHandler(hw_log_path, maxBytes=10 * 1024 * 1024, backupCount=100, encoding='utf-8')
hw_handler.namer = gzip_namer
hw_handler.rotator = gzip_rotator
hw_handler.setFormatter(logging.Formatter('%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s'))

logger = logging.getLogger(__name__)
if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == hw_log_path for h in logger.handlers):
    logger.addHandler(hw_handler)

# --- Dedicated Commands Logger ---
cmd_log_path = os.path.abspath(os.path.join(log_dir, "commands.log"))
cmd_logger = logging.getLogger("carina_commands")
cmd_logger.setLevel(logging.INFO)
cmd_logger.propagate = False

if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == cmd_log_path for h in cmd_logger.handlers):
    cmd_handler = RotatingFileHandler(cmd_log_path, maxBytes=10 * 1024 * 1024, backupCount=100, encoding='utf-8')
    cmd_handler.namer = gzip_namer
    cmd_handler.rotator = gzip_rotator
    cmd_handler.setFormatter(logging.Formatter('%(asctime)s - [CARINA_CORE] - %(message)s'))
    cmd_logger.addHandler(cmd_handler)

import src.drivers.traffic_light_driver
if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == hw_log_path for h in src.drivers.traffic_light_driver.logger.handlers):
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
    _active_instance = None

    @classmethod
    def get_instance(cls, locale_manager=None) -> 'HardwareConnectionManager':
        """Singleton accessor to ensure only one HardwareConnectionManager and SnmpTrapListener exist."""
        if cls._active_instance is None:
            cls(locale_manager=locale_manager)
        elif locale_manager and getattr(cls._active_instance, 'locale_manager', None) is None:
            cls._active_instance.locale_manager = locale_manager
        return cls._active_instance

    def __init__(self, locale_manager=None):
        HardwareConnectionManager._active_instance = self
        self.locale_manager = locale_manager
        # Maps intersection_id to its active TrafficLightDriver instance
        self.active_connections: Dict[str, TrafficLightDriver] = {}
        
        # Maps intersection_id to its configured IP Address
        self.saved_ips: Dict[str, str] = {} 

        # Automatically discover the real intersections from the live map
        self.known_intersections = self._discover_intersections()

        # Initialize Active Hardware Event Listener (SNMP Traps)
        from src.drivers.hardware_event_listener import SnmpTrapListener
        self.event_listener = SnmpTrapListener(
            port=162,
            get_intersection_by_ip=self._find_intersection_by_ip,
            is_connected_checker=self.is_intersection_connected
        )
        self.event_listener.start()

        # Load saved hardware connections from DB asynchronously in background thread
        import threading
        t_db_init = threading.Thread(
            target=self._load_and_restore_saved_connections,
            daemon=True,
            name="HWConnectionManager-DBRestore"
        )
        t_db_init.start()

    def _load_and_restore_saved_connections(self):
        """Loads saved connections from Database (PostgreSQL/SQLite) asynchronously and restores active drivers."""
        try:
            db_configs = ConnectionConfigRepository.load_all_connections_db(locale_manager=self.locale_manager)
            if db_configs:
                logger.info(f"[HardwareConnectionManager] Found {len(db_configs)} saved hardware connection(s) in Database. Restoring...")
                for tl_id, ip in db_configs.items():
                    self.saved_ips[tl_id] = ip
                    if tl_id not in self.known_intersections:
                        self.known_intersections.append(tl_id)
                    # Attempt to auto-reconnect in background thread to avoid blocking startup
                    import threading
                    t = threading.Thread(
                        target=self.toggle_connection,
                        args=(tl_id, ip, "connect"),
                        daemon=True,
                        name=f"AutoConnect-{tl_id}"
                    )
                    t.start()
        except Exception as e:
            logger.error(f"[HardwareConnectionManager] Asynchronous DB connection restore error: {e}")

    def _find_intersection_by_ip(self, ip_address: str) -> Optional[str]:
        """Resolves an IP address to a known intersection ID, prioritizing active connections."""
        clean_req_ip = ip_address.split(":")[0] if ":" in ip_address else ip_address

        # 1. Check active connected drivers first (PRIORITY)
        for tl_id, driver_wrapper in self.active_connections.items():
            if getattr(driver_wrapper, "is_connected", False):
                clean_driver_ip = driver_wrapper.ip_address.split(":")[0] if ":" in driver_wrapper.ip_address else driver_wrapper.ip_address
                if clean_req_ip == clean_driver_ip or (clean_req_ip in ["127.0.0.1", "localhost"] and clean_driver_ip in ["127.0.0.1", "localhost"]):
                    return tl_id

        # 2. Check any active driver wrapper
        for tl_id, driver_wrapper in self.active_connections.items():
            clean_driver_ip = driver_wrapper.ip_address.split(":")[0] if ":" in driver_wrapper.ip_address else driver_wrapper.ip_address
            if clean_req_ip == clean_driver_ip:
                return tl_id

        # 3. Fallback to saved IPs
        for tl_id, saved_ip in self.saved_ips.items():
            clean_saved = saved_ip.split(":")[0] if ":" in saved_ip else saved_ip
            if clean_req_ip == clean_saved:
                return tl_id

        # 4. Fallback: If only 1 connected intersection exists, resolve to it!
        connected_ids = [tid for tid, drv in self.active_connections.items() if getattr(drv, "is_connected", False)]
        if len(connected_ids) == 1:
            return connected_ids[0]

        return None

    def is_intersection_connected(self, intersection_id: str) -> bool:
        """Returns True if the specified intersection is actively connected."""
        if not intersection_id or intersection_id == "DESCONHECIDO":
            return False
        possible_ids = [intersection_id]
        if str(intersection_id).startswith("tl_"):
            possible_ids.append(str(intersection_id).replace("tl_", ""))
        else:
            possible_ids.append(f"tl_{intersection_id}")

        for pid in possible_ids:
            driver_wrapper = self.active_connections.get(pid)
            if driver_wrapper and getattr(driver_wrapper, "is_connected", False):
                return True
        return False

    def get_hardware_info(self, intersection_id: str) -> Dict[str, Any]:
        """Retrieves manufacturer (brand), model, and connection status for a given intersection."""
        possible_ids = [intersection_id]
        if str(intersection_id).startswith("tl_"):
            possible_ids.append(str(intersection_id).replace("tl_", ""))
        else:
            possible_ids.append(f"tl_{intersection_id}")

        for pid in possible_ids:
            driver_wrapper = self.active_connections.get(pid)
            if driver_wrapper and driver_wrapper.is_connected and driver_wrapper.hardware_driver:
                brand = getattr(driver_wrapper.hardware_driver, "brand", None)
                model = getattr(driver_wrapper.hardware_driver, "model", None)
                return {
                    "is_connected": True,
                    "brand": brand if brand else "Não informado",
                    "model": model if model else "Não informado"
                }
        return {"is_connected": False, "brand": "Desconectado", "model": "Desconectado"}

    @classmethod
    def get_global_hardware_info(cls, intersection_id: str) -> Dict[str, Any]:
        """Global accessor for hardware metadata of connected intersections."""
        if cls._active_instance:
            return cls._active_instance.get_hardware_info(intersection_id)
        return {"is_connected": False, "brand": "Desconectado", "model": "Desconectado"}

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

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

    def toggle_connection(self, intersection_id: str, ip_address: str = None, action: str = "toggle") -> bool:
        """
        Attempts to connect using SNMP (Port 161) or safely shuts down.
        If ip_address is provided, updates the internal record before connecting.
        'action' parameter can be 'connect', 'disconnect', or 'toggle'.
        """
        is_currently_connected = intersection_id in self.active_connections and self.active_connections[intersection_id].is_connected

        if action == "disconnect" or (action == "toggle" and is_currently_connected):
            # Action: Disconnect
            logger.info(self._get_string("connection_manager.hw_manager.disconnecting", default="[{id}] Disconnecting hardware control...", id=intersection_id))
            
            possible_ids = [intersection_id]
            if str(intersection_id).startswith("tl_"):
                possible_ids.append(str(intersection_id).replace("tl_", ""))
            else:
                possible_ids.append(f"tl_{intersection_id}")

            for pid in possible_ids:
                if pid in self.active_connections:
                    try:
                        self.active_connections[pid].shutdown()
                    except Exception as e:
                        logger.warning(f"Error shutting down driver for {pid}: {e}")
                    del self.active_connections[pid]
                ConnectionConfigRepository.remove_connection_db(pid, self.locale_manager)

            return False
            
        elif action == "connect" or (action == "toggle" and not is_currently_connected):
            # Action: Connect
            # Update the saved IP if the user typed a new one in the UI
            if ip_address:
                self.saved_ips[intersection_id] = ip_address.strip()
                
            target_ip = self.saved_ips.get(intersection_id)
            if not target_ip:
                logger.error(self._get_string("connection_manager.hw_manager.no_ip_error", default="[{id}] Cannot connect: No IP address provided.", id=intersection_id))
                ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
                return False

            # Robust extraction: find the first valid IPv4 address (and optional port)
            # from any input format, even if garbage text was pasted into the field.
            import re
            import ipaddress as ipmod
            
            ip_port_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d{1,5}))?', target_ip)
            
            if not ip_port_match:
                logger.error(self._get_string("connection_manager.hw_manager.invalid_ip_format", default="[{id}] Invalid IP address: no valid IPv4 found in input.", id=intersection_id))
                ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
                return False
            
            connect_ip = ip_port_match.group(1)
            connect_port = int(ip_port_match.group(2)) if ip_port_match.group(2) else 161
            
            # Final validation: ensure octets are within 0-255
            try:
                ipmod.ip_address(connect_ip)
            except ValueError:
                logger.error(self._get_string("connection_manager.hw_manager.invalid_ip_range", default="[{id}] Invalid IP address: '{ip}' is not a valid IPv4.", id=intersection_id, ip=connect_ip))
                ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
                return False

            # Update saved_ips with the clean value so the UI shows the correct IP
            clean_saved = f"{connect_ip}:{connect_port}" if connect_port != 161 else connect_ip
            self.saved_ips[intersection_id] = clean_saved

            logger.info(self._get_string("connection_manager.hw_manager.connecting", default="[{id}] Attempting to connect hardware at IP {ip} (Port {port})...", id=intersection_id, ip=connect_ip, port=connect_port))

            # Parse green stages list dynamically from the map topology discoverer
            green_stages = self.get_green_stages_for_intersection(intersection_id)

            driver = TrafficLightDriver(
                intersection_id=intersection_id, 
                ip_address=connect_ip, 
                port=connect_port,
                green_stages=green_stages,
                locale_manager=self.locale_manager
            )
            
            if driver.is_connected:
                self.active_connections[intersection_id] = driver
                # Save connection to Database (PostgreSQL / SQLite) for auto-restoration on next startup
                ConnectionConfigRepository.save_connection_db(intersection_id, clean_saved, self.locale_manager)
                return True
            else:
                # Deactivate auto_connect in Database on failure so restarts don't keep retrying
                ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
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
            logger.info(self._get_string("connection_manager.hw_manager.bulk_testing", default="[Bulk Import] Testing connection for {id} at {ip}...", id=tl_id, ip=ip))
            
            # Disconnect if already connected before testing new IP
            if tl_id in self.active_connections:
                self.active_connections[tl_id].shutdown()
                del self.active_connections[tl_id]
                
            is_connected = self.toggle_connection(tl_id, ip)
            if is_connected:
                success_count += 1
                
        logger.info(self._get_string("connection_manager.hw_manager.bulk_finished", default="Bulk connection finished: {success}/{total} connected successfully.", success=success_count, total=total_attempted))
        return success_count, total_attempted

    def shutdown_all(self) -> None:
        """Safely severs all active hardware connections."""
        logger.info(self._get_string("connection_manager.hw_manager.shutdown_all", default="Shutting down all active hardware connections..."))
        if hasattr(self, 'event_listener') and self.event_listener:
            self.event_listener.stop()
        for tl_id, driver in self.active_connections.items():
            driver.shutdown()
        self.active_connections.clear()