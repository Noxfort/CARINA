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

# File: src/sas/report_intersection_processor.py
# Author: Gabriel Moraes
# Date: August 10, 2026

from typing import Dict, Any, Tuple
from sas.report_template_provider import ReportTemplateProvider


class ReportIntersectionProcessor:
    """
    Extracts physical geometry attributes, metrics, and formatted labels for single intersections.
    """

    @staticmethod
    def extract_physical_geometry(d: Dict[str, Any]) -> Tuple[int, int, float, float, float, float]:
        """
        Extracts primary and secondary edge physical attributes (lanes, speed limits, lengths).

        Args:
            d (Dict[str, Any]): Junction internal data dictionary.

        Returns:
            Tuple[int, int, float, float, float, float]:
                (lanes_p, lanes_s, speed_p, speed_s, len_p, len_s)
        """
        p_edges = d.get("primary_edges", {})
        lanes_p, speed_p, len_p = 1, 50.0, 100.0
        if isinstance(p_edges, dict) and p_edges:
            first_p_samples = next(iter(p_edges.values()), [])
            if first_p_samples and isinstance(first_p_samples, list) and isinstance(first_p_samples[0], dict):
                s_p = first_p_samples[0]
                lanes_p = int(s_p.get("num_lanes") or 1)
                spd_p_raw = float(s_p.get("speed_limit") or 13.89)
                speed_p = spd_p_raw * 3.6 if spd_p_raw < 35.0 else spd_p_raw
                len_p = float(s_p.get("edge_length") or 100.0)

        s_edges = d.get("secondary_edges", {})
        lanes_s, speed_s, len_s = 1, 40.0, 100.0
        if isinstance(s_edges, dict) and s_edges:
            first_s_samples = next(iter(s_edges.values()), [])
            if first_s_samples and isinstance(first_s_samples, list) and isinstance(first_s_samples[0], dict):
                s_s = first_s_samples[0]
                lanes_s = int(s_s.get("num_lanes") or 1)
                spd_s_raw = float(s_s.get("speed_limit") or 11.11)
                speed_s = spd_s_raw * 3.6 if spd_s_raw < 35.0 else spd_s_raw
                len_s = float(s_s.get("edge_length") or 100.0)

        lanes_p = int(d.get("lanes_primary") or lanes_p)
        lanes_s = int(d.get("lanes_secondary") or lanes_s)
        speed_p = float(d.get("speed_primary") or speed_p)
        speed_s = float(d.get("speed_secondary") or speed_s)
        len_p = float(d.get("len_primary") or len_p)
        len_s = float(d.get("len_secondary") or len_s)

        return lanes_p, lanes_s, speed_p, speed_s, len_p, len_s

    @classmethod
    def process_single_intersection(
        cls,
        j_id: Any,
        j_data: Dict[str, Any],
        stats: Dict[str, Any],
        ui_language: str = "pt_br"
    ) -> Dict[str, Any]:
        """
        Parses junction metrics, determines recommendation status, extracts geometry,
        and constructs normalized data structure for single intersection reports.

        Args:
            j_id (Any): Junction ID.
            j_data (Dict[str, Any]): Raw junction data dictionary.
            stats (Dict[str, Any]): Pre-computed network statistics dictionary.
            ui_language (str): UI language code (e.g. 'pt_br').

        Returns:
            Dict[str, Any]: Struct containing formatted strings and numerical attributes.
        """
        clean_j_id = str(j_id)
        d = j_data.get("data", {}) if isinstance(j_data.get("data"), dict) else j_data

        vol_p = float(d.get("vol_primary_val") or d.get("vol_primary") or 0.0)
        vol_s = float(d.get("vol_secondary_val") or d.get("vol_secondary") or 0.0)
        delay = float(d.get("avg_delay") or 0.0)
        queue = int(d.get("queue_p95") or d.get("max_queue") or 0)
        sat = float(d.get("saturation_ratio") or 0.0)

        rec_raw = str(j_data.get("recommendation", "")).lower()
        is_optimize = "otimizar" in rec_raw or "optimize" in rec_raw or "remodelar" in rec_raw
        is_add = ("adicionar" in rec_raw or "add" in rec_raw) and not is_optimize
        is_remove = "remover" in rec_raw or "remove" in rec_raw
        is_no_signal = "não sinalizado" in rec_raw or "no_signal" in rec_raw or "unsignalized" in rec_raw
        is_keep = not (is_add or is_optimize or is_remove or is_no_signal)

        rec_formatted = ReportTemplateProvider.get_recommendation_labels(
            is_add, is_remove, is_keep, is_no_signal, ui_language, is_optimize=is_optimize
        )

        coherent_status_raw = "Não Sinalizado" if (is_add or is_no_signal) else "Sinalizado"
        status_formatted = ReportTemplateProvider.get_status_label(coherent_status_raw, ui_language)
        is_critical = j_id in stats.get("critical_j_ids", set()) or sat > 0.85

        lanes_p, lanes_s, speed_p, speed_s, len_p, len_s = cls.extract_physical_geometry(d)

        return {
            "clean_j_id": clean_j_id,
            "recommendation": rec_formatted,
            "current_status": status_formatted,
            "coherent_status_raw": coherent_status_raw,
            "vol_primary_val": vol_p,
            "vol_secondary_val": vol_s,
            "avg_delay": delay,
            "queue_p95": queue,
            "saturation_ratio": sat,
            "is_critical": is_critical,
            "lanes_p": lanes_p,
            "lanes_s": lanes_s,
            "speed_p": speed_p,
            "speed_s": speed_s,
            "len_p": len_p,
            "len_s": len_s
        }
