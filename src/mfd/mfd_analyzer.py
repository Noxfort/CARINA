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

# File: src/mfd/mfd_analyzer.py
# Author: Gabriel Moraes
# Date: July 03, 2026

from mfd.mfd_baseline_manager import MFDReportBaselineManager
from mfd.mfd_metrics_calculator import MFDMetricsCalculator
from mfd.mfd_comparison_engine import MFDComparisonEngine

class MFDAnalyzer:
    """
    Responsibility: Coordinates calculation of macroscopic fundamental diagram metrics,
    averages, trend detection (comparing simulation halves), and historical comparisons.
    Acts purely as an orchestrator.
    """

    @staticmethod
    def analyze(history: list, peak_prod: float, peak_accum: float, scenario_results_dir: str = None,
                scenario_name: str = None, db_manager=None) -> dict:
        if not history:
            return {}

        # 1. Load baseline history files (last + first)
        last_data, first_data = MFDReportBaselineManager.load_baselines(
            scenario_results_dir=scenario_results_dir,
            scenario_name=scenario_name,
            db_manager=db_manager
        )

        # 2. Calculate current run metrics, averages, trends and raw stats
        metrics = MFDMetricsCalculator.calculate_current_run_metrics(history)

        # 3. Persist current raw analysis for future runs
        MFDReportBaselineManager.save_baselines(
            scenario_results_dir=scenario_results_dir,
            current_analysis_snapshot=metrics["raw_snapshot"],
            scenario_name=scenario_name,
            db_manager=db_manager
        )

        # 4. Format current run speed units and vehicles counts
        formatting = MFDMetricsCalculator.format_current_metrics(
            global_speed=metrics["avg_speed"],
            global_queue=metrics["avg_global_queue_raw"],
            intersection_raw_stats=metrics["intersection_raw_stats"],
            avg_eff=metrics["avg_eff"],
            avg_prod=metrics["avg_prod"],
            avg_accum=metrics["avg_accum"]
        )

        # 5. Compute comparison dimensions
        comparison_last = MFDComparisonEngine.compare_since_last(
            current_raw=metrics["raw_snapshot"],
            last_data=last_data,
            speed_factor=formatting["speed_factor"],
            speed_label=formatting["speed_label"]
        )

        comparison_first = MFDComparisonEngine.compare_since_first(
            current_raw=metrics["raw_snapshot"],
            first_data=first_data,
            speed_factor=formatting["speed_factor"],
            speed_label=formatting["speed_label"]
        )

        # 6. Build and return structured output
        return {
            "total_steps": metrics["total_steps"],
            "peak_production": round(peak_prod * formatting["speed_factor"], 4),
            "critical_accumulation_veh": int(round(peak_accum)),
            "average_production": round(metrics["avg_prod"] * formatting["speed_factor"], 4),
            "average_accumulation_veh": int(round(metrics["avg_accum"])),
            "average_speed": round(metrics["avg_speed"] * formatting["speed_factor"], 2),
            "average_queue_length": int(round(metrics["avg_global_queue_raw"])),
            "average_efficiency": round(metrics["avg_eff"], 4),
            "max_efficiency": round(metrics["max_eff"], 4),
            "min_efficiency": round(metrics["min_eff"], 4),
            "network_state_percentages": metrics["state_pct"],
            "speed_unit": formatting["speed_label"],

            "trend_analysis_current_run": {
                "average_speed_first_half": round(metrics["avg_speed_first"] * formatting["speed_factor"], 2),
                "average_speed_second_half": round(metrics["avg_speed_second"] * formatting["speed_factor"], 2),
                "speed_improvement_percentage": round(metrics["speed_diff_pct"], 2),
                "efficiency_first_half": round(metrics["avg_eff_first"], 4),
                "efficiency_second_half": round(metrics["avg_eff_second"], 4),
                "efficiency_improvement_percentage": round(metrics["eff_diff_pct"], 2),
                "overall_traffic_outcome": metrics["trend"]
            },

            "intersections_current": formatting["intersection_current_stats"],

            "comparison_since_last_analysis": {
                "last_analysis_timestamp": comparison_last["last_analysis_timestamp"],
                "current_analysis_timestamp": metrics["current_timestamp"],
                "global_outcome": comparison_last["global_outcome"],
                "previous_speed": comparison_last["previous_speed"],
                "current_speed": comparison_last["current_speed"],
                "global_speed_change_pct": comparison_last["global_speed_change_pct"],
                "previous_queue": comparison_last["previous_queue"],
                "current_queue": comparison_last["current_queue"],
                "global_queue_change_pct": comparison_last["global_queue_change_pct"],
                "previous_efficiency": comparison_last["previous_efficiency"],
                "current_efficiency": comparison_last["current_efficiency"],
                "global_efficiency_change_pct": comparison_last["global_efficiency_change_pct"],
                "intersection_comparisons": comparison_last["intersection_comparisons"]
            },

            "comparison_since_first_analysis": {
                "first_analysis_timestamp": comparison_first["first_analysis_timestamp"],
                "current_analysis_timestamp": metrics["current_timestamp"],
                "global_outcome": comparison_first["global_outcome"],
                "global_speed_change_pct": comparison_first["global_speed_change_pct"],
                "global_queue_change_pct": comparison_first["global_queue_change_pct"],
                "global_efficiency_change_pct": comparison_first["global_efficiency_change_pct"],
                "baseline_speed": comparison_first["baseline_speed"],
                "current_speed": comparison_first["current_speed"],
                "baseline_queue": comparison_first["baseline_queue"],
                "current_queue": comparison_first["current_queue"],
                "intersection_comparisons": comparison_first["intersection_comparisons"]
            }
        }
