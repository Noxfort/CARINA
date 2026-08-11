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

# File: src/mfd/mfd_stage_aggregator.py
# Author: Gabriel Moraes
# Date: 2026

from typing import Dict, Any, List
from mfd.mfd_fallback_factory import MFDFallbackFactory

class MFDStageAggregator:
    """
    Responsibility: Perform pure memory-based mathematical aggregation of traffic snapshots
    across DA SILVA maturation stages (CHILD, TEEN, ADULT).
    Adheres strictly to Single Responsibility Principle (SRP).
    """

    @staticmethod
    def aggregate_snapshots(snaps: List[Dict[str, Any]], level_name: str, stage_label: str, stage_key: str) -> Dict[str, Any]:
        """
        Calculates exact mathematical averages across ALL snapshots belonging to a maturity stage.
        """
        if not snaps:
            return MFDStageAggregator.summarize_single_snapshot({}, level_name=level_name, stage_label=stage_label, stage_key=stage_key)
        
        n = len(snaps)
        avg_speed = sum(s.get("mean_speed", s.get("avg_speed", s.get("speed", 0.0))) for s in snaps) / n
        avg_prod = sum(s.get("production", 0.0) for s in snaps) / n
        avg_accum = sum(s.get("accumulation", 0.0) for s in snaps) / n
        avg_eff = sum(s.get("efficiency", 0.0) for s in snaps) / n
        avg_queue = sum(s.get("avg_queue", s.get("queue_length", s.get("queue", 0.0))) for s in snaps) / n
        avg_delay = sum(s.get("avg_delay", s.get("delay", 0.0)) for s in snaps) / n

        inter_sums = {}
        inter_counts = {}
        for s in snaps:
            inters = s.get("intersections", s.get("intersection_metrics", {}))
            for inter_id, inter_data in inters.items():
                if inter_id not in inter_sums:
                    inter_sums[inter_id] = {
                        "speed": 0.0, "delay": 0.0, "queue": 0.0, "saturation": 0.0, "entropy": 0.0,
                        "is_signalized": inter_data.get("is_signalized", True),
                        "status_label": inter_data.get("status_label", "Sinalizado (Controle Ativo CARINA)")
                    }
                    inter_counts[inter_id] = 0

                spd_val = inter_data.get("mean_speed", inter_data.get("speed", inter_data.get("speed_kmh", 0.0) / 3.6 if "speed_kmh" in inter_data else 0.0))
                queue_val = inter_data.get("queue_length", inter_data.get("queue", inter_data.get("queue_child", 0.0)))
                
                inter_sums[inter_id]["speed"] += float(spd_val)
                inter_sums[inter_id]["delay"] += float(inter_data.get("delay", inter_data.get("delay_child_s", 0.0)))
                inter_sums[inter_id]["queue"] += float(queue_val)
                inter_sums[inter_id]["saturation"] += float(inter_data.get("saturation", inter_data.get("saturation_child", 0.0)))
                inter_sums[inter_id]["entropy"] += float(inter_data.get("entropy", inter_data.get("entropy_child", 0.0)))
                inter_counts[inter_id] += 1

        aggregated_intersections = {}
        if inter_sums:
            for inter_id, sums in inter_sums.items():
                c = max(1, inter_counts[inter_id])
                spd_ms = sums["speed"] / c
                spd_kmh = round(spd_ms * 3.6 if spd_ms < 35.0 else spd_ms, 1)
                
                aggregated_intersections[inter_id] = {
                    "id": inter_id,
                    "speed": float(spd_ms),
                    "speed_kmh": float(spd_kmh),
                    "delay": round(sums["delay"] / c, 1),
                    "queue": round(sums["queue"] / c, 1),
                    "saturation": round(sums["saturation"] / c, 2),
                    "entropy": round(sums["entropy"] / c, 2),
                    "maturity": "CHILD" if stage_key == "initial" else ("TEEN" if stage_key == "intermediate" else "ADULT"),
                    "is_signalized": sums["is_signalized"],
                    "status_label": sums["status_label"],
                    "configured_entropy_limit": 0.15,
                    "configured_min_window": "1 episódio (24h)",
                    "configured_performance_margin": "+0.0%"
                }
        else:
            aggregated_intersections = MFDFallbackFactory.generate_fallback_intersections(
                stage_key=stage_key, avg_speed=avg_speed, avg_delay=avg_delay, avg_queue=avg_queue
            )

        return {
            "stage_label": stage_label,
            "level_name": level_name,
            "avg_speed": float(avg_speed),
            "production": float(avg_prod),
            "accumulation": float(avg_accum),
            "efficiency": float(avg_eff),
            "avg_queue": float(avg_queue),
            "avg_delay": float(avg_delay),
            "timestamp": snaps[0].get("timestamp", "N/A"),
            "intersections": aggregated_intersections
        }

    @staticmethod
    def summarize_single_snapshot(point: Dict[str, Any], level_name: str, stage_label: str, stage_key: str = "initial") -> Dict[str, Any]:
        """
        Summarizes representative metrics from a single snapshot point.
        """
        avg_speed = point.get("mean_speed", point.get("avg_speed", point.get("speed", 0.0)))
        production = point.get("production", 0.0)
        accumulation = point.get("accumulation", 0.0)
        efficiency = point.get("efficiency", 0.0)
        avg_queue = point.get("avg_queue", point.get("queue_length", point.get("queue", 0.0)))
        avg_delay = point.get("avg_delay", point.get("delay", 0.0))

        intersections = point.get("intersections", point.get("intersection_metrics", {}))
        if not intersections:
            intersections = MFDFallbackFactory.generate_fallback_intersections(
                stage_key=stage_key,
                avg_speed=avg_speed,
                avg_delay=avg_delay,
                avg_queue=avg_queue
            )

        return {
            "stage_label": stage_label,
            "level_name": level_name,
            "avg_speed": float(avg_speed),
            "production": float(production),
            "accumulation": float(accumulation),
            "efficiency": float(efficiency),
            "avg_queue": float(avg_queue),
            "avg_delay": float(avg_delay),
            "timestamp": point.get("timestamp", "N/A"),
            "intersections": intersections
        }

    @staticmethod
    def calculate_comparative_metrics(initial_metrics: Dict[str, Any], inter_metrics: Dict[str, Any], mature_metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculates percentage deltas for speed gain, delay reduction, queue reduction, production, and efficiency
        between Linha Base (CHILD) and ADULT stages.
        """
        speed_init = initial_metrics.get("avg_speed", 0.0)
        speed_inter = inter_metrics.get("avg_speed", 0.0)
        speed_mature = mature_metrics.get("avg_speed", 0.0)

        queue_init = initial_metrics.get("avg_queue", 0.0)
        queue_inter = inter_metrics.get("avg_queue", 0.0)
        queue_mature = mature_metrics.get("avg_queue", 0.0)

        delay_init = initial_metrics.get("avg_delay", 0.0)
        delay_inter = inter_metrics.get("avg_delay", 0.0)
        delay_mature = mature_metrics.get("avg_delay", 0.0)

        prod_init = initial_metrics.get("production", 0.0)
        prod_mature = mature_metrics.get("production", 0.0)

        eff_init = initial_metrics.get("efficiency", 0.0)
        eff_mature = mature_metrics.get("efficiency", 0.0)

        speed_gain_inter_pct = ((speed_inter - speed_init) / speed_init * 100.0) if speed_init > 0 else 0.0
        speed_gain_mature_pct = ((speed_mature - speed_init) / speed_init * 100.0) if speed_init > 0 else 0.0

        queue_red_inter_pct = ((queue_inter - queue_init) / queue_init * 100.0) if queue_init > 0 else 0.0
        queue_red_mature_pct = ((queue_mature - queue_init) / queue_init * 100.0) if queue_init > 0 else 0.0

        delay_red_inter_pct = ((delay_inter - delay_init) / delay_init * 100.0) if delay_init > 0 else 0.0
        delay_red_mature_pct = ((delay_mature - delay_init) / delay_init * 100.0) if delay_init > 0 else 0.0

        prod_gain_mature_pct = ((prod_mature - prod_init) / prod_init * 100.0) if prod_init > 0 else 0.0
        eff_gain_mature_pct = ((eff_mature - eff_init) / eff_init * 100.0) if eff_init > 0 else 0.0

        return {
            "speed_gain_inter_pct": round(speed_gain_inter_pct, 2),
            "speed_gain_mature_pct": round(speed_gain_mature_pct, 2),
            "queue_reduction_inter_pct": round(queue_red_inter_pct, 2),
            "queue_reduction_mature_pct": round(queue_red_mature_pct, 2),
            "delay_reduction_inter_pct": round(delay_red_inter_pct, 2),
            "delay_reduction_mature_pct": round(delay_red_mature_pct, 2),
            "production_gain_mature_pct": round(prod_gain_mature_pct, 2),
            "efficiency_gain_mature_pct": round(eff_gain_mature_pct, 2)
        }
