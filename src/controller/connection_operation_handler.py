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

# File: src/controller/connection_operation_handler.py
# Author: Gabriel Moraes
# Date: August 10, 2026

import logging
import threading
from typing import Dict, Any, List, Tuple, Callable

from src.utils.network_address_parser import NetworkAddressParser
from src.drivers.traffic_light_driver import TrafficLightDriver
from src.controller.connection_config_repo import ConnectionConfigRepository

logger = logging.getLogger("src.controller.connection_manager")


class ConnectionOperationHandler:
    """
    Handles hardware driver connection lifecycle (connect, disconnect, toggle, bulk import)
    and synchronizes settings with ConnectionConfigRepository.
    """

    def __init__(self, active_connections: Dict[str, Any], saved_ips: Dict[str, str], locale_manager: Any = None):
        self.active_connections = active_connections
        self.saved_ips = saved_ips
        self.locale_manager = locale_manager

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def restore_saved_connections_async(self, known_intersections: List[str], toggle_func: Callable[..., bool]) -> None:
        """
        Loads saved hardware connections from DB asynchronously in a background daemon thread.

        Args:
            known_intersections (List[str]): Shared list of known intersection IDs.
            toggle_func (Callable): Function reference to toggle_connection.
        """
        def _bg_restore():
            try:
                db_configs = ConnectionConfigRepository.load_all_connections_db(locale_manager=self.locale_manager)
                if db_configs:
                    logger.info(f"[HardwareConnectionManager] Found {len(db_configs)} saved hardware connection(s) in Database. Restoring...")
                    for tl_id, ip in db_configs.items():
                        self.saved_ips[tl_id] = ip
                        if tl_id not in known_intersections:
                            known_intersections.append(tl_id)

                        t = threading.Thread(
                            target=toggle_func,
                            args=(tl_id, ip, "connect"),
                            daemon=True,
                            name=f"AutoConnect-{tl_id}"
                        )
                        t.start()
            except Exception as e:
                logger.error(f"[HardwareConnectionManager] Asynchronous DB connection restore error: {e}")

        t_db_init = threading.Thread(
            target=_bg_restore,
            daemon=True,
            name="HWConnectionManager-DBRestore"
        )
        t_db_init.start()

    def toggle_connection(
        self,
        intersection_id: str,
        ip_address: str = None,
        action: str = "toggle",
        green_stages_provider: Callable[[str], List[int]] = None
    ) -> bool:
        """
        Attempts to connect via SNMP or safely shuts down driver for target intersection.

        Args:
            intersection_id (str): Target junction ID.
            ip_address (str): Target IP address string.
            action (str): Operation type ('connect', 'disconnect', or 'toggle').
            green_stages_provider (Callable): Function providing green stage lists for junction.

        Returns:
            bool: Connection success state.
        """
        is_currently_connected = (
            intersection_id in self.active_connections and
            getattr(self.active_connections[intersection_id], "is_connected", False)
        )

        if action == "disconnect" or (action == "toggle" and is_currently_connected):
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
            if ip_address:
                self.saved_ips[intersection_id] = ip_address.strip()

            target_ip = self.saved_ips.get(intersection_id)
            if not target_ip:
                logger.error(self._get_string("connection_manager.hw_manager.no_ip_error", default="[{id}] Cannot connect: No IP address provided.", id=intersection_id))
                ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
                return False

            is_valid, connect_ip, connect_port, clean_saved = NetworkAddressParser.parse_and_validate_ip(target_ip)
            if not is_valid:
                logger.error(self._get_string("connection_manager.hw_manager.invalid_ip_format", default="[{id}] Invalid IP address: no valid IPv4 found in input.", id=intersection_id))
                ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
                return False

            self.saved_ips[intersection_id] = clean_saved
            logger.info(self._get_string("connection_manager.hw_manager.connecting", default="[{id}] Attempting to connect hardware at IP {ip} (Port {port})...", id=intersection_id, ip=connect_ip, port=connect_port))

            green_stages = green_stages_provider(intersection_id) if green_stages_provider else []

            driver = TrafficLightDriver(
                intersection_id=intersection_id,
                ip_address=connect_ip,
                port=connect_port,
                green_stages=green_stages,
                locale_manager=self.locale_manager
            )

            if getattr(driver, "is_connected", False):
                self.active_connections[intersection_id] = driver
                ConnectionConfigRepository.save_connection_db(intersection_id, clean_saved, self.locale_manager)
                return True
            else:
                ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
                return False

        return False

    def import_csv_and_bulk_connect(
        self,
        filepath: str,
        known_intersections: List[str],
        toggle_func: Callable[..., bool]
    ) -> Tuple[int, int]:
        """
        Reads CSV file, updates internal IPs, and triggers bulk connection tests.

        Args:
            filepath (str): Path to CSV configuration file.
            known_intersections (List[str]): Shared list of known intersection IDs.
            toggle_func (Callable): Reference to toggle_connection function.

        Returns:
            Tuple[int, int]: (success_count, total_attempted)
        """
        success_count = 0
        total_attempted = 0

        configs = ConnectionConfigRepository.import_csv_config(filepath)
        for tl_id, ip in configs.items():
            self.saved_ips[tl_id] = ip
            if tl_id not in known_intersections:
                known_intersections.append(tl_id)

            total_attempted += 1
            logger.info(self._get_string("connection_manager.hw_manager.bulk_testing", default="[Bulk Import] Testing connection for {id} at {ip}...", id=tl_id, ip=ip))

            if tl_id in self.active_connections:
                try:
                    self.active_connections[tl_id].shutdown()
                except Exception:
                    pass
                del self.active_connections[tl_id]

            is_connected = toggle_func(tl_id, ip, "connect")
            if is_connected:
                success_count += 1

        logger.info(self._get_string("connection_manager.hw_manager.bulk_finished", default="Bulk connection finished: {success}/{total} connected successfully.", success=success_count, total=total_attempted))
        return success_count, total_attempted

    def shutdown_all_connections(self) -> None:
        """Safely terminates all active driver instances."""
        logger.info(self._get_string("connection_manager.hw_manager.shutdown_all", default="Shutting down all active hardware connections..."))
        for tl_id, driver in list(self.active_connections.items()):
            try:
                driver.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down driver {tl_id}: {e}")
        self.active_connections.clear()
