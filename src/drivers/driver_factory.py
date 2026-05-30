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
    def create_and_connect_driver(ip_address: str, port: int, community_string: str = 'public') -> Optional[BaseTrafficDriver]:
        """
        Attempts a handshake with the target IP and Port to discover its protocol.
        If successful, starts the heartbeat failsafe and returns the driver instance.
        """
        logger.info(f"[{ip_address}:{port}] Starting protocol discovery (Handshake)...")

        # ---------------------------------------------------------
        # 1. First Attempt: Test NTCIP
        # ---------------------------------------------------------
        logger.debug(f"[{ip_address}:{port}] Sending Handshake using NTCIP...")
        ntcip_driver = NtcipDriver(ip_address, port, community_string)
        
        # Test a basic NTCIP read (e.g., fetching active greens)
        success_ntcip, _ = ntcip_driver.snmp_get(NtcipDriver.OID_PHASE_STATUS_GREENS)
        
        if success_ntcip:
            logger.info(f"[{ip_address}:{port}] Handshake successful! Protocol identified as NTCIP 1202.")
            ntcip_driver.start_heartbeat()
            return ntcip_driver

        # ---------------------------------------------------------
        # 2. Second Attempt: Test UTMC2 (If NTCIP failed)
        # ---------------------------------------------------------
        logger.debug(f"[{ip_address}:{port}] NTCIP failed. Sending Handshake using UTMC2...")
        utmc_driver = UtmcDriver(ip_address, port, community_string)
        
        # Test a basic UTMC read (e.g., fetching active stages)
        success_utmc, _ = utmc_driver.snmp_get(UtmcDriver.OID_STAGE_STATUS_ACTIVE)

        if success_utmc:
            logger.info(f"[{ip_address}:{port}] Handshake successful! Protocol identified as UTMC2.")
            utmc_driver.start_heartbeat()
            return utmc_driver

        # ---------------------------------------------------------
        # 3. Fallback: Both attempts failed
        # ---------------------------------------------------------
        logger.error(f"[{ip_address}:{port}] Discovery failed. The controller did not respond to NTCIP or UTMC2 OIDs.")
        return None