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

# File: src/sas/report_prompt_builder.py
# Author: Gabriel Moraes
# Date: July 25, 2026

from typing import Dict, Any, Optional
from sas.sas_helpers import formatar_br

class ReportPromptBuilder:
    """Builds structured inputs and prompts for LLM Transducer inference."""

    @staticmethod
    def build_executive_summary_input(analysis_results: Dict[str, Any], light_results: Dict[str, Any], intervention_rate: float = 0.0, add_count: int = 0, optimize_count: int = 0, keep_count: int = 0, signalized_count: int = 0, unsignalized_count: int = 0, time_window_str: str = "") -> Dict[str, Any]:
        """Constructs input dictionary for executive summary generation including optimization and addition counts."""
        total_j = len(analysis_results)
        return {
            "mode": "EXECUTIVE_SUMMARY",
            "language": "pt_br",
            "intervention_rate": intervention_rate,
            "intervention_rate_fmt": formatar_br(intervention_rate, 2),
            "time_window": time_window_str,
            "attributions": {
                "intersections_count": total_j,
                "qtd_total_cruzamentos": total_j,
                "intervention_rate": formatar_br(intervention_rate, 2),
                "time_window": time_window_str,
                "add_count": add_count,
                "optimize_count": optimize_count,
                "keep_count": keep_count,
                "signalized_count": signalized_count,
                "unsignalized_count": unsignalized_count,
                "qtd_sinalizados_criticos": optimize_count,
                "qtd_nao_sinalizados_criticos": add_count,
                "summary": "Análise técnica da malha viária"
            }
        }

    @staticmethod
    def build_single_intersection_input(clean_j_id: str, single_intersection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Constructs input dictionary for single intersection narrative justification with pre-formatted numeric strings."""
        formatted_data = dict(single_intersection_data)
        if "vol_primary_val" in formatted_data and isinstance(formatted_data["vol_primary_val"], (int, float)):
            formatted_data["vol_primary_fmt"] = formatar_br(formatted_data["vol_primary_val"], 1)
        if "vol_secondary_val" in formatted_data and isinstance(formatted_data["vol_secondary_val"], (int, float)):
            formatted_data["vol_secondary_fmt"] = formatar_br(formatted_data["vol_secondary_val"], 1)
        if "delay" in formatted_data and isinstance(formatted_data["delay"], (int, float)):
            formatted_data["delay_fmt"] = formatar_br(formatted_data["delay"], 1)
        if "saturation" in formatted_data and isinstance(formatted_data["saturation"], (int, float)):
            formatted_data["saturation_fmt"] = formatar_br(formatted_data["saturation"], 2)
        if "lanes_p" in formatted_data:
            formatted_data["lanes_p_fmt"] = str(formatted_data["lanes_p"])
        if "lanes_s" in formatted_data:
            formatted_data["lanes_s_fmt"] = str(formatted_data["lanes_s"])
        if "speed_p" in formatted_data and isinstance(formatted_data["speed_p"], (int, float)):
            formatted_data["speed_p_fmt"] = formatar_br(formatted_data["speed_p"], 0)
        if "speed_s" in formatted_data and isinstance(formatted_data["speed_s"], (int, float)):
            formatted_data["speed_s_fmt"] = formatar_br(formatted_data["speed_s"], 0)

        return {
            "mode": "INTERSECTION_DETAIL",
            "language": "pt_br",
            "intersection_id": clean_j_id,
            "attributions": formatted_data
        }

    @staticmethod
    def build_conclusion_input(analysis_results: Dict[str, Any], light_results: Dict[str, Any]) -> Dict[str, Any]:
        """Constructs input dictionary for final conclusions and comparative overview."""
        return {
            "mode": "COMPARATIVE_REPORT",
            "language": "pt_br",
            "attributions": {
                "intersections_count": len(analysis_results)
            }
        }

    @staticmethod
    def build_final_opinion_input(
        analysis_results: Dict[str, Any], 
        light_results: Dict[str, Any], 
        add_count: int, 
        optimize_count: int, 
        keep_count: int, 
        no_signal_count: int, 
        signalized_count: int = 0, 
        unsignalized_count: int = 0,
        stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Constructs input dictionary for SLM qualitative synthesis with explicit subgroup variable names and real calculated statistics."""
        total_j = len(analysis_results)
        st = stats or {}
        
        max_sat = st.get("max_saturation_val", 0.0)
        max_sat_id = st.get("max_saturation_junction_id", "N/A")
        max_delay = st.get("max_delay_val", 0.0)
        max_delay_id = st.get("max_delay_junction_id", "N/A")

        optimize_ids = ", ".join(st.get("optimize_junction_ids", [])) or "Nenhum"
        add_ids = ", ".join(st.get("add_junction_ids", [])) or "Nenhum"
        keep_ids = ", ".join(st.get("keep_junction_ids", [])) or "Nenhum"
        no_signal_ids = ", ".join(st.get("no_signal_junction_ids", [])) or "Nenhum"

        return {
            "mode": "STATISTICAL_REPORT",
            "language": "pt_br",
            "attributions": {
                "engine_name": "CARINA v1.0 (SAS Engine)",
                "intersections_count": total_j,
                "qtd_total_cruzamentos": total_j,
                "qtd_total_sinalizados": signalized_count,
                "qtd_total_nao_sinalizados": unsignalized_count,
                "signalized_count": signalized_count,
                "unsignalized_count": unsignalized_count,
                "add_count": add_count,
                "optimize_count": optimize_count,
                "keep_count": keep_count,
                "no_signal_count": no_signal_count,
                "qtd_sinalizados_criticos": optimize_count,
                "qtd_sinalizados_estaveis": keep_count,
                "qtd_nao_sinalizados_criticos": add_count,
                "qtd_nao_sinalizados_estaveis": no_signal_count,
                "qtd_estaveis": keep_count + no_signal_count,
                "max_saturation_val": formatar_br(max_sat, 2),
                "max_saturation_junction_id": max_sat_id,
                "max_delay_val": formatar_br(max_delay, 1),
                "max_delay_junction_id": max_delay_id,
                "optimize_junction_ids": optimize_ids,
                "add_junction_ids": add_ids,
                "keep_junction_ids": keep_ids,
                "no_signal_junction_ids": no_signal_ids
            }
        }
