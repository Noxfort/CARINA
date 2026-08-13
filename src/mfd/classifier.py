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

# File: src/engine/mfd/classifier.py
# Author: Gabriel Moraes
# Date: June 15, 2026

"""
MFD Classifier — Network State Classification Engine.

Classifies the current state of the road network based on the MFD
congestion ratio and generates human-readable performance reports.

Open/Closed Principle (OCP): New traffic states can be added by
extending the classification thresholds without modifying existing logic.
"""

from typing import Dict, Any, Optional
from mfd.snapshot import MFDSnapshot
from mfd.tracker import MFDTracker


import os
import json
import logging

class NetworkState:
    """Enumeration of possible network operating states."""
    CALIBRATING = 'CALIBRATING'
    FREE_FLOW = 'FREE_FLOW'
    APPROACHING_CAPACITY = 'APPROACHING_CAPACITY'
    MILD_CONGESTION = 'MILD_CONGESTION'
    HEAVY_CONGESTION = 'HEAVY_CONGESTION'
    GRIDLOCK = 'GRIDLOCK'


# Default classification table fallback
_DEFAULT_CLASSIFICATION_TABLE = [
    (0.7,  NetworkState.FREE_FLOW,
     'Network is operating well below capacity.'),

    (1.0,  NetworkState.APPROACHING_CAPACITY,
     'Network is near optimal throughput.'),

    (1.3,  NetworkState.MILD_CONGESTION,
     'Network has exceeded critical density. Throughput is declining.'),

    (1.8,  NetworkState.HEAVY_CONGESTION,
     'Network is severely congested. Significant throughput loss.'),

    (float('inf'), NetworkState.GRIDLOCK,
     'Network is near gridlock. Immediate intervention required.'),
]

_CLASSIFICATION_TABLE_CACHE = None
_CALIBRATING_DESC_CACHE = 'Collecting baseline data to establish peak production.'


def _load_classification_config() -> tuple:
    """Loads classification thresholds from config/mfd_classification_thresholds.json with caching and fallback."""
    global _CLASSIFICATION_TABLE_CACHE, _CALIBRATING_DESC_CACHE
    if _CLASSIFICATION_TABLE_CACHE is not None:
        return _CLASSIFICATION_TABLE_CACHE, _CALIBRATING_DESC_CACHE

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(base_dir, "config", "mfd_classification_thresholds.json")

    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw_table = data.get("classification_table", [])
                table = []
                for entry in raw_table:
                    thresh = float('inf') if entry.get("threshold") is None else float(entry.get("threshold"))
                    state = entry.get("state", NetworkState.GRIDLOCK)
                    desc = entry.get("description", "")
                    table.append((thresh, state, desc))
                if table:
                    _CLASSIFICATION_TABLE_CACHE = table
                    _CALIBRATING_DESC_CACHE = data.get("calibrating_description", _CALIBRATING_DESC_CACHE)
                    logging.info(f"[MFD_CLASSIFIER] Loaded classification thresholds from {json_path}")
                    return _CLASSIFICATION_TABLE_CACHE, _CALIBRATING_DESC_CACHE
        except Exception as e:
            logging.warning(f"[MFD_CLASSIFIER] Failed to load JSON '{json_path}': {e}. Using fallback.")

    _CLASSIFICATION_TABLE_CACHE = _DEFAULT_CLASSIFICATION_TABLE
    return _CLASSIFICATION_TABLE_CACHE, _CALIBRATING_DESC_CACHE



class MFDClassifier:
    """
    Classifies network operating state and generates performance reports
    based on MFD metrics.
    """

    @staticmethod
    def classify(congestion_ratio: float, is_warmed_up: bool, language: str = "pt_br") -> tuple:
        """
        Determines the current network state based on the congestion ratio.

        Args:
            congestion_ratio: Current accumulation / critical accumulation.
            is_warmed_up: Whether the tracker has enough data for reliable classification.
            language: Target language code for localized description.

        Returns:
            Tuple of (state_name: str, description: str).
        """
        table, calibrating_desc = _load_classification_config()
        lang_key = (language or "pt_br").lower()

        if not is_warmed_up:
            desc_text = calibrating_desc.get(lang_key, calibrating_desc.get("pt_br", calibrating_desc.get("en", ""))) if isinstance(calibrating_desc, dict) else calibrating_desc
            return (
                NetworkState.CALIBRATING,
                desc_text
            )

        for threshold, state, description in table:
            if congestion_ratio < threshold:
                desc_text = description.get(lang_key, description.get("pt_br", description.get("en", ""))) if isinstance(description, dict) else description
                return state, desc_text

        # Fallback (should never reach here due to inf threshold)
        return NetworkState.GRIDLOCK, 'Unknown congestion state.'

    @staticmethod
    def generate_report(tracker: MFDTracker) -> Dict[str, Any]:
        """
        Generates a comprehensive network performance report.
        Suitable for logging, API responses, or dashboard display.

        Args:
            tracker: The MFDTracker instance containing historical state.

        Returns:
            Dictionary with full network performance data.
        """
        latest = tracker.get_latest()
        smoothed = tracker.get_smoothed_metrics()

        if latest is None:
            return {
                'status': 'NO_DATA',
                'message': 'MFD has not received any traffic data yet.'
            }

        # Classify current state
        state, state_description = MFDClassifier.classify(
            latest.congestion_ratio,
            tracker.is_warmed_up
        )

        return {
            'status': 'OK',
            'network_state': state,
            'network_state_description': state_description,
            'current': latest.to_dict(),
            'peak': {
                'production': round(tracker.peak_production, 4),
                'accumulation_at_peak': round(tracker.peak_accumulation, 4)
            },
            'smoothed': smoothed,
            'total_steps': tracker.step_count,
            'history_size': tracker.history_size
        }
