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

# File: src/mfd/mfd_impact_calculator.py
# Author: Gabriel Moraes
# Date: August 8, 2026

import logging
from typing import Dict, Any, List

from mfd.mfd_impact_labels import MFDImpactLabels
from mfd.mfd_zone_calculator import MFDZoneCalculator
from mfd.mfd_intersection_metrics_calculator import MFDIntersectionMetricsCalculator

class MFDImpactCalculator:
    """
    Orchestrator / Facade: Coordinates physical, operational, and socio-environmental impact metric
    calculations across DA SILVA maturation stages by delegating specialized sub-tasks to dedicated
    SOLID component calculators.
    """

    # Backward-compatible attribute reference to EVAL_LABELS
    EVAL_LABELS = MFDImpactLabels.load_labels_config()

    @staticmethod
    def calculate_full_impacts(stages_data: Dict[str, Any], history: List[Dict[str, Any]] = None, lang: str = "pt_br") -> Dict[str, Any]:
        """
        Orchestrate complete impact evaluation across physical speed, production, queue, delay, efficiency,
        zone statistics, and socio-environmental metrics.

        :param stages_data: Extracted stage data dictionary (initial, intermediate, mature)
        :param history: List of historical accumulation and network telemetry data points
        :param lang: Language locale string for evaluation labels
        :return: Fully structured impact evaluation metrics dictionary
        """
        initial = stages_data.get("initial", {})
        inter = stages_data.get("intermediate", {})
        mature = stages_data.get("mature", {})
        peak_accum = stages_data.get("peak_accumulation", 1.0)

        # 1. Speed Unit Conversion (m/s to km/h check) and capping
        speed_init_raw = initial.get("avg_speed", 0.0)
        speed_inter_raw = inter.get("avg_speed", 0.0)
        speed_mature_raw = mature.get("avg_speed", 0.0)

        speed_init_kmh = speed_init_raw * 3.6 if 0.0 < speed_init_raw < 35.0 else speed_init_raw
        speed_inter_kmh = speed_inter_raw * 3.6 if 0.0 < speed_inter_raw < 35.0 else speed_inter_raw
        speed_mature_kmh = speed_mature_raw * 3.6 if 0.0 < speed_mature_raw < 35.0 else speed_mature_raw

        if speed_mature_kmh > 48.5:
            speed_mature_kmh = 42.5

        # 2. Global Metric Delta Calculations
        calc_delta = MFDIntersectionMetricsCalculator.calc_pct_delta
        speed_delta_pct = calc_delta(speed_init_kmh, speed_mature_kmh)

        prod_init = initial.get("production", 0.0)
        prod_mature = mature.get("production", 0.0)
        prod_delta_pct = calc_delta(prod_init, prod_mature)

        queue_init = initial.get("avg_queue", 0.0)
        queue_mature = mature.get("avg_queue", 0.0)
        queue_delta_pct = calc_delta(queue_init, queue_mature)

        delay_init = initial.get("avg_delay", 0.0)
        delay_mature = mature.get("avg_delay", 0.0)
        delay_delta_pct = calc_delta(delay_init, delay_mature)

        eff_init = initial.get("efficiency", 0.0)
        eff_mature = mature.get("efficiency", 0.0)
        eff_delta_pct = calc_delta(eff_init, eff_mature)

        # 3. Zone Distribution Calculation
        zone_stats = MFDZoneCalculator.calculate_zone_distribution(history, peak_accum)

        # 4. Socio-Environmental Metrics Calculation (Man-Hours Saved)
        accum_mature = mature.get("accumulation", 500.0)
        total_vehicles = max(accum_mature, 100.0)

        delay_saved_per_veh = max(0.0, delay_init - delay_mature)
        total_delay_saved_sec = delay_saved_per_veh * total_vehicles * 100
        man_hours_saved_daily = (total_delay_saved_sec * 1.3) / 3600.0

        # 5. Per-Intersection Metrics Calculation
        intersections_table = MFDIntersectionMetricsCalculator.process_intersections_table(initial, inter, mature)

        # 6. Aggregate Fallback Means if Global Snapshots were Zero
        if speed_init_kmh <= 0.0 and intersections_table:
            speed_init_kmh = sum(r["speed_child_kmh"] for r in intersections_table) / len(intersections_table)
            speed_inter_kmh = sum(r["speed_teen_kmh"] for r in intersections_table) / len(intersections_table)
            speed_mature_kmh = sum(r["speed_adult_kmh"] for r in intersections_table) / len(intersections_table)
            speed_delta_pct = calc_delta(speed_init_kmh, speed_mature_kmh)

        if delay_init <= 0.0 and intersections_table:
            delay_init = sum(r["delay_child_s"] for r in intersections_table) / len(intersections_table)
            delay_inter = sum(r["delay_teen_s"] for r in intersections_table) / len(intersections_table)
            delay_mature = sum(r["delay_adult_s"] for r in intersections_table) / len(intersections_table)
            delay_delta_pct = calc_delta(delay_init, delay_mature)

        if queue_init <= 0.0 and intersections_table:
            queue_init = sum(r["queue_child"] for r in intersections_table) / len(intersections_table)
            queue_inter = sum(r["queue_teen"] for r in intersections_table) / len(intersections_table)
            queue_mature = sum(r["queue_adult"] for r in intersections_table) / len(intersections_table)
            queue_delta_pct = calc_delta(queue_init, queue_mature)

        # 7. Localized Metric Evaluation Labels Resolution
        eval_labels = MFDImpactLabels.resolve_metric_evaluations(
            speed_delta_pct=speed_delta_pct,
            prod_delta_pct=prod_delta_pct,
            queue_delta_pct=queue_delta_pct,
            delay_delta_pct=delay_delta_pct,
            eff_delta_pct=eff_delta_pct,
            lang=lang
        )

        return {
            "comparative_table": {
                "speed_kmh": {
                    "initial": round(speed_init_kmh, 2),
                    "intermediate": round(speed_inter_kmh, 2),
                    "mature": round(speed_mature_kmh, 2),
                    "delta_pct": round(speed_delta_pct, 1),
                    "evaluation": eval_labels["speed"]
                },
                "production": {
                    "initial": round(prod_init, 1),
                    "intermediate": round(inter.get("production", 0.0), 1),
                    "mature": round(prod_mature, 1),
                    "delta_pct": round(prod_delta_pct, 1),
                    "evaluation": eval_labels["production"]
                },
                "queue": {
                    "initial": round(queue_init, 1),
                    "intermediate": round(inter.get("avg_queue", 0.0), 1),
                    "mature": round(queue_mature, 1),
                    "delta_pct": round(queue_delta_pct, 1),
                    "evaluation": eval_labels["queue"]
                },
                "delay": {
                    "initial": round(delay_init, 1),
                    "intermediate": round(inter.get("avg_delay", 0.0), 1),
                    "mature": round(delay_mature, 1),
                    "delta_pct": round(delay_delta_pct, 1),
                    "evaluation": eval_labels["delay"]
                },
                "efficiency": {
                    "initial": round(eff_init, 4),
                    "intermediate": round(inter.get("efficiency", 0.0), 4),
                    "mature": round(eff_mature, 4),
                    "delta_pct": round(eff_delta_pct, 1),
                    "evaluation": eval_labels["efficiency"]
                }
            },
            "intersections_table": intersections_table,
            "mfd_zones": zone_stats,
            "socio_environmental": {
                "man_hours_saved_daily": round(man_hours_saved_daily, 1),
                "speed_gain_mature_pct": round(speed_delta_pct, 1),
                "delay_reduction_mature_pct": round(abs(delay_delta_pct), 1),
                "production_gain_mature_pct": round(prod_delta_pct, 1)
            }
        }

    @staticmethod
    def _calc_pct_delta(val_base: float, val_target: float) -> float:
        """Backward compatible helper method for percentage delta calculation."""
        return MFDIntersectionMetricsCalculator.calc_pct_delta(val_base, val_target)

    @staticmethod
    def _calculate_zone_distribution(history: List[Dict[str, Any]], peak_accum: float) -> Dict[str, Any]:
        """Backward compatible helper method for MFD zone calculation."""
        return MFDZoneCalculator.calculate_zone_distribution(history, peak_accum)
