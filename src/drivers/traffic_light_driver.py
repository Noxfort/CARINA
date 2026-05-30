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

# File: src/drivers/traffic_light_driver.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
High-level manager for a single traffic light intersection.
Acts as a wrapper that utilizes the DriverFactory to establish 
and maintain the hardware connection (NTCIP or UTMC2).
"""

import logging
from typing import Optional, Dict, Any

from src.drivers.driver_factory import DriverFactory
from src.drivers.base_driver import BaseTrafficDriver

logger = logging.getLogger(__name__)

class TrafficLightDriver:
    """
    Represents a logical intersection controller in the CARINA engine.
    Abstracts the underlying hardware protocol from the AI agents.
    """

    def __init__(self, intersection_id: str, ip_address: str, port: int, community_string: str = 'public') -> None:
        self.intersection_id = intersection_id
        self.ip_address = ip_address
        self.port = port
        self.community_string = community_string
        
        self.hardware_driver: Optional[BaseTrafficDriver] = None
        self.is_connected = False
        
        logger.info(f"[Intersection {self.intersection_id}] Initializing TrafficLightDriver...")
        self._connect()

    def _connect(self) -> None:
        """
        Attempts to connect to the hardware using the factory discovery.
        """
        self.hardware_driver = DriverFactory.create_and_connect_driver(
            self.ip_address, 
            self.port, 
            self.community_string
        )
        
        if self.hardware_driver is not None:
            self.is_connected = True
            logger.info(f"[Intersection {self.intersection_id}] Connected via {self.hardware_driver.get_protocol_name()}")
        else:
            self.is_connected = False
            logger.error(f"[Intersection {self.intersection_id}] Failed to connect to hardware at {self.ip_address}:{self.port}")

    def apply_action(self, action_data: Dict[str, Any]) -> bool:
        """
        Receives an action from the CARINA AI engine and forwards it to the hardware.
        """
        if not self.is_connected or self.hardware_driver is None:
            logger.warning(f"[Intersection {self.intersection_id}] Cannot apply action. Driver is disconnected.")
            return False
            
        logger.debug(f"[Intersection {self.intersection_id}] Applying action: {action_data}")
        return self.hardware_driver.send_action(action_data)

    def get_status(self) -> Dict[str, Any]:
        """
        Retrieves current telemetry from the hardware to feed the state extractor and HMI.
        """
        if not self.is_connected or self.hardware_driver is None:
            return {
                "intersection_id": self.intersection_id,
                "status": "offline",
                "protocol": "none",
                "active_greens": 0,
                "active_yellows": 0,
                "active_reds": 0,
                "active_ped_calls": 0
            }
            
        telemetry = self.hardware_driver.get_telemetry()
        telemetry["intersection_id"] = self.intersection_id
        return telemetry

    def shutdown(self) -> None:
        """
        Safely disconnects the driver, stopping the heartbeat and returning control to local mode.
        """
        if self.hardware_driver is not None:
            logger.info(f"[Intersection {self.intersection_id}] Shutting down driver. Stopping heartbeat...")
            self.hardware_driver.stop_heartbeat()
            self.is_connected = False
            self.hardware_driver = None