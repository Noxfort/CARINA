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

# File: src/xai/mfd_metrics_calculator.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import time
from typing import Dict, Any, List
from mfd.classifier import MFDClassifier
from utils.settings_manager import SettingsManager

def _classify_outcome(speed_change_pct: float) -> str:
    """Classify a speed change percentage into IMPROVED, STABLE, or WORSENED."""
    if speed_change_pct > 3.0:
        return "IMPROVED"
    elif speed_change_pct < -3.0:
        return "WORSENED"
    return "STABLE"


def _safe_pct(current: float, previous: float) -> float:
    """Calculate safe percentage change: ((current - previous) / previous) * 100."""
    if previous > 0:
        return ((current - previous) / previous) * 100.0
    return 0.0


class MFDMetricsCalculator:
    """Calculates basic averages, trends, per-intersection stats, and unit formatting."""

    @staticmethod
    def calculate_current_run_metrics(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_steps = len(history)
        if total_steps == 0:
            return {}

        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Basic Averages
        sum_prod = sum(s.get("production", 0.0) for s in history)
        sum_accum = sum(s.get("accumulation", 0.0) for s in history)
        sum_speed = sum(s.get("mean_speed", 0.0) for s in history)
        sum_eff = sum(s.get("efficiency", 0.0) for s in history)

        avg_prod = sum_prod / total_steps
        avg_accum = sum_accum / total_steps
        avg_speed = sum_speed / total_steps
        avg_eff = sum_eff / total_steps

        max_eff = max(s.get("efficiency", 0.0) for s in history)
        min_eff = min(s.get("efficiency", 0.0) for s in history)

        # 2. Network State breakdown
        state_counts = {}
        for s in history:
            c_ratio = s.get("congestion_ratio", 0.0)
            state, _ = MFDClassifier.classify(c_ratio, is_warmed_up=True)
            state_counts[state] = state_counts.get(state, 0) + 1

        state_pct = {state: round((count / total_steps) * 100, 2) for state, count in state_counts.items()}

        # 3. Trend analysis: compare first half vs second half of current run
        half_idx = total_steps // 2
        first_half = history[:half_idx] if half_idx > 0 else history
        second_half = history[half_idx:] if half_idx > 0 else history

        avg_speed_first = sum(s.get("mean_speed", 0.0) for s in first_half) / len(first_half) if first_half else 0.0
        avg_speed_second = sum(s.get("mean_speed", 0.0) for s in second_half) / len(second_half) if second_half else 0.0

        avg_eff_first = sum(s.get("efficiency", 0.0) for s in first_half) / len(first_half) if first_half else 0.0
        avg_eff_second = sum(s.get("efficiency", 0.0) for s in second_half) / len(second_half) if second_half else 0.0

        speed_diff_pct = _safe_pct(avg_speed_second, avg_speed_first)
        eff_diff_pct = _safe_pct(avg_eff_second, avg_eff_first)
        trend = _classify_outcome(speed_diff_pct)

        # 4. Per-intersection stats (this run)
        intersection_ids = []
        for s in reversed(history):
            inters = s.get("intersections", {})
            if inters:
                intersection_ids = list(inters.keys())
                break

        intersection_raw_stats = {}
        for tl_id in intersection_ids:
            speeds = []
            queues = []
            prods = []
            accums = []

            for step in history:
                inter = step.get("intersections", {}).get(tl_id)
                if inter:
                    speeds.append(inter.get("mean_speed", 0.0))
                    queues.append(inter.get("queue_length", 0.0))
                    prods.append(inter.get("production", 0.0))
                    accums.append(inter.get("accumulation", 0.0))

            avg_spd = sum(speeds) / len(speeds) if speeds else 0.0
            avg_q = sum(queues) / len(queues) if queues else 0.0
            avg_prd = sum(prods) / len(prods) if prods else 0.0
            avg_acc = sum(accums) / len(accums) if accums else 0.0

            intersection_raw_stats[tl_id] = {
                "average_speed_m_s": round(avg_spd, 2),
                "average_queue_length": round(avg_q, 2),
                "average_production": round(avg_prd, 4),
                "average_accumulation": round(avg_acc, 4)
            }

        avg_global_queue_raw = sum(
            intersection_raw_stats[tid]["average_queue_length"] for tid in intersection_ids
        ) / len(intersection_ids) if intersection_ids else 0.0

        # Construct raw snapshot dictionary
        raw_snapshot = {
            "timestamp": current_timestamp,
            "global_stats": {
                "average_speed_m_s": round(avg_speed, 2),
                "average_queue_length": round(avg_global_queue_raw, 2),
                "average_efficiency": round(avg_eff, 4),
                "average_production": round(avg_prod, 4)
            },
            "intersections_stats": intersection_raw_stats
        }

        return {
            "total_steps": total_steps,
            "raw_snapshot": raw_snapshot,
            "avg_speed": avg_speed,
            "avg_global_queue_raw": avg_global_queue_raw,
            "avg_eff": avg_eff,
            "avg_prod": avg_prod,
            "avg_accum": avg_accum,
            "max_eff": max_eff,
            "min_eff": min_eff,
            "state_pct": state_pct,
            "avg_speed_first": avg_speed_first,
            "avg_speed_second": avg_speed_second,
            "speed_diff_pct": speed_diff_pct,
            "avg_eff_first": avg_eff_first,
            "avg_eff_second": avg_eff_second,
            "eff_diff_pct": eff_diff_pct,
            "trend": trend,
            "intersection_ids": intersection_ids,
            "intersection_raw_stats": intersection_raw_stats,
            "current_timestamp": current_timestamp
        }

    @staticmethod
    def get_speed_factors() -> tuple[float, str]:
        settings = SettingsManager().load_settings()
        speed_unit = settings.get("xai_speed_unit", "m/s").lower()
        if speed_unit == "km/h":
            return 3.6, "km/h"
        elif speed_unit in ["imperial", "mph"]:
            return 2.23694, "mph"
        return 1.0, "m/s"

    @classmethod
    def format_current_metrics(cls, global_speed: float, global_queue: float, intersection_raw_stats: dict,
                               avg_eff: float, avg_prod: float, avg_accum: float) -> dict:
        speed_factor, speed_label = cls.get_speed_factors()

        intersection_current_stats = {}
        for tl_id, raw in intersection_raw_stats.items():
            intersection_current_stats[tl_id] = {
                "average_speed": round(raw["average_speed_m_s"] * speed_factor, 2),
                "average_queue_length": int(round(raw["average_queue_length"])),
                "average_production": round(raw["average_production"] * speed_factor, 2),
                "average_accumulation": int(round(raw["average_accumulation"]))
            }

        return {
            "speed_factor": speed_factor,
            "speed_label": speed_label,
            "intersection_current_stats": intersection_current_stats
        }
