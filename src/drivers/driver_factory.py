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

# File: src/drivers/driver_factory.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
Factory module for traffic light drivers.
Implements an automatic handshake protocol discovery mechanism to determine
whether a specific intersection port speaks NTCIP 1202 or UTMC2.
"""

import logging
from typing import Optional

from src.drivers.base_driver import BaseTrafficDriver
from src.drivers.ntcip_driver import NtcipDriver
from src.drivers.utmc_driver import UtmcDriver

logger = logging.getLogger(__name__)

class DriverFactory:
    """
    Factory class responsible for discovering the controller's protocol
    and instantiating the appropriate driver (NTCIP or UTMC2).
    """

    @staticmethod
    def create_and_connect_driver(ip_address: str, port: int, community_string: str = 'public', intersection_id: str = "Desconhecido", green_stages: list = None) -> Optional[BaseTrafficDriver]:
        """
        Attempts a handshake with the target IP and Port to discover its protocol.
        First sends an SNMP GET for sysDescr (1.3.6.1.2.1.1.1.0) to ask which protocol the controller speaks.
        If unrecognized, falls back to probing protocol-specific telemetry OIDs.
        """
        logger.info(f"[{ip_address}:{port}] Starting protocol discovery (Handshake)...")

        # ---------------------------------------------------------
        # 1. Ask the controller directly what protocol it speaks via sysDescr
        # ---------------------------------------------------------
        logger.debug(f"[{ip_address}:{port}] Querying sysDescr (1.3.6.1.2.1.1.1.0) for protocol discovery...")
        temp_driver = NtcipDriver(ip_address, port, intersection_id, community_string, green_stages=green_stages)
        success_descr, descr_val = temp_driver.snmp_get("1.3.6.1.2.1.1.1.0")

        if success_descr:
            descr_upper = str(descr_val).upper()
            logger.info(f"[{ip_address}:{port}] Controller returned sysDescr: '{descr_val}'")
            
            if "NTCIP" in descr_upper:
                logger.info(f"[{ip_address}:{port}] Protocol identified as NTCIP 1202 via sysDescr.")
                ntcip_driver = NtcipDriver(ip_address, port, intersection_id, community_string, green_stages=green_stages)
                ntcip_driver.start_heartbeat()
                return ntcip_driver
            elif "UTMC" in descr_upper:
                logger.info(f"[{ip_address}:{port}] Protocol identified as UTMC2 via sysDescr.")
                utmc_driver = UtmcDriver(ip_address, port, intersection_id, community_string, green_stages=green_stages)
                utmc_driver.start_heartbeat()
                return utmc_driver
            else:
                logger.warning(f"[{ip_address}:{port}] Unrecognized protocol in sysDescr. Falling back to active probing.")
        else:
            logger.warning(f"[{ip_address}:{port}] Direct protocol query failed ({descr_val}). Falling back to active probing.")

        # ---------------------------------------------------------
        # 2. Probe Fallback: Test NTCIP
        # ---------------------------------------------------------
        logger.debug(f"[{ip_address}:{port}] Probing NTCIP 1202...")
        ntcip_driver = NtcipDriver(ip_address, port, intersection_id, community_string, green_stages=green_stages)
        success_ntcip, _ = ntcip_driver.snmp_get(ntcip_driver.oids["telemetry"].get("status_greens"))
        
        if success_ntcip:
            logger.info(f"[{ip_address}:{port}] Probe successful! Protocol identified as NTCIP 1202.")
            ntcip_driver.start_heartbeat()
            return ntcip_driver

        # ---------------------------------------------------------
        # 3. Probe Fallback: Test UTMC2
        # ---------------------------------------------------------
        logger.debug(f"[{ip_address}:{port}] Probing UTMC2...")
        utmc_driver = UtmcDriver(ip_address, port, intersection_id, community_string, green_stages=green_stages)
        success_utmc, _ = utmc_driver.snmp_get(utmc_driver.oids["telemetry"].get("status_active"))

        if success_utmc:
            logger.info(f"[{ip_address}:{port}] Probe successful! Protocol identified as UTMC2.")
            utmc_driver.start_heartbeat()
            return utmc_driver

        # ---------------------------------------------------------
        # 4. Fallback: Both attempts failed
        # ---------------------------------------------------------
        logger.error(f"[{ip_address}:{port}] Discovery failed. The controller did not respond to protocol queries or probes.")
        return None