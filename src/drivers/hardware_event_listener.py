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

# File: src/drivers/hardware_event_listener.py
# Author: Gabriel Moraes
# Date: 2026-07-30

"""
Abstract and concrete event listeners for active controller notifications (Traps, Push, Webhooks).
Designed according to the Open-Closed Principle (OCP) to allow seamless extension for new protocols.
"""

import logging
import socket
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, Callable

from src.drivers.incident_reporter import IncidentReporter

logger = logging.getLogger(__name__)


class BaseActiveEventListener(ABC):
    """
    Abstract base class for active event listeners.
    Listens for asynchronous push notifications / traps from physical controllers.
    """

    def __init__(self, port: int, on_event_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.port = port
        self.on_event_callback = on_event_callback
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    @abstractmethod
    def start(self) -> None:
        """Starts the active event listener loop in a background thread."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the active event listener and frees network resources."""
        pass

    def dispatch_event(self, event_data: Dict[str, Any]) -> None:
        """
        Dispatches event payload to the UI callback (Channel 1) synchronously
        and to the Monitor MQTT reporter (Channel 2) asynchronously via background thread.
        """
        try:
            intersection_id = event_data.get("intersection_id", "DESCONHECIDO")
            level = event_data.get("level", "WARNING")
            
            # Channel 1: UI Callback (Synchronous 0ms UI update)
            if self.on_event_callback:
                try:
                    self.on_event_callback(event_data)
                except Exception as cb_err:
                    logger.error(f"[BaseActiveEventListener] Error in UI event callback: {cb_err}")

            # Channel 2: External Monitor MQTT via IncidentFilter pass-through (Asynchronous daemon thread)
            from src.drivers.incident_filter import IncidentFilter
            threading.Thread(
                target=IncidentFilter.process_and_report,
                args=(intersection_id, level, event_data),
                daemon=True,
                name="IncidentFilterThread"
            ).start()

        except Exception as e:
            logger.error(f"[BaseActiveEventListener] Error dispatching event: {e}")


class SnmpTrapListener(BaseActiveEventListener):
    """
    Concrete implementation for listening to SNMP Traps / Informs (UDP 162).
    Decodes SNMP packets and formats active hardware faults into JSON.
    """

    def __init__(
        self,
        port: int = 162,
        get_intersection_by_ip: Optional[Callable[[str], str]] = None,
        is_connected_checker: Optional[Callable[[str], bool]] = None
    ) -> None:
        super().__init__(port=port)
        self.get_intersection_by_ip = get_intersection_by_ip
        self.is_connected_checker = is_connected_checker
        self._socket: Optional[socket.socket] = None
        self._recent_traps_cache: Dict[str, float] = {}

    def start(self) -> None:
        if self.is_running:
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="SnmpTrapListener")
        self._thread.start()
        logger.info(f"[SnmpTrapListener] Listening for active SNMP Traps on UDP port {self.port}...")

    def stop(self) -> None:
        self.is_running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("[SnmpTrapListener] SNMP Trap Listener stopped.")

    def _listen_loop(self) -> None:
        bound = False
        ports_to_try = [self.port] if self.port != 162 else [162, 1620]
        for p in ports_to_try:
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._socket.bind(("0.0.0.0", p))
                self._socket.settimeout(1.0)
                self.port = p
                bound = True
                logger.info(f"[SnmpTrapListener] Listening for active SNMP Traps on UDP port {self.port}...")
                print(f"[CARINA SYSTEM] SNMP Trap Listener ativo escutando alertas na porta UDP {self.port}")
                break
            except Exception as e:
                logger.debug(f"[SnmpTrapListener] Could not bind to UDP port {p}: {e}")
                if self._socket:
                    try:
                        self._socket.close()
                    except Exception:
                        pass
                    self._socket = None

        if not bound:
            logger.warning(f"[SnmpTrapListener] Could not bind to any UDP ports ({ports_to_try}). Trap listener disabled.")
            self.is_running = False
            return

        while self.is_running:
            try:
                if self._socket:
                    data, addr = self._socket.recvfrom(4096)
                    if data:
                        self._process_trap_packet(data, addr[0])
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    logger.debug(f"[SnmpTrapListener] Error receiving UDP packet: {e}")

    def _process_trap_packet(self, raw_data: bytes, sender_ip: str) -> None:
        """
        Decodes incoming SNMP Trap data packet and extracts OID/error details.
        """
        try:
            intersection_id = "DESCONHECIDO"
            if self.get_intersection_by_ip:
                resolved_id = self.get_intersection_by_ip(sender_ip)
                if resolved_id:
                    intersection_id = resolved_id

            # Filter out traps ONLY if an intersection ID was resolved and is explicitly marked as disconnected
            if self.is_connected_checker and intersection_id != "DESCONHECIDO":
                if not self.is_connected_checker(intersection_id):
                    logger.info(f"[SnmpTrapListener] Ignored SNMP Trap from {sender_ip} ({intersection_id}) because controller status is DISCONNECTED.")
                    return

            # Decode raw text and fallback to PDU parser if raw binary SNMP trap
            raw_text = raw_data.decode('utf-8', errors='ignore')
            if "TRAP|" not in raw_text and not any(tag in raw_text for tag in ["[HARDWARE]", "[SOFTWARE]", "[HARDWARE_TRAP]", "[SOFTWARE_TRAP]"]):
                parsed_pdu = self._parse_snmp_pdu(raw_data)
                if parsed_pdu and parsed_pdu.get("message"):
                    raw_text = parsed_pdu["message"]
            
            from src.drivers.trap_transformer import TrapTransformer
            event_payload = TrapTransformer.transform(
                raw_message=raw_text,
                protocol="UTMC2",
                intersection_id=intersection_id
            )
            event_payload["source_ip"] = sender_ip

            # Deduplication filter: Ignore identical traps flagged by TrapTransformer within 3-second window
            if event_payload.get("is_duplicate"):
                logger.info(f"[SnmpTrapListener] Ignored duplicate SNMP Trap packet from {sender_ip} ({intersection_id}) within 3s window.")
                return

            print(f"\n🚨 [CARINA ALERT RECEIVER] SNMP TRAP RECEBIDO! IP: {sender_ip} | Cruzamento: {intersection_id} | Alerta: {event_payload['message']}\n")
            logger.warning(f"[SnmpTrapListener] ACTIVE HARDWARE TRAP from {sender_ip} ({intersection_id}): {event_payload['message']}")
            self.dispatch_event(event_payload)

        except Exception as e:
            logger.error(f"[SnmpTrapListener] Failed to process trap from {sender_ip}: {e}")

    def _parse_snmp_pdu(self, raw_data: bytes) -> Dict[str, Any]:
        """
        Decodes SNMP ASN.1 PDU bytes or embedded TRAP|... payload into structured fields.
        """
        details = {
            "trap_oid": "1.3.6.1.4.1.2825.4.1",
            "message": "Alerta ativo de hardware recebido do controlador",
            "level": "CRITICAL",
            "varbinds": {}
        }
        try:
            # 1. Search for custom TRAP| header if present
            raw_text = raw_data.decode('utf-8', errors='ignore')
            if "TRAP|" in raw_text:
                trap_part = raw_text.split("TRAP|", 1)[1]
                parts = trap_part.split("|")
                if len(parts) >= 3:
                    details["trap_oid"] = parts[0].strip()
                    details["level"] = parts[1].strip()
                    details["message"] = "|".join(parts[2:]).strip()
                    return details

            # 2. Fallback: extract clean printable ASCII/UTF-8 strings
            import re
            printable_strings = re.findall(r'[A-Za-z0-9_\-\.\:\/\[\]\s\(\)]{4,}', raw_text)
            clean_strings = [s for s in printable_strings if s not in ["public", "private"] and len(s) > 5]
            if clean_strings:
                details["message"] = " | ".join(clean_strings[:2])

        except Exception as e:
            logger.debug(f"[SnmpTrapListener] Error parsing PDU: {e}")

        return details
