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

# File: src/sas/report_table_builder.py
# Author: Gabriel Moraes
# Date: August 10, 2026

from typing import Dict, Any, List, Tuple

from sas.report_intersection_processor import ReportIntersectionProcessor
from sas.report_prompt_builder import ReportPromptBuilder
from sas.report_template_provider import ReportTemplateProvider
from blocks.report_post_processor import ReportPostProcessor


class ReportTableBuilder:
    """
    Constructs audit synthesis tables and individual intersection fichas for technical reports.
    """

    @staticmethod
    def build_audit_table_and_fichas(
        analysis_results: Dict[str, Any],
        stats: Dict[str, Any],
        transducer: Any,
        ui_language: str = "pt_br"
    ) -> Tuple[List[str], List[str]]:
        """
        Iterates over normalized junction analysis data, generates tabular rows for
        Section 5 (Audit Table 1), and compiles detailed intersection fichas for Annex I.

        Args:
            analysis_results (Dict[str, Any]): Normalized junction analysis dictionary.
            stats (Dict[str, Any]): Network statistical metrics.
            transducer (Any): Neural transducer instance for neural reasoning generation.
            ui_language (str): UI language code (e.g., 'pt_br').

        Returns:
            Tuple[List[str], List[str]]:
                - table_rows: Markdown table headers and data rows.
                - cruzamentos_detalhe: List of formatted intersection ficha strings.
        """
        cruzamentos_detalhe = []
        table_rows = [
            "### Tabela 1 – Síntese de Auditoria da Malha Viária\n",
            "| ID | Status Atual | Vol. Principal (vph) | Vol. Secundário (vph) | Atraso Médio (s) | Fila Max (P95) | Saturação (X) | Recomendação |",
            "|---|---|---|---|---|---|---|---|"
        ]

        for j_id, j_data in analysis_results.items():
            processed = ReportIntersectionProcessor.process_single_intersection(
                j_id=j_id,
                j_data=j_data,
                stats=stats,
                ui_language=ui_language
            )

            clean_j_id = processed["clean_j_id"]
            status_formatted = processed["current_status"]
            vol_p = processed["vol_primary_val"]
            vol_s = processed["vol_secondary_val"]
            delay = processed["avg_delay"]
            queue = processed["queue_p95"]
            sat = processed["saturation_ratio"]
            rec_formatted = processed["recommendation"]
            is_critical = processed["is_critical"]
            coherent_status_raw = processed["coherent_status_raw"]

            # Append row to Audit Table 1
            table_rows.append(
                f"| {clean_j_id} | {status_formatted} | {vol_p:.1f} | {vol_s:.1f} | "
                f"{delay:.1f} | {queue} | {sat:.2f} | {rec_formatted} |"
            )

            # Generate neural reasoning/justification for single intersection
            single_input = ReportPromptBuilder.build_single_intersection_input(clean_j_id, processed)
            justificativa_raw = transducer.generate_report(single_input)
            justificativa = ReportPostProcessor.clean_ai_preamble(justificativa_raw)
            justificativa = ReportPostProcessor.enforce_semantic_consistency(
                justificativa,
                is_signalized=(coherent_status_raw == "Sinalizado")
            )

            # Render Annex I detailed intersection ficha
            ficha_str = ReportTemplateProvider.get_intersection_ficha_template(
                clean_j_id=clean_j_id,
                status_formatted=status_formatted,
                rec_formatted=rec_formatted,
                vol_p=vol_p,
                vol_s=vol_s,
                delay=delay,
                queue=queue,
                sat=sat,
                is_critical=is_critical,
                justificativa=justificativa,
                language=ui_language,
                lanes_p=processed["lanes_p"],
                lanes_s=processed["lanes_s"],
                speed_p=processed["speed_p"],
                speed_s=processed["speed_s"],
                len_p=processed["len_p"],
                len_s=processed["len_s"]
            )
            cruzamentos_detalhe.append(ficha_str)

        return table_rows, cruzamentos_detalhe
