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


class NetworkState:
    """Enumeration of possible network operating states."""
    CALIBRATING = 'CALIBRATING'
    FREE_FLOW = 'FREE_FLOW'
    APPROACHING_CAPACITY = 'APPROACHING_CAPACITY'
    MILD_CONGESTION = 'MILD_CONGESTION'
    HEAVY_CONGESTION = 'HEAVY_CONGESTION'
    GRIDLOCK = 'GRIDLOCK'


# Classification thresholds: (max_congestion_ratio, state, description)
# Ordered from lowest to highest. First match wins.
# To add a new state, simply insert a new tuple — no existing code changes needed (OCP).
_CLASSIFICATION_TABLE = [
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


class MFDClassifier:
    """
    Classifies network operating state and generates performance reports
    based on MFD metrics.
    """

    @staticmethod
    def classify(congestion_ratio: float, is_warmed_up: bool) -> tuple:
        """
        Determines the current network state based on the congestion ratio.

        Args:
            congestion_ratio: Current accumulation / critical accumulation.
            is_warmed_up: Whether the tracker has enough data for reliable classification.

        Returns:
            Tuple of (state_name: str, description: str).
        """
        if not is_warmed_up:
            return (
                NetworkState.CALIBRATING,
                'Collecting baseline data to establish peak production.'
            )

        for threshold, state, description in _CLASSIFICATION_TABLE:
            if congestion_ratio < threshold:
                return state, description

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
