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

# File: src/drivers/utmc2_parser.py
# Author: Gabriel Moraes
# Date: 2026-07-31

"""
UTMC2 Passive Protocol Dictionary.
Contains static regex patterns, token extraction rules, and category mappings
for parsing UTMC2 / SNMP Trap messages without side effects.
"""

import re
from typing import Dict, Any, Optional

# Static Regular Expression for UTMC2 SNMP Trap messages:
# Structure A (5 fields from carina_mock_lights): TRAP|<INTERSECTION_ID>|<OID>|<LEVEL>|[<CATEGORY>] <MESSAGE>
UTMC2_TRAP_5FIELD_REGEX = re.compile(
    r"TRAP\|(?P<intersection_id>[^|]+)\|(?P<oid>[^|]+)\|(?P<level>[^|]+)\|\[(?P<category>[^\]]+)\]\s*(?P<details>.*)",
    re.IGNORECASE
)

# Structure B (4 fields standard): TRAP|<OID>|<LEVEL>|[<CATEGORY>] <MESSAGE>
UTMC2_TRAP_REGEX = re.compile(
    r"TRAP\|(?P<oid>[^|]+)\|(?P<level>[^|]+)\|\[(?P<category>[^\]]+)\]\s*(?P<details>.*)",
    re.IGNORECASE
)

class UTMC2Parser:
    """
    100% Passive Dictionary & Rule Set for UTMC2 / NTCIP SNMP Trap messages.
    Does not execute network IO or side effects.
    """

    @staticmethod
    def parse_raw_string(raw_text: str) -> Optional[Dict[str, str]]:
        """
        Parses a raw string according to UTMC2 / NTCIP dictionary rules or bracketed category tags.
        Supports both 5-field (with intersection_id) and 4-field TRAP payloads.
        Returns a dictionary of parsed tokens or None if not recognizable.
        """
        if not raw_text:
            return None

        clean_text = str(raw_text).strip()

        # 1. Parse TRAP payloads
        if "TRAP|" in clean_text:
            # 1a. Try 5-field pattern from carina_mock_lights: TRAP|<INTERSECTION_ID>|<OID>|<LEVEL>|[<CATEGORY>] <DETAILS>
            match5 = UTMC2_TRAP_5FIELD_REGEX.search(clean_text)
            if match5:
                groups = match5.groupdict()
                intersection_id = groups.get("intersection_id", "").strip()
                oid = groups.get("oid", "1.3.6.1.4.1.2825.4.1").strip()
                level = groups.get("level", "CRITICAL").strip().upper()
                raw_cat = groups.get("category", "HARDWARE").strip().upper()
                details = groups.get("details", "").strip()

                category = "SOFTWARE" if "SOFTWARE" in raw_cat else "HARDWARE"
                if level not in ["INFO", "WARNING", "CRITICAL"]:
                    level = "CRITICAL"

                return {
                    "intersection_id": intersection_id,
                    "oid": oid,
                    "level": level,
                    "category": category,
                    "details": details
                }

            # 1b. Try 4-field standard pattern: TRAP|<OID>|<LEVEL>|[<CATEGORY>] <DETAILS>
            match4 = UTMC2_TRAP_REGEX.search(clean_text)
            if match4:
                groups = match4.groupdict()
                oid = groups.get("oid", "1.3.6.1.4.1.2825.4.1").strip()
                level = groups.get("level", "CRITICAL").strip().upper()
                raw_cat = groups.get("category", "HARDWARE").strip().upper()
                details = groups.get("details", "").strip()

                category = "SOFTWARE" if "SOFTWARE" in raw_cat else "HARDWARE"
                if level not in ["INFO", "WARNING", "CRITICAL"]:
                    level = "CRITICAL"

                return {
                    "oid": oid,
                    "level": level,
                    "category": category,
                    "details": details
                }

            # 1c. Fallback simple pipe split
            parts = clean_text.split("TRAP|", 1)[1].split("|")
            if len(parts) >= 4:
                intersection_id = parts[0].strip()
                oid = parts[1].strip()
                level = parts[2].strip().upper()
                msg = "|".join(parts[3:]).strip()
                cat = "SOFTWARE" if "SOFTWARE" in msg.upper() else "HARDWARE"
                for tag in ["[HARDWARE]", "[SOFTWARE]", "[HARDWARE_TRAP]", "[SOFTWARE_TRAP]"]:
                    msg = msg.replace(tag, "").strip()

                return {
                    "intersection_id": intersection_id,
                    "oid": oid,
                    "level": level if level in ["INFO", "WARNING", "CRITICAL"] else "CRITICAL",
                    "category": cat,
                    "details": msg
                }
            elif len(parts) >= 3:
                oid = parts[0].strip()
                level = parts[1].strip().upper()
                msg = "|".join(parts[2:]).strip()
                cat = "SOFTWARE" if "SOFTWARE" in msg.upper() else "HARDWARE"
                for tag in ["[HARDWARE]", "[SOFTWARE]", "[HARDWARE_TRAP]", "[SOFTWARE_TRAP]"]:
                    msg = msg.replace(tag, "").strip()

                return {
                    "oid": oid,
                    "level": level if level in ["INFO", "WARNING", "CRITICAL"] else "CRITICAL",
                    "category": cat,
                    "details": msg
                }

        # 2. Parse bracketed category tags directly (e.g. "[HARDWARE] Erro de sensor" or "[SOFTWARE] Timeout")
        tag_match = re.search(r"\[(?P<category>HARDWARE|SOFTWARE|HARDWARE_TRAP|SOFTWARE_TRAP)\]\s*(?P<details>.*)", clean_text, re.IGNORECASE)
        if tag_match:
            raw_cat = tag_match.group("category").upper()
            details = tag_match.group("details").strip()
            category = "SOFTWARE" if "SOFTWARE" in raw_cat else "HARDWARE"
            
            msg_upper = details.upper()
            if any(k in msg_upper for k in ["WARN", "WARNING"]):
                level = "WARNING"
            elif "INFO" in msg_upper:
                level = "INFO"
            else:
                level = "CRITICAL"

            return {
                "oid": "1.3.6.1.4.1.2825.4.1",
                "level": level,
                "category": category,
                "details": details
            }

        return None
