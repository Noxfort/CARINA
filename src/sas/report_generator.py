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

# File: src/sas/report_generator.py
# Author: Gabriel Moraes
# Date: July 27, 2026

import logging
from typing import Any, Tuple

from sas.report_transducer_factory import ReportTransducerFactory
from sas.report_template_provider import ReportTemplateProvider
from sas.report_prompt_builder import ReportPromptBuilder
from sas.report_section_builder import ReportSectionBuilder
from sas.report_data_normalizer import ReportDataNormalizer
from sas.report_table_builder import ReportTableBuilder
from blocks.report_post_processor import ReportPostProcessor


class ReportGenerator:
    """
    Main orchestrator for generating structured ABNT Technical Reports.
    Coordinates data normalization, neural inference, section building,
    and post-processing via dedicated modular components.
    """

    def __init__(self, locale_manager: Any = None):
        self.locale_manager = locale_manager

    def generate_docx_report(
        self,
        analysis_results: Any,
        scenario_dir: str = None,
        net_file_path: str = None,
        has_significant_change: bool = False,
        has_last_report: bool = False,
        ui_language: str = "pt_br",
        time_window_str: str = ""
    ) -> Tuple[None, str]:
        """Instance wrapper method for backward compatibility with AnalyzerEngine."""
        junctions_norm = ReportDataNormalizer.normalize_junctions(analysis_results)
        return self.generate_report(
            junctions_data=junctions_norm,
            scenario_dir=scenario_dir,
            has_significant_change=has_significant_change,
            has_last_report=has_last_report,
            ui_language=ui_language,
            time_window_str=time_window_str
        )

    @classmethod
    def generate_report(
        cls,
        junctions_data: Any,
        agency_name: str = "Prefeitura Municipal",
        department_name: str = "Secretaria Municipal de Mobilidade e Trânsito",
        scenario_dir: str = None,
        ui_language: str = "pt_br",
        has_significant_change: bool = False,
        has_last_report: bool = False,
        time_window_str: str = ""
    ) -> Tuple[None, str]:
        """
        High-Level Orchestrator method for generating a comprehensive ABNT Technical Report.

        Returns:
            Tuple[None, str]: (None, report_markdown_text)
        """
        transducer = None
        try:
            # 1. Data Normalization & Statistical Calculation
            analysis_results = ReportDataNormalizer.normalize_junctions(junctions_data)
            stats = ReportDataNormalizer.calculate_statistics(analysis_results)

            # 2. Neural Transducer Acquisition
            transducer = ReportTransducerFactory.create_transducer()

            # 3. Extract Light Evaluation Results
            light_results = {}
            for j_id, j_data in analysis_results.items():
                light_results[j_id] = transducer.generate_report({"mode": "LIGHT_EVALUATION", "data": j_data})

            # 4. Generate Section 3 (Executive Summary & Introduction)
            exec_summary_input = ReportPromptBuilder.build_executive_summary_input(
                analysis_results,
                light_results,
                intervention_rate=stats["intervention_rate"],
                add_count=stats["add_count"],
                optimize_count=stats["optimize_count"],
                keep_count=stats["keep_count"],
                signalized_count=stats["signalized_count"],
                unsignalized_count=stats["unsignalized_count"],
                time_window_str=time_window_str
            )
            raw_exec_summary = transducer.generate_report(exec_summary_input)
            resumo_executivo = ReportPostProcessor.format_executive_summary(raw_exec_summary, stats["intervention_rate"])
            if hasattr(transducer, "review_text"):
                try:
                    resumo_executivo = transducer.review_text(resumo_executivo, language=ui_language)
                except Exception as e:
                    logging.warning(f"[REPORT_GEN] 2nd Pass Neural Revision failed for executive summary: {e}")

            secao_introducao = ReportSectionBuilder.build_introduction_section(
                resumo_executivo, sec_num=3, time_window_str=time_window_str
            )

            # 5. Generate Section 4 (Equations & Methodology)
            equacoes_section = ReportSectionBuilder.build_equations_section(ui_language)

            # 6. Process Section 5 (Audit Table 1) & Annex I (Individual Fichas)
            table_rows, cruzamentos_detalhe = ReportTableBuilder.build_audit_table_and_fichas(
                analysis_results=analysis_results,
                stats=stats,
                transducer=transducer,
                ui_language=ui_language
            )

            # 7. Generate Section 6 & 7 (Consolidated Summary and Conclusions)
            resumo_consolidado = ReportTemplateProvider.get_consolidated_summary_text(
                total_intersections=stats["total_junctions"],
                keep_count=stats["keep_count"],
                remove_count=stats["remove_count"],
                add_count=stats["add_count"],
                no_signal_count=stats["no_signal_count"],
                optimize_count=stats["optimize_count"],
                language=ui_language
            )

            include_comparison = has_last_report and has_significant_change

            if include_comparison:
                conclusion_input = ReportPromptBuilder.build_conclusion_input(analysis_results, light_results)
                conclusion_text_raw = transducer.generate_report(conclusion_input)
                conclusion_text = ReportPostProcessor.clean_ai_preamble(conclusion_text_raw)
                conclusion_text = ReportPostProcessor.enforce_semantic_consistency(conclusion_text, is_signalized=True)
            else:
                conclusion_text = ""

            secao_conclusao = ReportTemplateProvider.get_conclusions_section(
                add_count=stats["add_count"],
                remove_count=stats["remove_count"],
                keep_count=stats["keep_count"],
                no_signal_count=stats["no_signal_count"],
                conclusion_text=conclusion_text,
                has_last_report=include_comparison,
                language=ui_language
            )

            # 8. Generate Section 8 (Final Technical Opinion)
            final_opinion_input = ReportPromptBuilder.build_final_opinion_input(
                analysis_results,
                light_results,
                stats["add_count"],
                stats["optimize_count"],
                stats["keep_count"],
                stats["no_signal_count"],
                signalized_count=stats["signalized_count"],
                unsignalized_count=stats["unsignalized_count"],
                stats=stats
            )
            slm_synthesis_raw = transducer.generate_report(final_opinion_input)
            slm_synthesis = ReportPostProcessor.clean_ai_preamble(slm_synthesis_raw)
            slm_synthesis = ReportPostProcessor.sanitize_zero_maintenance_protocol(slm_synthesis, stats["keep_count"])
            slm_synthesis = ReportPostProcessor.enforce_semantic_consistency(slm_synthesis, is_signalized=True)
            if hasattr(transducer, "review_text"):
                try:
                    slm_synthesis = transducer.review_text(slm_synthesis, language=ui_language)
                except Exception as e:
                    logging.warning(f"[REPORT_GEN] 2nd Pass Neural Revision failed for SLM synthesis: {e}")

            # 9. Assemble Sections with Dynamic Sequential Numbering
            curr_sec = 3
            secao_introducao = ReportSectionBuilder.build_introduction_section(resumo_executivo, sec_num=curr_sec)
            curr_sec += 1

            equacoes_section_num = equacoes_section.replace("## 4.", f"## {curr_sec}.")
            curr_sec += 1

            secao_tabela = ReportSectionBuilder.build_synthetic_table_section(table_rows, sec_num=curr_sec)
            curr_sec += 1

            secao_resumo_conclusao = ReportSectionBuilder.build_summary_conclusions_section(
                resumo_consolidado, secao_conclusao, sec_num=curr_sec
            )
            curr_sec += 1

            has_comparative = include_comparison and conclusion_text and len(conclusion_text) > 10
            if has_comparative:
                secao_comparativo = ReportSectionBuilder.build_comparative_section(conclusion_text, sec_num=curr_sec)
                curr_sec += 1
            else:
                secao_comparativo = ""

            add_ids_str = ", ".join(stats.get("add_junction_ids", []))
            opt_ids_str = ", ".join(stats.get("optimize_junction_ids", []))

            secao_parecer = ReportSectionBuilder.build_final_opinion_section(
                stats["total_junctions"],
                stats["signalized_count"],
                stats["unsignalized_count"],
                stats["add_count"],
                stats["optimize_count"],
                stats["keep_count"],
                stats["no_signal_count"],
                slm_synthesis=slm_synthesis,
                agency_name=agency_name,
                department_name=department_name,
                sec_num=curr_sec,
                add_junction_ids=add_ids_str,
                optimize_junction_ids=opt_ids_str
            )
            secao_anexo = ReportSectionBuilder.build_annex_section(cruzamentos_detalhe)

            report_text = (
                f"{secao_introducao}"
                f"{equacoes_section_num}\n\n"
                f"{secao_tabela}"
                f"{secao_resumo_conclusao}"
                f"{secao_comparativo}"
                f"{secao_parecer}"
                f"{secao_anexo}"
            )

            # 10. Document-level post-processing
            report_text = ReportPostProcessor.enforce_semantic_consistency(report_text, is_signalized=True)

            logging.info("[REPORT_GEN] Technical report text successfully compiled.")
            return None, report_text

        except Exception as e:
            logging.error(f"[REPORT_GEN] Error generating report: {e}", exc_info=True)
            return None, None
        finally:
            ReportTransducerFactory.release_transducer(transducer)
