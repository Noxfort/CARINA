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

# File: src/sas/report_data_normalizer.py
# Author: Gabriel Moraes
# Date: July 27, 2026

from typing import Any, Dict, Set

class ReportDataNormalizer:
    """Handles data structure normalization and statistical calculation for traffic reports."""

    @staticmethod
    def normalize_junctions(junctions_input: Any) -> Dict[str, Any]:
        """Normalizes lists or tuples of junction dicts into a keyed dictionary."""
        if isinstance(junctions_input, dict):
            return junctions_input
        res = {}
        if isinstance(junctions_input, (list, tuple)):
            for idx, item in enumerate(junctions_input):
                if isinstance(item, dict):
                    j_id = str(item.get("id") or item.get("junction_id") or f"J{idx+1}")
                    res[j_id] = item
                else:
                    j_id = f"J{idx+1}"
                    res[j_id] = {"id": j_id, "data": item}
        return res

    @staticmethod
    def calculate_statistics(analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Computes counts, saturation criticality, categorized junction IDs, and peak metrics."""
        add_count = 0
        optimize_count = 0
        remove_count = 0
        keep_count = 0
        no_signal_count = 0
        critical_j_ids: Set[str] = set()

        add_junction_ids = []
        optimize_junction_ids = []
        remove_junction_ids = []
        keep_junction_ids = []
        no_signal_junction_ids = []

        max_sat_val = -1.0
        max_sat_j_id = "N/A"
        max_delay_val = -1.0
        max_delay_j_id = "N/A"

        for j_id, j_data in analysis_results.items():
            d = j_data.get("data", {}) if isinstance(j_data.get("data"), dict) else j_data
            sat_val = float(d.get("saturation_ratio", 0.0) or 0.0)
            delay_val = float(d.get("average_delay", 0.0) or 0.0)

            if sat_val > max_sat_val:
                max_sat_val = sat_val
                max_sat_j_id = j_id

            if delay_val > max_delay_val:
                max_delay_val = delay_val
                max_delay_j_id = j_id

            if sat_val > 0.85:
                critical_j_ids.add(j_id)

            rec_raw = str(j_data.get("recommendation", "")).lower()
            is_optimize = "otimizar" in rec_raw or "optimize" in rec_raw or "remodelar" in rec_raw
            is_add = ("adicionar" in rec_raw or "add" in rec_raw) and not is_optimize
            is_remove = "remover" in rec_raw or "remove" in rec_raw
            is_no_signal = "não sinalizado" in rec_raw or "no_signal" in rec_raw or "unsignalized" in rec_raw

            if is_optimize:
                optimize_count += 1
                optimize_junction_ids.append(j_id)
            elif is_add:
                add_count += 1
                add_junction_ids.append(j_id)
            elif is_remove:
                remove_count += 1
                remove_junction_ids.append(j_id)
            elif is_no_signal:
                no_signal_count += 1
                no_signal_junction_ids.append(j_id)
            else:
                keep_count += 1
                keep_junction_ids.append(j_id)

        total_junctions = len(analysis_results)
        signalized_count = keep_count + optimize_count + remove_count
        unsignalized_count = add_count + no_signal_count

        total_interventions = add_count + optimize_count + remove_count
        intervention_rate = (total_interventions / total_junctions) if total_junctions > 0 else 0.0

        return {
            "total_junctions": total_junctions,
            "add_count": add_count,
            "optimize_count": optimize_count,
            "remove_count": remove_count,
            "keep_count": keep_count,
            "no_signal_count": no_signal_count,
            "signalized_count": signalized_count,
            "unsignalized_count": unsignalized_count,
            "intervention_rate": intervention_rate,
            "critical_j_ids": critical_j_ids,
            "add_junction_ids": add_junction_ids,
            "optimize_junction_ids": optimize_junction_ids,
            "remove_junction_ids": remove_junction_ids,
            "keep_junction_ids": keep_junction_ids,
            "no_signal_junction_ids": no_signal_junction_ids,
            "max_saturation_val": max_sat_val if max_sat_val >= 0 else 0.0,
            "max_saturation_junction_id": max_sat_j_id,
            "max_delay_val": max_delay_val if max_delay_val >= 0 else 0.0,
            "max_delay_junction_id": max_delay_j_id
        }
