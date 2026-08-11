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

# File: src/xai/mfd_comparison_engine.py
# Author: Gabriel Moraes
# Date: July 03, 2026

from typing import Dict, Any
from mfd.mfd_metrics_calculator import _classify_outcome, _safe_pct

class MFDComparisonEngine:
    """Computes comparison dimensions (delta changes and outcomes) vs first and last baselines."""

    @staticmethod
    def compare_since_last(current_raw: dict, last_data: dict, speed_factor: float, speed_label: str) -> dict:
        avg_speed = current_raw.get("global_stats", {}).get("average_speed_m_s", 0.0)
        avg_global_queue_raw = current_raw.get("global_stats", {}).get("average_queue_length", 0.0)
        avg_eff = current_raw.get("global_stats", {}).get("average_efficiency", 0.0)

        last_global_speed = last_data.get("global_stats", {}).get("average_speed_m_s", 0.0)
        last_global_queue = last_data.get("global_stats", {}).get("average_queue_length", 0.0)
        last_global_eff = last_data.get("global_stats", {}).get("average_efficiency", 0.0)

        global_speed_change_last = _safe_pct(avg_speed, last_global_speed) if last_global_speed > 0 else 0.0
        global_queue_change_last = _safe_pct(avg_global_queue_raw, last_global_queue) if last_global_queue > 0 else 0.0
        global_eff_change_last = _safe_pct(avg_eff, last_global_eff) if last_global_eff > 0 else 0.0
        global_outcome_last = _classify_outcome(global_speed_change_last) if last_global_speed > 0 else "FIRST_ANALYSIS"

        last_intersections = last_data.get("intersections_stats", {})
        intersection_comparisons_last = {}
        for tl_id, curr_raw_inter in current_raw.get("intersections_stats", {}).items():
            prev = last_intersections.get(tl_id)
            if prev:
                spd_change = _safe_pct(curr_raw_inter["average_speed_m_s"], prev.get("average_speed_m_s", 0.0))
                q_diff = curr_raw_inter["average_queue_length"] - prev.get("average_queue_length", 0.0)
                q_change_pct = _safe_pct(curr_raw_inter["average_queue_length"], prev.get("average_queue_length", 0.0))
                intersection_comparisons_last[tl_id] = {
                    "outcome": _classify_outcome(spd_change),
                    "speed_change_pct": round(spd_change, 2),
                    "queue_change_value": int(round(q_diff)),
                    "queue_change_pct": round(q_change_pct, 2),
                    "previous_speed": round(prev.get("average_speed_m_s", 0.0) * speed_factor, 2),
                    "current_speed": round(curr_raw_inter["average_speed_m_s"] * speed_factor, 2),
                    "previous_queue": int(round(prev.get("average_queue_length", 0.0))),
                    "current_queue": int(round(curr_raw_inter["average_queue_length"]))
                }
            else:
                intersection_comparisons_last[tl_id] = {
                    "outcome": "FIRST_ANALYSIS",
                    "speed_change_pct": 0.0,
                    "queue_change_value": 0,
                    "queue_change_pct": 0.0,
                    "previous_speed": 0.0,
                    "current_speed": round(curr_raw_inter["average_speed_m_s"] * speed_factor, 2),
                    "previous_queue": 0,
                    "current_queue": int(round(curr_raw_inter["average_queue_length"]))
                }

        return {
            "last_analysis_timestamp": last_data.get("timestamp") or "Primeira Análise / First Analysis",
            "global_outcome": global_outcome_last,
            "global_speed_change_pct": round(global_speed_change_last, 2),
            "global_queue_change_pct": round(global_queue_change_last, 2),
            "global_efficiency_change_pct": round(global_eff_change_last, 2),
            "previous_speed": round(last_global_speed * speed_factor, 2),
            "current_speed": round(avg_speed * speed_factor, 2),
            "previous_queue": int(round(last_global_queue)),
            "current_queue": int(round(avg_global_queue_raw)),
            "queue_change_value": int(round(avg_global_queue_raw - last_global_queue)),
            "previous_efficiency": round(last_global_eff, 4),
            "current_efficiency": round(avg_eff, 4),
            "efficiency_change_pct": round(global_eff_change_last, 2),
            "intersection_comparisons": intersection_comparisons_last
        }

    @staticmethod
    def compare_since_first(current_raw: dict, first_data: dict, speed_factor: float, speed_label: str) -> dict:
        avg_speed = current_raw.get("global_stats", {}).get("average_speed_m_s", 0.0)
        avg_global_queue_raw = current_raw.get("global_stats", {}).get("average_queue_length", 0.0)
        avg_eff = current_raw.get("global_stats", {}).get("average_efficiency", 0.0)

        first_global_speed = first_data.get("global_stats", {}).get("average_speed_m_s", 0.0)
        first_global_queue = first_data.get("global_stats", {}).get("average_queue_length", 0.0)
        first_global_eff = first_data.get("global_stats", {}).get("average_efficiency", 0.0)

        global_speed_change_first = _safe_pct(avg_speed, first_global_speed) if first_global_speed > 0 else 0.0
        global_queue_change_first = _safe_pct(avg_global_queue_raw, first_global_queue) if first_global_queue > 0 else 0.0
        global_eff_change_first = _safe_pct(avg_eff, first_global_eff) if first_global_eff > 0 else 0.0
        global_outcome_first = _classify_outcome(global_speed_change_first) if first_global_speed > 0 else "FIRST_ANALYSIS"

        first_intersections = first_data.get("intersections_stats", {})
        intersection_comparisons_global = {}
        for tl_id, curr_raw_inter in current_raw.get("intersections_stats", {}).items():
            baseline = first_intersections.get(tl_id)
            if baseline:
                spd_change = _safe_pct(curr_raw_inter["average_speed_m_s"], baseline.get("average_speed_m_s", 0.0))
                q_diff = curr_raw_inter["average_queue_length"] - baseline.get("average_queue_length", 0.0)
                q_change_pct = _safe_pct(curr_raw_inter["average_queue_length"], baseline.get("average_speed_m_s", 0.0))
                intersection_comparisons_global[tl_id] = {
                    "outcome": _classify_outcome(spd_change),
                    "speed_change_pct": round(spd_change, 2),
                    "queue_change_value": int(round(q_diff)),
                    "queue_change_pct": round(q_change_pct, 2),
                    "baseline_speed": round(baseline.get("average_speed_m_s", 0.0) * speed_factor, 2),
                    "current_speed": round(curr_raw_inter["average_speed_m_s"] * speed_factor, 2),
                    "baseline_queue": int(round(baseline.get("average_queue_length", 0.0))),
                    "current_queue": int(round(curr_raw_inter["average_queue_length"]))
                }
            else:
                intersection_comparisons_global[tl_id] = {
                    "outcome": "FIRST_ANALYSIS",
                    "speed_change_pct": 0.0,
                    "queue_change_value": 0,
                    "queue_change_pct": 0.0,
                    "baseline_speed": 0.0,
                    "current_speed": round(curr_raw_inter["average_speed_m_s"] * speed_factor, 2),
                    "baseline_queue": 0,
                    "current_queue": int(round(curr_raw_inter["average_queue_length"]))
                }

        return {
            "first_analysis_timestamp": first_data.get("timestamp") or "Primeira Análise / First Analysis",
            "global_outcome": global_outcome_first,
            "global_speed_change_pct": round(global_speed_change_first, 2),
            "global_queue_change_pct": round(global_queue_change_first, 2),
            "global_efficiency_change_pct": round(global_eff_change_first, 2),
            "baseline_speed": round(first_global_speed * speed_factor, 2),
            "current_speed": round(avg_speed * speed_factor, 2),
            "baseline_queue": int(round(first_global_queue)),
            "current_queue": int(round(avg_global_queue_raw)),
            "intersection_comparisons": intersection_comparisons_global
        }
