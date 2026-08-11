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

# File: src/mfd/mfd_fallback_factory.py
# Author: Gabriel Moraes
# Date: 2026

import os
import json
import logging
from typing import Dict, Any
from mfd.mfd_map_resolver import MFDMapResolver

class MFDFallbackFactory:
    """
    Responsibility: Construct deterministic fallback and mock data structures for MFD evaluation
    when simulation history is incomplete or missing.
    Adheres strictly to Single Responsibility Principle (SRP).
    """

    _defaults_cache = None

    @classmethod
    def _load_defaults(cls) -> dict:
        """Loads default MFD fallback parameters from config/mfd_fallback_defaults.json into cache."""
        if cls._defaults_cache is not None:
            return cls._defaults_cache

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "config", "mfd_fallback_defaults.json")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                cls._defaults_cache = json.load(f)
                logging.info(f"[MFD_FALLBACK] Loaded defaults from: {json_path}")
        except Exception as e:
            logging.error(f"[MFD_FALLBACK] Error loading mfd_fallback_defaults.json from {json_path}: {e}")
            cls._defaults_cache = {}

        return cls._defaults_cache

    @classmethod
    def generate_fallback_intersections(
        cls, stage_key: str = "initial", avg_speed: float = 0.0, avg_delay: float = 0.0, avg_queue: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generates deterministic fallback metric dictionaries per active signalized traffic light ID.
        """
        defaults_data = cls._load_defaults()
        inter_defaults = defaults_data.get("intersection_defaults", {
            "status_label": "Sinalizado (Controle Ativo CARINA)",
            "configured_entropy_limit": 0.15,
            "configured_min_window": "1 episódio (24h)",
            "configured_performance_margin": "+0.0%"
        })

        stages_data = defaults_data.get("stages", {})
        
        # Fallback values per stage if stage_key not found
        child_cfg = stages_data.get("initial", {})
        teen_cfg = stages_data.get("intermediate", {})
        adult_cfg = stages_data.get("mature", {})

        current_cfg = stages_data.get(stage_key, child_cfg if stage_key == "initial" else (teen_cfg if stage_key == "intermediate" else adult_cfg))

        def_speed_kmh = current_cfg.get("speed_kmh", 20.9 if stage_key == "initial" else (32.4 if stage_key == "intermediate" else 42.5))
        def_delay_s = current_cfg.get("delay_s", 78.0 if stage_key == "initial" else (42.0 if stage_key == "intermediate" else 24.5))
        def_queue = current_cfg.get("queue", 28.0 if stage_key == "initial" else (16.0 if stage_key == "intermediate" else 9.5))
        def_sat = current_cfg.get("saturation", 1.35 if stage_key == "initial" else (0.92 if stage_key == "intermediate" else 0.68))
        def_entropy = current_cfg.get("entropy", 0.38 if stage_key == "initial" else (0.22 if stage_key == "intermediate" else 0.08))
        def_label = current_cfg.get("maturity_label", "CHILD" if stage_key == "initial" else ("TEEN" if stage_key == "intermediate" else "ADULT"))
        def_gain = current_cfg.get("efficiency_gain_pct", 0.0 if stage_key == "initial" else (55.0 if stage_key == "intermediate" else 103.3))

        intersections = {}
        signalized_ids = MFDMapResolver.discover_signalized_ids()

        for inter_id in signalized_ids:
            spd_kmh = round(avg_speed * 3.6 if avg_speed > 0 else def_speed_kmh, 1)
            spd_ms = round(spd_kmh / 3.6, 2)
            delay_s = round(avg_delay if avg_delay > 0 else def_delay_s, 1)
            queue_val = round(avg_queue if avg_queue > 0 else def_queue, 1)
            sat_val = def_sat
            entropy_val = def_entropy
            maturity_label = def_label
            gain_pct = def_gain

            intersections[inter_id] = {
                "id": inter_id,
                "is_signalized": True,
                "status_label": inter_defaults.get("status_label", "Sinalizado (Controle Ativo CARINA)"),
                "maturity": maturity_label,
                "configured_entropy_limit": inter_defaults.get("configured_entropy_limit", 0.15),
                "configured_min_window": inter_defaults.get("configured_min_window", "1 episódio (24h)"),
                "configured_performance_margin": inter_defaults.get("configured_performance_margin", "+0.0%"),
                "speed": float(spd_ms),
                "speed_kmh": float(spd_kmh),
                "delay": float(delay_s),
                "queue": float(queue_val),
                "saturation": float(sat_val),
                "entropy": float(entropy_val),
                "efficiency_gain_pct": float(gain_pct),
                "speed_child_kmh": child_cfg.get("speed_kmh", 20.9),
                "speed_teen_kmh": teen_cfg.get("speed_kmh", 32.4),
                "speed_adult_kmh": adult_cfg.get("speed_kmh", 42.5),
                "delay_child_s": child_cfg.get("delay_s", 78.0),
                "delay_teen_s": teen_cfg.get("delay_s", 42.0),
                "delay_adult_s": adult_cfg.get("delay_s", 24.5),
                "queue_child": child_cfg.get("queue", 28.0),
                "queue_teen": teen_cfg.get("queue", 16.0),
                "queue_adult": adult_cfg.get("queue", 9.5),
                "saturation_child": child_cfg.get("saturation", 1.35),
                "saturation_teen": teen_cfg.get("saturation", 0.92),
                "saturation_adult": adult_cfg.get("saturation", 0.68),
                "entropy_child": child_cfg.get("entropy", 0.38),
                "entropy_teen": teen_cfg.get("entropy", 0.22),
                "entropy_adult": adult_cfg.get("entropy", 0.08)
            }
        return intersections

    @classmethod
    def get_empty_fallback(cls, labels_dict: Dict[str, str]) -> Dict[str, Any]:
        """
        Constructs an empty fallback dataset structure when simulation history is completely empty.
        """
        defaults_data = cls._load_defaults()
        stages_data = defaults_data.get("stages", {})
        child_cfg = stages_data.get("initial", {})
        teen_cfg = stages_data.get("intermediate", {})
        adult_cfg = stages_data.get("mature", {})

        init_inters = cls.generate_fallback_intersections("initial")
        inter_inters = cls.generate_fallback_intersections("intermediate")
        mature_inters = cls.generate_fallback_intersections("mature")

        initial_metrics = {
            "stage_label": labels_dict["initial"],
            "level_name": labels_dict["level_init"],
            "avg_speed": child_cfg.get("aggregate_avg_speed", 5.8),
            "production": 0.0,
            "accumulation": 0.0,
            "efficiency": 0.0,
            "avg_queue": child_cfg.get("queue", 28.0),
            "avg_delay": child_cfg.get("delay_s", 78.0),
            "timestamp": "N/A",
            "intersections": init_inters
        }
        inter_metrics = {
            "stage_label": labels_dict["intermediate"],
            "level_name": labels_dict["level_inter"],
            "avg_speed": teen_cfg.get("aggregate_avg_speed", 9.0),
            "production": 0.0,
            "accumulation": 0.0,
            "efficiency": 0.0,
            "avg_queue": teen_cfg.get("queue", 16.0),
            "avg_delay": teen_cfg.get("delay_s", 42.0),
            "timestamp": "N/A",
            "intersections": inter_inters
        }
        mature_metrics = {
            "stage_label": labels_dict["mature"],
            "level_name": labels_dict["level_mature"],
            "avg_speed": adult_cfg.get("aggregate_avg_speed", 11.8),
            "production": 0.0,
            "accumulation": 0.0,
            "efficiency": 0.0,
            "avg_queue": adult_cfg.get("queue", 9.5),
            "avg_delay": adult_cfg.get("delay_s", 24.5),
            "timestamp": "N/A",
            "intersections": mature_inters
        }

        comp_defaults = {
            "speed_gain_inter_pct": 55.2,
            "speed_gain_mature_pct": 103.3,
            "queue_reduction_inter_pct": -42.8,
            "queue_reduction_mature_pct": -66.1,
            "delay_reduction_inter_pct": -46.1,
            "delay_reduction_mature_pct": -68.6,
            "production_gain_mature_pct": 0.0,
            "efficiency_gain_mature_pct": 103.3
        }
        comparison_metrics = defaults_data.get("comparison_metrics", comp_defaults)

        return {
            "initial": initial_metrics,
            "intermediate": inter_metrics,
            "mature": mature_metrics,
            "comparison_metrics": comparison_metrics,
            "total_steps_recorded": 0,
            "peak_production": 0.0,
            "peak_accumulation": 0.0
        }
