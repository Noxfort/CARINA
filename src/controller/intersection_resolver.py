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

# File: src/controller/intersection_resolver.py
# Author: Gabriel Moraes
# Date: August 10, 2026

from typing import Dict, Optional, Any


class IntersectionResolver:
    """
    Handles resolution of IP addresses to junction IDs, normalization of prefix aliases (tl_),
    and querying active driver hardware metadata.
    """

    def __init__(self, active_connections: Dict[str, Any], saved_ips: Dict[str, str]):
        self.active_connections = active_connections
        self.saved_ips = saved_ips

    def find_intersection_by_ip(self, ip_address: str) -> Optional[str]:
        """
        Resolves an incoming IP address to a known intersection ID, prioritizing active connections.

        Args:
            ip_address (str): Incoming IP address string (e.g. from SNMP Trap).

        Returns:
            Optional[str]: Matching junction ID string or None.
        """
        if not ip_address:
            return None

        clean_req_ip = ip_address.split(":")[0] if ":" in ip_address else ip_address

        # 1. Check active connected drivers first (PRIORITY)
        for tl_id, driver_wrapper in self.active_connections.items():
            if getattr(driver_wrapper, "is_connected", False):
                drv_ip = getattr(driver_wrapper, "ip_address", "")
                clean_driver_ip = drv_ip.split(":")[0] if ":" in drv_ip else drv_ip
                if clean_req_ip == clean_driver_ip or (clean_req_ip in ["127.0.0.1", "localhost"] and clean_driver_ip in ["127.0.0.1", "localhost"]):
                    return tl_id

        # 2. Check any active driver wrapper
        for tl_id, driver_wrapper in self.active_connections.items():
            drv_ip = getattr(driver_wrapper, "ip_address", "")
            clean_driver_ip = drv_ip.split(":")[0] if ":" in drv_ip else drv_ip
            if clean_req_ip == clean_driver_ip:
                return tl_id

        # 3. Fallback to saved IPs
        for tl_id, saved_ip in self.saved_ips.items():
            clean_saved = saved_ip.split(":")[0] if ":" in saved_ip else saved_ip
            if clean_req_ip == clean_saved:
                return tl_id

        # 4. Fallback: If only 1 connected intersection exists, resolve to it!
        connected_ids = [
            tid for tid, drv in self.active_connections.items()
            if getattr(drv, "is_connected", False)
        ]
        if len(connected_ids) == 1:
            return connected_ids[0]

        return None

    def is_intersection_connected(self, intersection_id: str) -> bool:
        """
        Returns True if the specified intersection is actively connected.

        Args:
            intersection_id (str): Target intersection ID.

        Returns:
            bool: Connection state.
        """
        if not intersection_id or intersection_id == "DESCONHECIDO":
            return False

        possible_ids = [str(intersection_id)]
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
        """
        Retrieves manufacturer brand, model, and connection status for a given intersection.

        Args:
            intersection_id (str): Target intersection ID.

        Returns:
            Dict[str, Any]: Struct containing is_connected, brand, and model strings.
        """
        possible_ids = [str(intersection_id)]
        if str(intersection_id).startswith("tl_"):
            possible_ids.append(str(intersection_id).replace("tl_", ""))
        else:
            possible_ids.append(f"tl_{intersection_id}")

        for pid in possible_ids:
            driver_wrapper = self.active_connections.get(pid)
            if driver_wrapper and getattr(driver_wrapper, "is_connected", False) and getattr(driver_wrapper, "hardware_driver", None):
                hw_drv = driver_wrapper.hardware_driver
                brand = getattr(hw_drv, "brand", None)
                model = getattr(hw_drv, "model", None)
                return {
                    "is_connected": True,
                    "brand": brand if brand else "Não informado",
                    "model": model if model else "Não informado"
                }

        return {"is_connected": False, "brand": "Desconectado", "model": "Desconectado"}
