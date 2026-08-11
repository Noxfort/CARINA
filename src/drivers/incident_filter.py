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

# File: src/drivers/incident_filter.py
# Author: Gabriel Moraes
# Date: 2026-07-31

"""
Incident Filter Intermediary Module.
Filters duplicate hardware alert bursts before forwarding incidents to IncidentReporter,
supporting cross-process deduplication via shared file stamp (.carina_incident_filter.stamp).
"""

import os
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any
from src.drivers.incident_reporter import IncidentReporter

logger = logging.getLogger(__name__)

def _log_filter_debug(intersection_id: str, message_text: str, is_duplicate: bool, action: str):
    """Logs incident filtering activity directly to carina_incident_filter_debug.log in project root."""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        log_entry = (
            f"==================== [INCIDENT FILTER DEBUG LOG] {timestamp} ====================\n"
            f"Intersection ID : {intersection_id}\n"
            f"Message Text    : {message_text}\n"
            f"Is Duplicate    : {is_duplicate}\n"
            f"Action Taken    : {action}\n"
            f"===================================================================================\n\n"
        )
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        filepath = os.path.join(project_root, "carina_incident_filter_debug.log")
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as err:
        logger.error(f"Error writing incident filter debug log: {err}")

# Force immediate creation of carina_incident_filter_debug.log upon module import
try:
    _init_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _init_path = os.path.join(_init_root, "carina_incident_filter_debug.log")
    with open(_init_path, "a", encoding="utf-8") as _f:
        _f.write(f"=== [INCIDENT FILTER DEBUG LOG INITIALIZED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===\n")
except Exception:
    pass

class IncidentFilter:
    """
    Intermediary filter component for Monitor incident reporting.
    Uses shared file stamp (.carina_incident_filter.stamp) for 100% cross-process deduplication.
    """

    @staticmethod
    def process_and_report(intersection_id: str, level: str, trap_data: Dict[str, Any]) -> None:
        """
        Processes incoming trap data using cross-process shared file stamp matching.
        If ID and Message Text match the last sent message within 1.0s across any process, it is silently dropped.
        """
        try:
            resolved_id = str(trap_data.get("intersection_id", intersection_id))
            details = trap_data.get("details") or trap_data.get("message") or "Alerta ativo de hardware recebido"
            
            if trap_data.get("message"):
                msg_text = str(trap_data.get("message"))
            elif resolved_id and resolved_id != "DESCONHECIDO":
                msg_text = f"[{resolved_id}] {details}"
            else:
                msg_text = str(details)

            current_key = f"{resolved_id}:{msg_text}"
            now = time.time()

            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            stamp_file = os.path.join(project_root, ".carina_incident_filter.stamp")

            time_diff = 999.0
            if os.path.exists(stamp_file):
                try:
                    with open(stamp_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content and "|||" in content:
                            parts = content.split("|||")
                            if len(parts) == 2:
                                last_key, last_time_str = parts[0], float(parts[1])
                                if last_key == current_key:
                                    time_diff = now - last_time_str
                except Exception:
                    time_diff = 999.0

            # Cross-process comparison: if identical message arrived < 1.0s ago anywhere -> DUPLICATE!
            if time_diff < 1.0:
                _log_filter_debug(resolved_id, msg_text, True, f"DROPPED (DUPLICATE BURST IGNORED - diff: {time_diff:.4f}s)")
                logger.info(f"[IncidentFilter] Ignored duplicate cross-process burst ({time_diff:.4f}s): {msg_text}")
                return

            # Write current key and timestamp to shared cross-process file stamp
            try:
                with open(stamp_file, "w", encoding="utf-8") as f:
                    f.write(f"{current_key}|||{now}")
            except Exception:
                pass

            _log_filter_debug(resolved_id, msg_text, False, f"FORWARDED TO INCIDENT_REPORTER (diff: {time_diff:.4f}s)")
            IncidentReporter.report_trap(intersection_id, level, trap_data)
        except Exception as err:
            logger.error(f"[IncidentFilter] Error in incident filter: {err}")
