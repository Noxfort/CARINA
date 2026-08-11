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

# File: src/communication/monitor_payload.py
# Author: Gabriel Moraes
# Date: 2026-07-31

"""
MonitorPayloadBuilder is responsible for formatting and validating JSON payloads
for the external Monitor system.
"""

import json
from datetime import datetime


class MonitorPayloadBuilder:
    """Builder utility for constructing standardized Monitor JSON telemetry payloads."""

    ORIGIN = "Carina"

    @staticmethod
    def create_payload(category: str, level: str, message: str) -> str:
        """
        Constructs the strict JSON payload expected by the Monitor.

        Args:
            category: "HARDWARE" or "SOFTWARE" (defaults to SOFTWARE if invalid/empty)
            level: "INFO", "WARNING", or "CRITICAL" (defaults to CRITICAL if invalid/empty)
            message: Descriptive message text

        Returns:
            JSON string payload
        """
        cat_upper = category.upper() if isinstance(category, str) else ""
        level_upper = level.upper() if isinstance(level, str) else ""

        category_final = cat_upper if cat_upper in ["HARDWARE", "SOFTWARE"] else "SOFTWARE"
        if not cat_upper and level_upper == "INFO":
            category_final = ""

        level_final = level_upper if level_upper in ["INFO", "WARNING", "CRITICAL"] else "CRITICAL"

        current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        payload = {
            "category": category_final,
            "origin": MonitorPayloadBuilder.ORIGIN,
            "level": level_final,
            "message": str(message),
            "occurred_at": current_time
        }
        return json.dumps(payload)
