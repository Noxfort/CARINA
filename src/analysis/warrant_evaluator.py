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
# ORCHESTRATOR
# ===========================================================================
from analysis.warrant_strategies import VolumeWarrant, DelayWarrant, QueueWarrant, SaturationWarrant

class WarrantEvaluator:
    """
    Orchestrates traffic engineering warrants to determine whether a traffic
    light is justified at a given junction, delegating logic to Strategy classes.
    """

    def __init__(self, analysis_params: dict, true_traffic_light_ids: list, locale_manager: 'LocaleManagerBackend'):
        self.params = analysis_params
        self.true_tl_ids = true_traffic_light_ids
        self.lm = locale_manager

        # Extract thresholds used directly in decision logic
        self.min_volume_primary = self.params.get('min_volume_primary', 500)
        self.removal_threshold = self.params.get('removal_threshold_percent', 60.0)

        # Strategy Pattern Registry
        self.warrants = {
            'w1': VolumeWarrant(),
            'w2': DelayWarrant(),
            'w3': QueueWarrant(),
            'w4': SaturationWarrant()
        }

        logger.debug("WarrantEvaluator V2 initialized with Strategy Pattern.")

    def evaluate(self, junction_id: str, junction_data: dict) -> dict | None:
        if not junction_data:
            return None

        primary_edges = junction_data.get('primary_edges', {})
        secondary_edges = junction_data.get('secondary_edges', {})
        all_edges = {**primary_edges, **secondary_edges}

        if not all_edges:
            # If we don't have edges but have legacy data, we can still proceed
            if not ('volume' in junction_data or 'vol_secondary' in junction_data):
                return None

        # Execute all strategies dynamically
        results = {}
        strategy_params = {**self.params, '_legacy_data': junction_data}
        for key, strategy in self.warrants.items():
            results[key] = strategy.evaluate(all_edges, primary_edges, secondary_edges, strategy_params)

        w1_result = results['w1']
        w2_result = results['w2']
        w3_result = results['w3']
        w4_result = results['w4']

        # --- DECISION LOGIC & PHYSICAL COUPLING ---
        has_traffic_light = junction_id in self.true_tl_ids
        warrants_met = sum([w1_result['met'], w2_result['met'], w3_result['met'], w4_result['met']])

        recommendation, justification = self._make_recommendation(
            has_traffic_light, warrants_met, w1_result, w2_result, w3_result, w4_result
        )

        current_status = self.lm.get_string("warrant_evaluator.has_tl") if has_traffic_light else self.lm.get_string("warrant_evaluator.no_tl")

        # Apply physical coupling: D = f(X) and P95 = f(X)
        from analysis.warrant_math import apply_saturation_coupling
        raw_delay = w2_result.get('avg_delay', 0.0)
        raw_queue = w3_result.get('p95_value', 0.0)
        sat_x = w4_result.get('max_x_ratio', 0.0)
        coupled_delay, coupled_queue = apply_saturation_coupling(raw_delay, raw_queue, sat_x)

        # Keep backwards compatibility for ReportGenerator
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
                'avg_delay': coupled_delay,
                'queue_p95': coupled_queue,
                'saturation_ratio': sat_x,
                'conflict_events': junction_data.get('conflict_events', 0),
            },
            'warrant_details': results
        }

    # =========================================================================
    # DECISION LOGIC
    # =========================================================================
    def _make_recommendation(self, has_tl: bool, warrants_met: int,
                             w1: dict, w2: dict, w3: dict, w4: dict) -> tuple:
        """
        Determines the final recommendation based on warrant results and status coherence.
        """
        rec_add = self.lm.get_string("warrant_evaluator.rec_add", default="ADICIONAR SEMÁFORO")
        rec_optimize = self.lm.get_string("warrant_evaluator.rec_optimize", default="OTIMIZAR SEMÁFORO")
        rec_keep = self.lm.get_string("warrant_evaluator.rec_keep", default="MANTER SEMÁFORO")
        rec_no_signal = self.lm.get_string("warrant_evaluator.rec_no_signal", default="MANTER NÃO SINALIZADO")

        saturation_critical = w4.get('met', False) or (w4.get('max_x_ratio', 0.0) > 0.85)

        if has_tl:
            # Status Atual == "Sinalizado"
            if saturation_critical or warrants_met >= 1:
                justification = "O cruzamento já é sinalizado e opera sob alta demanda ou warrants normativos, recomendando-se a otimização dos tempos de ciclo e sincronização viária."
                return rec_optimize, justification
            else:
                justification = self.lm.get_string("warrant_evaluator.justify_keep", count=warrants_met)
                return rec_keep, justification
        else:
            # Status Atual == "Não Sinalizado"
            if saturation_critical or warrants_met >= 1:
                justification = self.lm.get_string("warrant_evaluator.justify_add_saturation") if saturation_critical else self.lm.get_string("warrant_evaluator.justify_add", count=warrants_met)
                return rec_add, justification
            else:
                justification = self.lm.get_string("warrant_evaluator.justify_keep_no_tl", count=warrants_met)
                return rec_no_signal, justification