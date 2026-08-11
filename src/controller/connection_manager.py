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
Manages hardware connections between CARINA logic and physical traffic light controllers.
Acts as a pure orchestrator, delegating logging setup, IP resolution, connection operations,
topology discovery, and repository persistence to specialized modules to comply with SOLID.
"""

from typing import List, Dict, Optional, Any, Tuple

from src.utils.hardware_logging_setup import setup_hardware_loggers
from src.drivers.traffic_light_driver import TrafficLightDriver
from src.controller.map_discoverer import MapTopologyDiscoverer
from src.controller.connection_config_repo import ConnectionConfigRepository
from src.controller.intersection_resolver import IntersectionResolver
from src.controller.connection_operation_handler import ConnectionOperationHandler
from src.drivers.hardware_event_listener import SnmpTrapListener

# Initialize dedicated hardware and command loggers
logger, cmd_logger = setup_hardware_loggers()


class HardwareConnectionManager:
    """
    Centralized orchestrator for active hardware driver instances.
    Delegates discovery, IP resolution, connection handling, and CSV/DB persistence to specialized services.
    """
    _active_instance = None

    @classmethod
    def get_instance(cls, locale_manager=None) -> 'HardwareConnectionManager':
        """Singleton accessor to ensure a single HardwareConnectionManager and SnmpTrapListener instance."""
        if cls._active_instance is None:
            cls(locale_manager=locale_manager)
        elif locale_manager and getattr(cls._active_instance, 'locale_manager', None) is None:
            cls._active_instance.locale_manager = locale_manager
        return cls._active_instance

    def __init__(self, locale_manager=None):
        HardwareConnectionManager._active_instance = self
        self.locale_manager = locale_manager
        self.active_connections: Dict[str, TrafficLightDriver] = {}
        self.saved_ips: Dict[str, str] = {}

        self.resolver = IntersectionResolver(self.active_connections, self.saved_ips)
        self.op_handler = ConnectionOperationHandler(
            self.active_connections, self.saved_ips, locale_manager=self.locale_manager
        )

        self.known_intersections = self._discover_intersections()

        # Initialize Active Hardware Event Listener (SNMP Traps on UDP 162)
        self.event_listener = SnmpTrapListener(
            port=162,
            get_intersection_by_ip=self.resolver.find_intersection_by_ip,
            is_connected_checker=self.resolver.is_intersection_connected
        )
        self.event_listener.start()

        # Restore saved connections asynchronously from Database
        self._load_and_restore_saved_connections()

    def _load_and_restore_saved_connections(self) -> None:
        """Alias for backward compatibility with test suites patching this method."""
        self.op_handler.restore_saved_connections_async(
            self.known_intersections, toggle_func=self.toggle_connection
        )

    def is_intersection_connected(self, intersection_id: str) -> bool:
        """Delegates connection status check to IntersectionResolver."""
        return self.resolver.is_intersection_connected(intersection_id)

    def get_hardware_info(self, intersection_id: str) -> Dict[str, Any]:
        """Delegates hardware metadata extraction to IntersectionResolver."""
        return self.resolver.get_hardware_info(intersection_id)

    @classmethod
    def get_global_hardware_info(cls, intersection_id: str) -> Dict[str, Any]:
        """Global accessor for hardware metadata of connected intersections."""
        if cls._active_instance:
            return cls._active_instance.get_hardware_info(intersection_id)
        return {"is_connected": False, "brand": "Desconectado", "model": "Desconectado"}

    def _discover_intersections(self) -> List[str]:
        """Delegates map scanning and parsing to MapTopologyDiscoverer."""
        return MapTopologyDiscoverer.discover_intersections()

    def get_green_stages_for_intersection(self, intersection_id: str) -> List[int]:
        """Delegates phase parsing to MapTopologyDiscoverer."""
        return MapTopologyDiscoverer.get_green_stages(intersection_id)

    def get_ui_status_list(self) -> List[Dict[str, str]]:
        """Builds status list expected by HardwareConnectionCard UI."""
        current_intersections = self._discover_intersections()
        for tl_id in current_intersections:
            if tl_id not in self.known_intersections:
                self.known_intersections.append(tl_id)
        self.known_intersections = sorted(self.known_intersections)

        ui_data = []
        for tl_id in self.known_intersections:
            if tl_id in self.active_connections and getattr(self.active_connections[tl_id], "is_connected", False):
                driver_instance = getattr(self.active_connections[tl_id], "hardware_driver", None)
                status = driver_instance.get_protocol_name() if driver_instance and hasattr(driver_instance, "get_protocol_name") else "online"
            else:
                status = "disconnected"

            ui_data.append({
                "agent_id": tl_id,
                "ip_address": self.saved_ips.get(tl_id, ""),
                "status": status
            })

        return ui_data

    def toggle_connection(self, intersection_id: str, ip_address: str = None, action: str = "toggle") -> bool:
        """Delegates connection toggle operations to ConnectionOperationHandler."""
        return self.op_handler.toggle_connection(
            intersection_id=intersection_id,
            ip_address=ip_address,
            action=action,
            green_stages_provider=self.get_green_stages_for_intersection
        )

    def export_csv_template(self, filepath: str) -> bool:
        """Delegates CSV template creation to ConnectionConfigRepository."""
        return ConnectionConfigRepository.export_csv_template(
            filepath, self.saved_ips, self.known_intersections
        )

    def import_csv_config(self, filepath: str) -> Tuple[int, int]:
        """Delegates CSV parsing and bulk connection to ConnectionOperationHandler."""
        return self.op_handler.import_csv_and_bulk_connect(
            filepath=filepath,
            known_intersections=self.known_intersections,
            toggle_func=self.toggle_connection
        )

    def shutdown_all(self) -> None:
        """Safely severs all active hardware connections and stops event listener."""
        if hasattr(self, 'event_listener') and self.event_listener:
            self.event_listener.stop()
        self.op_handler.shutdown_all_connections()