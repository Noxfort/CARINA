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
Implements modern asyncio-wrapped SNMP client functionality (PySNMP v7+) 
and Heartbeat (Failsafe) mechanisms.
"""

import time
import logging
import threading
import asyncio
import re
import ipaddress
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple, Dict, Union

# Modern PySNMP (v7+) compatibility for Python 3.12+
try:
    from pysnmp.hlapi.v3arch.asyncio import (
        SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
        ObjectType, ObjectIdentity, get_cmd, set_cmd
    )
except ImportError:
    # Fallback for PySNMP v6.x
    from pysnmp.hlapi.v3arch.asyncio import (
        SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
        ObjectType, ObjectIdentity, getCmd as get_cmd, setCmd as set_cmd
    )

logger = logging.getLogger(__name__)

class BaseTrafficDriver(ABC):
    """
    Abstract base class for all traffic controller drivers (NTCIP, UTMC2, etc.).
    Provides built-in SNMP communication and a background heartbeat mechanism.
    """

    def __init__(self, ip_address: str, port: int, community_string: str = 'public', timeout: int = 2, retries: int = 1) -> None:
        # Robust IP sanitization: extract a valid IPv4 address from any input,
        # even if garbage text (e.g. log output) was accidentally pasted.
        ip_address = str(ip_address).strip()
        
        # Search for the first valid IPv4 pattern (optionally followed by :port)
        ip_port_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d{1,5}))?', ip_address)
        if ip_port_match:
            candidate_ip = ip_port_match.group(1)
            try:
                ipaddress.ip_address(candidate_ip)  # Validate it's a real IPv4
                ip_address = candidate_ip
                if ip_port_match.group(2):
                    port = int(ip_port_match.group(2))
            except ValueError:
                pass  # Keep original ip_address if validation fails

        self.ip_address = ip_address
        self.port = port
        self.community_string = community_string
        self.timeout = timeout
        self.retries = retries
        
        # Note: SnmpEngine is instantiated per-call to avoid Asyncio Event Loop
        # closure errors across different Flet/Heartbeat threads.

        # Heartbeat control variables
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_heartbeat_event = threading.Event()
        self.heartbeat_interval_seconds = 2.0

    def snmp_get(self, oid: str) -> Tuple[bool, Any]:
        """
        Performs a synchronous SNMP GET request by wrapping the async PySNMP API.
        Returns a tuple: (Success Boolean, Value or Error Message)
        """
        async def _async_get():
            engine = SnmpEngine()
            try:
                transport = await UdpTransportTarget.create(
                    (self.ip_address, self.port),
                    timeout=self.timeout,
                    retries=self.retries
                )
                error_ind, error_stat, error_idx, binds = await get_cmd(
                    engine,
                    CommunityData(self.community_string, mpModel=1), # SNMPv2c
                    transport,
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
                return error_ind, error_stat, error_idx, binds
            finally:
                # Safely release sockets to prevent memory leaks in the new API
                if hasattr(engine, 'close_dispatcher'):
                    engine.close_dispatcher()
                elif hasattr(engine, 'transportDispatcher') and engine.transportDispatcher:
                    engine.transportDispatcher.closeDispatcher()

        try:
            error_indication, error_status, error_index, var_binds = asyncio.run(_async_get())
            
            if error_indication:
                logger.error(f"[{self.ip_address}:{self.port}] SNMP GET Error: {error_indication}")
                return False, str(error_indication)
            elif error_status:
                err_msg = f"{error_status.prettyPrint()} at {error_index and var_binds[int(error_index) - 1][0] or '?'}"
                logger.error(f"[{self.ip_address}:{self.port}] SNMP GET Status Error: {err_msg}")
                return False, err_msg
            else:
                for var_bind in var_binds:
                    return True, var_bind[1].prettyPrint()
                    
        except Exception as e:
            logger.error(f"[{self.ip_address}:{self.port}] SNMP GET Exception: {e}")
            return False, str(e)

        return False, "Unknown Error"

    def snmp_set(self, oid: str, value: Any, value_type: Any) -> Tuple[bool, Any]:
        """
        Performs a synchronous SNMP SET request by wrapping the async PySNMP API.
        """
        async def _async_set():
            engine = SnmpEngine()
            try:
                transport = await UdpTransportTarget.create(
                    (self.ip_address, self.port),
                    timeout=self.timeout,
                    retries=self.retries
                )
                error_ind, error_stat, error_idx, binds = await set_cmd(
                    engine,
                    CommunityData(self.community_string, mpModel=1),
                    transport,
                    ContextData(),
                    ObjectType(ObjectIdentity(oid), value_type(value))
                )
                return error_ind, error_stat, error_idx, binds
            finally:
                if hasattr(engine, 'close_dispatcher'):
                    engine.close_dispatcher()
                elif hasattr(engine, 'transportDispatcher') and engine.transportDispatcher:
                    engine.transportDispatcher.closeDispatcher()

        try:
            error_indication, error_status, error_index, var_binds = asyncio.run(_async_set())
            
            if error_indication:
                logger.error(f"[{self.ip_address}:{self.port}] SNMP SET Error: {error_indication}")
                return False, str(error_indication)
            elif error_status:
                err_msg = f"{error_status.prettyPrint()} at {error_index and var_binds[int(error_index) - 1][0] or '?'}"
                logger.error(f"[{self.ip_address}:{self.port}] SNMP SET Status Error: {err_msg}")
                return False, err_msg
            else:
                for var_bind in var_binds:
                    return True, var_bind[1].prettyPrint()
                    
        except Exception as e:
            logger.error(f"[{self.ip_address}:{self.port}] SNMP SET Exception: {e}")
            return False, str(e)

        return False, "Unknown Error"

    def start_heartbeat(self) -> None:
        """Starts the background heartbeat thread to maintain the failsafe mechanism."""
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return

        self._stop_heartbeat_event.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name=f"Heartbeat-{self.ip_address}")
        self._heartbeat_thread.start()
        logger.info(f"[{self.ip_address}:{self.port}] Heartbeat started.")

    def stop_heartbeat(self) -> None:
        """Stops the background heartbeat thread cleanly."""
        if self._heartbeat_thread is not None:
            self._stop_heartbeat_event.set()
            self._heartbeat_thread.join(timeout=3.0)
            logger.info(f"[{self.ip_address}:{self.port}] Heartbeat stopped.")

    def _heartbeat_loop(self) -> None:
        while not self._stop_heartbeat_event.is_set():
            success = self.send_heartbeat_pulse()
            if not success:
                logger.warning(f"[{self.ip_address}:{self.port}] Heartbeat pulse failed. Controller might revert to local fallback.")
            
            self._stop_heartbeat_event.wait(self.heartbeat_interval_seconds)

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