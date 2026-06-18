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

# File: src/drivers/snmp_client.py
# Author: Gabriel Moraes
# Date: 2026-06-16

"""
Low-level SNMP client wrapper to manage asynchronous GET and SET calls.
Extracts network transport concerns to satisfy SRP.
"""

import logging
import asyncio
from typing import Any, Tuple

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

class SnmpClient:
    """
    Handles standard SNMP GET and SET requests asynchronously, wrapping them for synchronous callers.
    """
    def __init__(self, ip_address: str, port: int, community_string: str = 'public', timeout: int = 2, retries: int = 1):
        self.ip_address = ip_address
        self.port = port
        self.community_string = community_string
        self.timeout = timeout
        self.retries = retries

    def get(self, oid: str) -> Tuple[bool, Any]:
        """
        Performs a synchronous SNMP GET request.
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

    def set(self, oid: str, value: Any, value_type: Any) -> Tuple[bool, Any]:
        """
        Performs a synchronous SNMP SET request.
        Returns a tuple: (Success Boolean, Value or Error Message)
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
