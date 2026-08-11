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
import os
from typing import Optional, Dict, Any

from src.drivers.driver_factory import DriverFactory
from src.drivers.base_driver import BaseTrafficDriver
from src.utils.paths import get_base_output_dir

logger = logging.getLogger(__name__)
cmd_logger = None  # Will be injected by ConnectionManager

class TrafficLightDriver:
    """
    Represents a logical intersection controller in the CARINA engine.
    Abstracts the underlying hardware protocol from the AI agents.
    """

    def __init__(self, intersection_id: str, ip_address: str, port: int, community_string: str = 'public', green_stages: list = None, locale_manager: Any = None) -> None:
        self.intersection_id = intersection_id
        self.ip_address = ip_address
        self.port = port
        self.community_string = community_string
        self.locale_manager = locale_manager
        
        self.hardware_driver: Optional[BaseTrafficDriver] = None
        self.is_connected = False
        
        self.current_stage = None
        self.green_stages = green_stages if green_stages is not None else []
        self.stage_states = self._load_stage_states_from_map()
        
        logger.info(self._get_string("drivers.traffic_light.init", default="[Intersection {id}] Initializing TrafficLightDriver...", id=self.intersection_id))
        self._connect()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _connect(self) -> None:
        """
        Attempts to connect to the hardware using the factory discovery.
        """
        self.hardware_driver = DriverFactory.create_and_connect_driver(
            self.ip_address, 
            self.port, 
            self.community_string,
            self.intersection_id,
            green_stages=self.green_stages
        )
        
        if self.hardware_driver is not None:
            self.is_connected = True
            logger.info(self._get_string("drivers.traffic_light.connected", default="[Intersection {id}] Connected via {protocol}", id=self.intersection_id, protocol=self.hardware_driver.get_protocol_name()))
            self.hardware_driver.start_heartbeat()
        else:
            self.is_connected = False
            logger.error(self._get_string("drivers.traffic_light.connect_failed", default="[Intersection {id}] Failed to connect to hardware at {ip}:{port}", id=self.intersection_id, ip=self.ip_address, port=self.port))

    def _load_stage_states_from_map(self) -> dict:
        """
        Parses the SUMO network map (.net.xml or .net.xml.gz) to extract
        the phase states for this intersection.
        """
        try:
            from src.controller.map_discoverer import MapTopologyDiscoverer
            map_file = MapTopologyDiscoverer.get_map_file()
            if not map_file or not os.path.exists(map_file):
                logger.warning(self._get_string("drivers.traffic_light.map_not_found", default="[Intersection {id}] Map file not found: {path}", id=self.intersection_id, path=map_file))
                return {}

            import gzip
            import xml.etree.ElementTree as ET

            opener = gzip.open if map_file.endswith('.gz') else open
            with opener(map_file, 'rt', encoding='utf-8') as f:
                tree = ET.parse(f)

            root = tree.getroot()
            states = {}
            for tl in root.findall('tlLogic'):
                if tl.get('id') == self.intersection_id:
                    for idx, phase in enumerate(tl.findall('phase')):
                        state = phase.get('state')
                        if state:
                            states[idx] = state
            return states
        except Exception as e:
            logger.error(self._get_string("drivers.traffic_light.map_load_failed", default="[Intersection {id}] Failed to load stage states from map: {error}", id=self.intersection_id, error=e))
            return {}

    def apply_logical_action(self, action: int, current_stage_idx: int, green_stages: list, stage_codes: dict = None) -> bool:
        """
        Translates a high-level logical AI action (0 = NEXT_STAGE, 1 = HOLD)
        into protocol-specific actions and dispatches them to the physical hardware.
        """
        self.current_stage = current_stage_idx
        self.green_stages = green_stages

        if not self.is_connected or self.hardware_driver is None:
            logger.warning(self._get_string("drivers.traffic_light.action_disconnected", default="[Intersection {id}] Cannot apply logical action. Driver is disconnected.", id=self.intersection_id))
            return False

        return self.hardware_driver.apply_logical_action(action, current_stage_idx, green_stages, stage_codes)

    def log_carina_colors(self, current_stage_idx: int, stage_codes: dict = None) -> None:
        """
        Logs the commanded stage state to carina_colors.log in SUMO format.
        """
        # Load from map file if not already done
        if not hasattr(self, 'stage_states') or not self.stage_states:
            self.stage_states = self._load_stage_states_from_map()

        # Determine which states mapping to use (prefer map file, fallback to stage_codes)
        active_states = self.stage_states if self.stage_states else (stage_codes if stage_codes else {})

        if not active_states:
            return

        log_dir = os.path.join(get_base_output_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "carina_colors.log")

        try:
            if current_stage_idx in active_states:
                state_str = active_states[current_stage_idx]
                if state_str and all(c.lower() == 'r' for c in state_str):
                    stage_num = 0
                else:
                    stage_num = current_stage_idx + 1

                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"estágio {stage_num}: {state_str}\n")
        except Exception as e:
            logger.error(self._get_string("drivers.traffic_light.colors_log_error", default="[Intersection {id}] Error writing to carina_colors.log: {error}", id=self.intersection_id, error=e))

    def log_carina_override(self, override_type: str) -> None:
        """
        Logs a manual override (flash or dark/desligado) to carina_colors.log.
        """
        log_dir = os.path.join(get_base_output_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "carina_colors.log")

        label = "flash" if override_type == "ALERT" else "desligado"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"estágio {label}: {label}\n")
        except Exception as e:
            logger.error(self._get_string("drivers.traffic_light.override_log_error", default="[Intersection {id}] Error writing override to carina_colors.log: {error}", id=self.intersection_id, error=e))

    def apply_action(self, action_data: Dict[str, Any]) -> bool:
        """
        Receives an action from the CARINA AI engine and forwards it to the hardware.
        """
        if not self.is_connected or self.hardware_driver is None:
            logger.warning(self._get_string("drivers.traffic_light.action_disconnected", default="[Intersection {id}] Cannot apply action. Driver is disconnected.", id=self.intersection_id))
            return False
            
        logger.debug(self._get_string("drivers.traffic_light.applying_action", default="[Intersection {id}] Applying action: {action}", id=self.intersection_id, action=action_data))
        if cmd_logger:
            cmd_logger.info(self._get_string("drivers.traffic_light.cmd_sending", default="CARINA sending command to {id} ({ip}): {action}", id=self.intersection_id, ip=self.ip_address, action=action_data))
            
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
                "brand": "Não informado",
                "model": "Não informado",
                "active_greens": 0,
                "active_yellows": 0,
                "active_reds": 0,
                "active_ped_calls": 0
            }
            
        telemetry = self.hardware_driver.get_telemetry()
        telemetry["intersection_id"] = self.intersection_id
        telemetry["brand"] = getattr(self.hardware_driver, "brand", "Não informado")
        telemetry["model"] = getattr(self.hardware_driver, "model", "Não informado")
        return telemetry

    def shutdown(self) -> None:
        """
        Safely disconnects the driver, stopping the heartbeat and returning control to local mode.
        """
        if self.hardware_driver is not None:
            logger.info(self._get_string("drivers.traffic_light.shutdown", default="[Intersection {id}] Shutting down driver. Stopping heartbeat...", id=self.intersection_id))
            self.hardware_driver.stop_heartbeat()
            self.is_connected = False
            self.hardware_driver = None