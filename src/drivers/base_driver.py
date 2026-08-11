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

# File: src/drivers/base_driver.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
Base abstraction for traffic light controllers.
Delegates SNMP networking, incident reporting, and heartbeat monitoring
to separate classes to respect SRP and OCP.
"""

import logging
import re
import ipaddress
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from src.drivers.snmp_client import SnmpClient
from src.drivers.incident_reporter import IncidentReporter
from src.drivers.heartbeat_manager import HeartbeatManager

logger = logging.getLogger(__name__)

class BaseTrafficDriver(ABC):
    """
    Abstract base class for all traffic controller drivers (NTCIP, UTMC2, etc.).
    Delegates SNMP communication, incident reporting, and heartbeat monitoring 
    to dedicated helper classes to satisfy SRP and OCP.
    """

    def __init__(self, ip_address: str, port: int, intersection_id: str = "Desconhecido", community_string: str = 'public', timeout: int = 2, retries: int = 1, green_stages: list = None) -> None:
        self.intersection_id = intersection_id
        self.green_stages = green_stages if green_stages is not None else []
        
        # Robust IP sanitization: extract a valid IPv4 address from any input
        ip_address = str(ip_address).strip()
        ip_port_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d{1,5}))?', ip_address)
        if ip_port_match:
            candidate_ip = ip_port_match.group(1)
            try:
                ipaddress.ip_address(candidate_ip)  # Validate it's a real IPv4
                ip_address = candidate_ip
                if ip_port_match.group(2):
                    port = int(ip_port_match.group(2))
            except ValueError:
                pass

        self.ip_address = ip_address
        self.port = port
        
        # Hardware device metadata (Manufacturer & Model)
        self.brand: str = "Não informado"
        self.model: str = "Não informado"
        self.sys_descr: str = ""

        # 1. Delegate SNMP communication to SnmpClient
        self.snmp_client = SnmpClient(ip_address, port, community_string, timeout, retries)

        # 2. Delegate Heartbeat lifecycle to HeartbeatManager
        self.heartbeat_manager = HeartbeatManager(
            ip_address=ip_address,
            port=port,
            send_pulse_cb=self.send_heartbeat_pulse,
            on_loss_cb=self._report_connection_loss,
            on_restore_cb=self._report_connection_restored,
            interval=2.0
        )

    def snmp_get(self, oid: str) -> Tuple[bool, Any]:
        """Delegates OID reading to SnmpClient."""
        return self.snmp_client.get(oid)

    def snmp_set(self, oid: str, value: Any, value_type: Any) -> Tuple[bool, Any]:
        """Delegates OID writing to SnmpClient."""
        return self.snmp_client.set(oid, value, value_type)

    def start_heartbeat(self) -> None:
        """Delegates heartbeat start to HeartbeatManager."""
        self.heartbeat_manager.start()

    def stop_heartbeat(self) -> None:
        """Delegates heartbeat stop to HeartbeatManager."""
        self.heartbeat_manager.stop()

    def _publish_incident(self, level: str, message: str) -> None:
        """Delegates incident reporting to IncidentReporter."""
        IncidentReporter.report(self.intersection_id, level, message)

    def _report_connection_loss(self) -> None:
        logger.critical(f"[{self.ip_address}:{self.port}] Connection LOST to intersection {self.intersection_id} after 3 failures.")
        self._publish_incident("CRITICAL", f"CARINA perdeu conexão com o controlador: {self.intersection_id}.")

    def _report_connection_restored(self) -> None:
        logger.info(f"[{self.ip_address}:{self.port}] Connection RESTORED to intersection {self.intersection_id}.")
        self._publish_incident("INFO", f"CARINA restabeleceu conexão com o controlador: {self.intersection_id}.")

    # =========================================================================
    # Abstract Methods to be implemented by specific protocols (NTCIP / UTMC2)
    # =========================================================================

    @abstractmethod
    def get_protocol_name(self) -> str:
        pass

    @abstractmethod
    def send_action(self, action_data: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def get_telemetry(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def send_heartbeat_pulse(self) -> bool:
        pass

    @abstractmethod
    def apply_logical_action(self, action: int, current_stage_idx: int, green_stages: list, stage_codes: dict = None) -> bool:
        pass