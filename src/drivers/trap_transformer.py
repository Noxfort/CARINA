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

# File: src/drivers/trap_transformer.py
# Author: Gabriel Moraes
# Date: 2026-07-31

"""
Active Trap Transformer Engine.
Orchestrates protocol dictionary lookup (e.g. UTMC2Parser) to chew raw messages
and output strict Monitor MQTT payloads for IncidentReporter.
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any

from src.drivers.utmc2_parser import UTMC2Parser

logger = logging.getLogger(__name__)

class TrapTransformer:
    """
    Active Transformer Engine that chews raw incoming controller alerts
    and generates standardized payloads matching both UI and Monitor requirements.
    """

    @staticmethod
    def transform(raw_message: str, protocol: str = "UTMC2", intersection_id: str = "DESCONHECIDO") -> Dict[str, Any]:
        """
        Transforms a raw controller message into a clean, standardized payload dictionary.
        
        Args:
            raw_message (str): The raw string received from the traffic light controller.
            protocol (str): Protocol name to select dictionary parser (e.g. "UTMC2").
            intersection_id (str): The resolved intersection ID (e.g. "1116667894").
            
        Returns:
            Dict[str, Any]: Standardized 6-field alert payload dictionary.
        """
        protocol_upper = str(protocol).upper() if protocol else "UTMC2"
        
        # Clean non-printable control characters while preserving unicode letters/spaces
        clean_raw = str(raw_message).strip()
        clean_raw = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_raw)
        
        parsed_data = None

        # 1. Consult passive dictionary based on protocol
        if protocol_upper in ["UTMC2", "UTMC", "SNMP"]:
            parsed_data = UTMC2Parser.parse_raw_string(clean_raw)

        # Fallback if no specific parser matched or string was unrecognized
        if not parsed_data:
            logger.warning(f"[TrapTransformer] Could not parse message with protocol '{protocol_upper}'. Using fallback formatter.")
            clean_msg = clean_raw
            for tag in ["[HARDWARE]", "[SOFTWARE]", "[HARDWARE_TRAP]", "[SOFTWARE_TRAP]"]:
                clean_msg = clean_msg.replace(tag, "").strip()

            msg_upper = clean_raw.upper()
            cat = "SOFTWARE" if "SOFTWARE" in msg_upper else "HARDWARE"
            
            # Infer severity level
            if any(k in msg_upper for k in ["CRITICAL", "ALARM", "FAULT", "ERROR", "FATAL"]):
                level = "CRITICAL"
            elif any(k in msg_upper for k in ["WARN", "WARNING"]):
                level = "WARNING"
            elif "INFO" in msg_upper:
                level = "INFO"
            else:
                level = "CRITICAL"

            parsed_data = {
                "oid": "1.3.6.1.4.1.2825.4.1",
                "level": level,
                "category": cat,
                "details": clean_msg or "Alerta ativo de hardware recebido do controlador"
            }

        # 2. Format details and full message text
        details_text = parsed_data.get("details", "").strip() or "Alerta recebido do controlador"
        resolved_intersection_id = parsed_data.get("intersection_id") or intersection_id
        
        if resolved_intersection_id and resolved_intersection_id != "DESCONHECIDO":
            formatted_message = f"[{resolved_intersection_id}] {details_text}"
        else:
            formatted_message = details_text

        category = parsed_data.get("category", "HARDWARE").upper()
        if category not in ["HARDWARE", "SOFTWARE"]:
            category = "HARDWARE"

        level = parsed_data.get("level", "CRITICAL").upper()
        if level not in ["INFO", "WARNING", "CRITICAL"]:
            level = "CRITICAL"

        result_payload = {
            "category": category,
            "level": level,
            "details": details_text,
            "message": formatted_message,
            "intersection_id": resolved_intersection_id,
            "trap_oid": parsed_data.get("oid", "1.3.6.1.4.1.2825.4.1")
        }

        # 3. Return unified alert payload dictionary (consumed by both UI and IncidentReporter)
        return result_payload

