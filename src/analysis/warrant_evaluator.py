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

# File: src/analysis/warrant_evaluator.py (V2 — Traffic Engineering Mathematics)
# Author: Gabriel Moraes
# Date: April 22, 2026

# -*- coding: utf-8 -*-
"""
WarrantEvaluator V2 — Proper Traffic Engineering Analysis.

This module replaces the previous simplistic warrant evaluation with
mathematically correct traffic engineering formulas:

  Warrant 1 (Volume):     q = k × (v × 3.6)       — Fundamental Flow Equation
  Warrant 2 (Delay):      D = L/v_real - L/v_limit — Real Delay Calculation
  Warrant 3 (Queue P95):  P95 of queue_length       — Statistical Queue Analysis
  Warrant 4 (Saturation): X = q / (N × F_ideal)    — Volume/Capacity Ratio

All data comes from the historical traffic_samples table in the database,
populated by the TrafficDataRecorder from Synapse gRPC TrafficFrames.
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

logger = logging.getLogger(__name__)

# ===========================================================================
# CONSTANTS — Traffic Engineering
# ===========================================================================
# Ideal saturation flow per lane (veh/hour/lane).
# Standard value used in HCM (Highway Capacity Manual) methodology.
F_IDEAL_DEFAULT = 1800

# Speed unit conversion factor: m/s -> km/h
MS_TO_KMH = 3.6

# Minimum speed threshold to avoid division-by-zero (m/s ~ 0.36 km/h)
MIN_SPEED_THRESHOLD = 0.1


class WarrantEvaluator:
    """
    Evaluates traffic engineering warrants to determine whether a traffic
    light is justified at a given junction, using data from the database.
    """

    def __init__(self, analysis_params: dict, true_traffic_light_ids: list, locale_manager: 'LocaleManagerBackend'):
        """
        Initializes the evaluator.

        Args:
            analysis_params: Dict with thresholds from settings.ini.
            true_traffic_light_ids: List of junction IDs that currently have traffic lights.
            locale_manager: Locale manager for translated recommendation strings.
        """
        self.params = analysis_params
        self.true_tl_ids = true_traffic_light_ids
        self.lm = locale_manager

        # Extract thresholds with sane defaults
        self.min_volume_primary = self.params.get('min_volume_primary', 500)
        self.min_volume_secondary = self.params.get('min_volume_secondary', 150)
        self.unacceptable_delay = self.params.get('unacceptable_delay', 90.0)
        self.max_queue_p95 = self.params.get('max_queue_p95', 15)
        self.saturation_critical = self.params.get('saturation_critical', 0.85)
        self.f_ideal = self.params.get('ideal_flow_per_lane', F_IDEAL_DEFAULT)
        self.removal_threshold = self.params.get('removal_threshold_percent', 60.0)
        self.conflict_threshold = self.params.get('conflict_threshold', 10)

        logger.debug("WarrantEvaluator V2 initialized with traffic engineering formulas.")

    def evaluate(self, junction_id: str, junction_data: dict) -> dict | None:
        """
        Evaluates all warrants for a single junction.

        Args:
            junction_id: The junction identifier.
            junction_data: Dict with keys:
                - 'primary_edges': {edge_id: [list of sample dicts]}
                - 'secondary_edges': {edge_id: [list of sample dicts]}
                - 'conflict_events': int (legacy, kept for compatibility)
                - 'type': str (junction type from topology)

        Returns:
            A result dict with warrants, recommendation, and data, or None.
        """
        if not junction_data:
            return None

        primary_edges = junction_data.get('primary_edges', {})
        secondary_edges = junction_data.get('secondary_edges', {})
        all_edges = {**primary_edges, **secondary_edges}

        if not all_edges:
            return None

        # === WARRANT 1: Volume (Fundamental Flow Equation) ===
        w1_result = self._warrant_1_volume(primary_edges, secondary_edges)

        # === WARRANT 2: Delay (Real Delay Calculation) ===
        w2_result = self._warrant_2_delay(secondary_edges)

        # === WARRANT 3: Queue P95 (Statistical Queue Analysis) ===
        w3_result = self._warrant_3_queue_p95(all_edges)

        # === WARRANT 4: Saturation (V/C Ratio) ===
        w4_result = self._warrant_4_saturation(all_edges)

        # --- DECISION LOGIC ---
        has_traffic_light = junction_id in self.true_tl_ids
        warrants_met = sum([w1_result['met'], w2_result['met'], w3_result['met'], w4_result['met']])

        recommendation, justification = self._make_recommendation(
            has_traffic_light, warrants_met, w1_result, w2_result, w3_result, w4_result
        )

        current_status = self.lm.get_string("warrant_evaluator.has_tl") if has_traffic_light else self.lm.get_string("warrant_evaluator.no_tl")

        return {
            'recommendation': recommendation,
            'current_status': current_status,
            'justification': justification,
            'warrants': {
                'volume': w1_result['met'],
                'delay': w2_result['met'],
                'queue_p95': w3_result['met'],
                'saturation': w4_result['met'],
            },
            'data': {
                'vol_primary_val': w1_result.get('avg_volume_primary', 0),
                'vol_secondary_val': w1_result.get('avg_volume_secondary', 0),
                'avg_delay': w2_result.get('avg_delay', 0),
                'queue_p95': w3_result.get('p95_value', 0),
                'saturation_ratio': w4_result.get('max_x_ratio', 0),
                'conflict_events': junction_data.get('conflict_events', 0),
            },
            'warrant_details': {
                'w1': w1_result,
                'w2': w2_result,
                'w3': w3_result,
                'w4': w4_result,
            }
        }

    # =========================================================================
    # WARRANT 1: Volume — Fundamental Flow Equation
    #   q = k × (v × 3.6)
    #   k = density (veh/km), v = mean_speed (m/s)
    #   q = volume in vehicles per hour (vph)
    # =========================================================================
    def _warrant_1_volume(self, primary_edges: dict, secondary_edges: dict) -> dict:
        """Evaluates Warrant 1 using the fundamental flow equation."""
        vol_primary = self._compute_avg_volume(primary_edges)
        vol_secondary = self._compute_avg_volume(secondary_edges)

        met = (vol_primary >= self.min_volume_primary and
               vol_secondary >= self.min_volume_secondary)

        return {
            'met': met,
            'avg_volume_primary': round(vol_primary, 1),
            'avg_volume_secondary': round(vol_secondary, 1),
            'threshold_primary': self.min_volume_primary,
            'threshold_secondary': self.min_volume_secondary,
        }

    def _compute_avg_volume(self, edges: dict) -> float:
        """Computes average volume across all edges using q = k × (v × 3.6)."""
        all_volumes = []
        for edge_id, samples in edges.items():
            for s in samples:
                density = s.get('density', 0)
                speed = s.get('mean_speed', 0)
                q = density * (speed * MS_TO_KMH)  # veh/hour
                all_volumes.append(q)
        return sum(all_volumes) / len(all_volumes) if all_volumes else 0.0

    # =========================================================================
    # WARRANT 2: Delay — Real Delay Calculation
    #   D = L / v_real - L / v_limit
    #   L = edge length (m), v_real = actual speed (m/s), v_limit = speed limit (m/s)
    #   D = delay per vehicle in seconds
    # =========================================================================
    def _warrant_2_delay(self, secondary_edges: dict) -> dict:
        """Evaluates Warrant 2 using the real delay formula on secondary edges."""
        all_delays = []

        for edge_id, samples in secondary_edges.items():
            for s in samples:
                edge_length = s.get('edge_length', 0)
                v_real = s.get('mean_speed', 0)
                v_limit = s.get('speed_limit', 0)

                if edge_length > 0 and v_real > MIN_SPEED_THRESHOLD and v_limit > MIN_SPEED_THRESHOLD:
                    delay = (edge_length / v_real) - (edge_length / v_limit)
                    all_delays.append(max(0.0, delay))  # Delay cannot be negative

        avg_delay = sum(all_delays) / len(all_delays) if all_delays else 0.0
        met = avg_delay > self.unacceptable_delay

        return {
            'met': met,
            'avg_delay': round(avg_delay, 2),
            'threshold': self.unacceptable_delay,
            'sample_count': len(all_delays),
        }

    # =========================================================================
    # WARRANT 3: Queue P95 — Statistical Queue Analysis
    #   Instead of using the simple average (which masks oscillations between
    #   green=0 and red=20 → avg=10), we use the 95th Percentile (P95).
    #   P95 = value below which 95% of queue measurements fall.
    # =========================================================================
    def _warrant_3_queue_p95(self, all_edges: dict) -> dict:
        """Evaluates Warrant 3 using P95 of queue_length across all edges."""
        all_queues = []

        for edge_id, samples in all_edges.items():
            for s in samples:
                all_queues.append(s.get('queue_length', 0))

        if all_queues:
            sorted_queues = sorted(all_queues)
            idx = int(len(sorted_queues) * 0.95)
            p95 = sorted_queues[min(idx, len(sorted_queues) - 1)]
        else:
            p95 = 0

        met = p95 > self.max_queue_p95

        return {
            'met': met,
            'p95_value': p95,
            'threshold': self.max_queue_p95,
            'sample_count': len(all_queues),
            'avg_queue': round(sum(all_queues) / len(all_queues), 1) if all_queues else 0,
        }

    # =========================================================================
    # WARRANT 4: Saturation — Volume/Capacity Ratio (V/C = X)
    #   X = q / C
    #   C = N × F_ideal  (capacity in veh/hour)
    #   N = number of lanes, F_ideal = ideal flow per lane (~1800 vph)
    #   If X > 0.85, the road is technically in collapse.
    # =========================================================================
    def _warrant_4_saturation(self, all_edges: dict) -> dict:
        """Evaluates Warrant 4 using the V/C saturation ratio."""
        edge_ratios = {}

        for edge_id, samples in all_edges.items():
            volumes = []
            num_lanes = 1
            for s in samples:
                density = s.get('density', 0)
                speed = s.get('mean_speed', 0)
                q = density * (speed * MS_TO_KMH)
                volumes.append(q)
                nl = s.get('num_lanes')
                if nl and nl > 0:
                    num_lanes = nl

            avg_q = sum(volumes) / len(volumes) if volumes else 0.0
            capacity = num_lanes * self.f_ideal
            x_ratio = avg_q / capacity if capacity > 0 else 0.0
            edge_ratios[edge_id] = round(x_ratio, 4)

        max_x = max(edge_ratios.values()) if edge_ratios else 0.0
        met = max_x > self.saturation_critical

        return {
            'met': met,
            'max_x_ratio': round(max_x, 4),
            'threshold': self.saturation_critical,
            'edge_ratios': edge_ratios,
        }

    # =========================================================================
    # DECISION LOGIC
    # =========================================================================
    def _make_recommendation(self, has_tl: bool, warrants_met: int,
                             w1: dict, w2: dict, w3: dict, w4: dict) -> tuple:
        """
        Determines the final recommendation based on warrant results.

        Returns:
            Tuple of (recommendation_string, justification_string).
        """
        rec_add = self.lm.get_string("warrant_evaluator.rec_add")
        rec_remove = self.lm.get_string("warrant_evaluator.rec_remove")
        rec_keep = self.lm.get_string("warrant_evaluator.rec_keep")

        if has_tl:
            # Junction HAS a traffic light — should we remove it?
            if warrants_met == 0:
                justification = self.lm.get_string("warrant_evaluator.justify_remove_no_warrants")
                return rec_remove, justification
            elif warrants_met <= 1:
                # Only 1 warrant met: check if volume is below removal threshold
                vol_primary = w1.get('avg_volume_primary', 0)
                removal_vol = self.min_volume_primary * (self.removal_threshold / 100.0)
                if vol_primary < removal_vol:
                    justification = self.lm.get_string("warrant_evaluator.justify_remove_low_volume")
                    return rec_remove, justification
            # Otherwise keep
            justification = self.lm.get_string("warrant_evaluator.justify_keep", count=warrants_met)
            return rec_keep, justification
        else:
            # Junction does NOT have a traffic light — should we add one?
            if warrants_met >= 2:
                justification = self.lm.get_string("warrant_evaluator.justify_add", count=warrants_met)
                return rec_add, justification
            elif w4.get('met'):
                # Saturation alone is critical enough
                justification = self.lm.get_string("warrant_evaluator.justify_add_saturation")
                return rec_add, justification
            else:
                justification = self.lm.get_string("warrant_evaluator.justify_keep_no_tl", count=warrants_met)
                return rec_keep, justification