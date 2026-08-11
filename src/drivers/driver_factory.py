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
from typing import Optional, Any

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
    def create_and_connect_driver(ip_address: str, port: int, community_string: str = 'public', intersection_id: str = "Desconhecido", green_stages: list = None, locale_manager: Optional[Any] = None) -> Optional[BaseTrafficDriver]:
        """
        Attempts a handshake with the target IP and Port to discover its protocol.
        First sends an SNMP GET for sysDescr (1.3.6.1.2.1.1.1.0) to ask which protocol the controller speaks.
        If unrecognized, falls back to probing protocol-specific telemetry OIDs.
        """
        def _get_string(key: str, default: str = None, **kwargs) -> str:
            if locale_manager and hasattr(locale_manager, 'get_string'):
                return locale_manager.get_string(key, default=default, **kwargs)
            return default.format(**kwargs) if default and kwargs else (default or key)

        logger.info(f"[{ip_address}:{port}] Starting protocol discovery (Handshake)...")

        detected_brand = "Não informado"
        detected_model = "Não informado"
        raw_sys_descr = ""

        # ---------------------------------------------------------
        # 1. Ask the controller directly what protocol it speaks via sysDescr
        # ---------------------------------------------------------
        logger.debug(f"[{ip_address}:{port}] Querying sysDescr (1.3.6.1.2.1.1.1.0) for protocol discovery...")
        temp_driver = NtcipDriver(ip_address, port, intersection_id, community_string, green_stages=green_stages)
        success_descr, descr_val = temp_driver.snmp_get("1.3.6.1.2.1.1.1.0")

        if success_descr:
            raw_sys_descr = str(descr_val)
            detected_brand, detected_model = DriverFactory.extract_brand_and_model(descr_val)
            descr_upper = raw_sys_descr.upper()
            logger.info(f"[{ip_address}:{port}] Controller returned sysDescr: '{descr_val}' (Brand: '{detected_brand}', Model: '{detected_model}')")
            
            if "NTCIP" in descr_upper:
                logger.info(f"[{ip_address}:{port}] Protocol identified as NTCIP 1202 via sysDescr.")
                ntcip_driver = NtcipDriver(ip_address, port, intersection_id, community_string, green_stages=green_stages)
                ntcip_driver.brand = detected_brand
                ntcip_driver.model = detected_model
                ntcip_driver.sys_descr = raw_sys_descr
                ntcip_driver.start_heartbeat()
                return ntcip_driver
            elif "UTMC" in descr_upper:
                logger.info(f"[{ip_address}:{port}] Protocol identified as UTMC2 via sysDescr.")
                utmc_driver = UtmcDriver(ip_address, port, intersection_id, community_string, green_stages=green_stages)
                utmc_driver.brand = detected_brand
                utmc_driver.model = detected_model
                utmc_driver.sys_descr = raw_sys_descr
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
            ntcip_driver.brand = detected_brand
            ntcip_driver.model = detected_model
            ntcip_driver.sys_descr = raw_sys_descr
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
            utmc_driver.brand = detected_brand
            utmc_driver.model = detected_model
            utmc_driver.sys_descr = raw_sys_descr
            utmc_driver.start_heartbeat()
            return utmc_driver

    @staticmethod
    def extract_brand_and_model(descr_val: Any) -> tuple[str, str]:
        """
        Parses sysDescr string to identify brand (manufacturer) and model of the controller.
        Returns ('Não informado', 'Não informado') if unknown.
        """
        if not descr_val:
            return "Não informado", "Não informado"
        
        descr = str(descr_val).strip()
        if not descr:
            return "Não informado", "Não informado"

        descr_upper = descr.upper()
        
        known_brands = [
            "SIEMENS", "PEEK", "SWARCO", "ECONOLITE", "DATAPROM", "TRAFFICWARE",
            "MCCAIN", "YUNEX", "COMPASS", "TELVENT", "KAPSCH"
        ]
        
        brand = "Não informado"
        for b in known_brands:
            if b in descr_upper:
                brand = b.title()
                break

        import re
        model_match = re.search(r'\b(ST\d{3,4}|M\d{2,3}|ATC[-_ ]?\d{4}|ASC[/-]?\d+|[A-Z]{1,4}[-_]?\d{3,4})\b', descr, re.IGNORECASE)
        if model_match:
            model = model_match.group(1).upper()
        else:
            model = descr if len(descr) <= 30 else descr[:30] + "..."

        return brand, model


        # ---------------------------------------------------------
        # 4. Fallback: Both attempts failed
        # ---------------------------------------------------------
        logger.error(_get_string("drivers.factory.unknown_protocol", default="[DriverFactory] No supported protocol responded at IP {ip}:{port}.", ip=ip_address, port=port))
        return None