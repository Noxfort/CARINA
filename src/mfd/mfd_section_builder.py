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

# File: src/mfd/mfd_section_builder.py
# Author: Gabriel Moraes
# Date: August 9, 2026

import logging
from typing import Dict, Any, List, Tuple
from mfd.mfd_template_provider import MFDTemplateProvider
from mfd.mfd_prompt_builder import MFDPromptBuilder
from blocks.report_post_processor import ReportPostProcessor

class MFDSectionBuilder:
    """
    Responsibility (SRP): Construct structured Markdown document sections (1 to 5 and Anexo I)
    for MFD performance and optimization reports.
    """

    @staticmethod
    def build_executive_intro(normalized_data: Dict[str, Any], transducer: Any = None, lang: str = "pt_br") -> Tuple[str, str]:
        """
        Build Section 1: Executive Introduction & Context.

        :param normalized_data: Normalized MFD data dictionary
        :param transducer: Optional SLM transducer instance for neural generation
        :param lang: UI target language
        :return: Tuple of (intro_section_markdown, raw_executive_summary)
        """
        stats = normalized_data.get("stats", {})
        impacts = normalized_data.get("impact_stats", {})
        comp = impacts.get("comparative_table", {})
        spd = comp.get("speed_kmh", {})
        speed_gain = spd.get("delta_pct", 0.0)

        summary_payload = MFDPromptBuilder.build_executive_summary_input(normalized_data, lang=lang)
        raw_exec_summary = ""

        if transducer is not None and hasattr(transducer, "generate_report"):
            try:
                logging.info("[MFD_SECTION_BUILDER] Generating Section 1 Executive Summary via SLM Transducer...")
                raw_exec_summary = transducer.generate_report(summary_payload)
            except Exception as slm_err:
                logging.warning(f"[MFD_SECTION_BUILDER] SLM generation for Executive Summary failed: {slm_err}")
                raw_exec_summary = ""

        if not raw_exec_summary or len(raw_exec_summary.strip()) < 20 or "Não foi possível" in raw_exec_summary or "DATA_PAYLOAD" in raw_exec_summary:
            if speed_gain > 0:
                raw_exec_summary = (
                    f"A mobilidade urbana da malha viária analisada apresenta evolução operacional positiva sob o controle ativo do motor CARINA v1.0. "
                    f"A velocidade média alcançou {spd.get('mature', 42.5)} km/h (Fase Adulta), registrando ganho de fluidez de +{speed_gain:.1f}% em relação à Linha Base (Fase Criança). "
                    f"Os cruzamentos semafóricos auditados demonstraram estabilização na entropia da política e alívio contínuo do acúmulo de filas no tráfego urbano."
                )
            else:
                raw_exec_summary = (
                    f"A mobilidade urbana da malha viária analisada registrou ponto de atrito e retenção de fluxo sob o controle ativo do motor CARINA v1.0. "
                    f"A velocidade média da malha evoluiu para {spd.get('mature', 42.5)} km/h, apresentando variação de {speed_gain:.1f}% e elevação no volume de acúmulo de filas. "
                    f"Os dados empíricos observados indicam a necessidade de readequação e sintonia fina nos tempos de ciclo semafórico."
                )

        clean_intro = ReportPostProcessor.clean_ai_preamble(raw_exec_summary)
        intro_section = f"## 1. INTRODUÇÃO E CONTEXTO EXECUTIVO\n{clean_intro}"
        return intro_section, raw_exec_summary

    @staticmethod
    def build_narrative_sections(normalized_data: Dict[str, Any], transducer: Any = None, lang: str = "pt_br") -> Tuple[str, str]:
        """
        Assemble the full narrative text (Sections 1 through 5).

        :param normalized_data: Normalized MFD data dictionary
        :param transducer: Optional SLM transducer instance
        :param lang: UI target language
        :return: Tuple of (narrative_markdown_text, raw_executive_summary)
        """
        intersections_list = normalized_data.get("intersections_list", [])

        intro_section, raw_exec_summary = MFDSectionBuilder.build_executive_intro(normalized_data, transducer=transducer, lang=lang)
        equations_section = MFDTemplateProvider.get_section_4_equations()
        synthesis_table_section = MFDTemplateProvider.get_section_5_synthesis_table(intersections_list)
        consolidated_section = MFDTemplateProvider.get_section_6_consolidated_summary(normalized_data)

        # Build Section 5: Technical Final Opinion
        opinion_payload = MFDPromptBuilder.build_final_opinion_input(normalized_data, lang=lang)
        raw_final_opinion = ""

        if transducer is not None and hasattr(transducer, "generate_report"):
            try:
                logging.info("[MFD_SECTION_BUILDER] Generating Section 5 Technical Final Opinion via SLM Transducer...")
                raw_final_opinion = transducer.generate_report(opinion_payload)
            except Exception as slm_err:
                logging.warning(f"[MFD_SECTION_BUILDER] SLM generation for Technical Final Opinion failed: {slm_err}")
                raw_final_opinion = ""

        impacts = normalized_data.get("impact_stats", {})
        comp = impacts.get("comparative_table", {})
        speed_gain = comp.get("speed_kmh", {}).get("delta_pct", 0.0)

        if not raw_final_opinion or len(raw_final_opinion.strip()) < 20:
            if speed_gain > 0:
                raw_final_opinion = (
                    "O Motor CARINA v1.0 (MFD Engine / Método DA SILVA) atesta que a malha viária urbana analisada registrou ganho efetivo na velocidade de fluxo "
                    "e redução significativa no tempo de espera dos veículos. Com base nos dados empíricos observados, emitimos o Parecer Técnico de "
                    "APROVAÇÃO E HOMOLOGAÇÃO DA OTIMIZAÇÃO SEMAFÓRICA da malha auditada."
                )
            else:
                raw_final_opinion = (
                    "O Motor CARINA v1.0 (MFD Engine / Método DA SILVA) atesta que a malha viária urbana analisada registrou retenção no fluxo de veículos "
                    "e aumento no acúmulo de filas no cenário sob auditoria. Com base nos dados empíricos observados, emitimos o Parecer Técnico de "
                    "REAPRECIAÇÃO E REAJUSTE DOS PARÂMETROS SEMAFÓRICOS, recomendando a readequação dos tempos de ciclo e a recalibração dos modelos neurais de Aprendizado por Reforço antes da homologação definitiva."
                )

        clean_final_opinion = ReportPostProcessor.clean_ai_preamble(raw_final_opinion)

        narrative_lines = [
            intro_section,
            equations_section,
            synthesis_table_section,
            consolidated_section,
            "## 5. Considerações Finais e Parecer Técnico",
            clean_final_opinion
        ]

        narrative_text = "\n\n".join(narrative_lines)
        narrative_text = ReportPostProcessor.enforce_semantic_consistency(narrative_text)
        narrative_text = ReportPostProcessor.sanitize_truncated_text(narrative_text)
        return narrative_text, raw_exec_summary

    @staticmethod
    def build_anexo_fichas(normalized_data: Dict[str, Any], transducer: Any = None, lang: str = "pt_br") -> str:
        """
        Assemble Section ANEXO I Fichas for all signalized intersections.

        :param normalized_data: Normalized MFD data dictionary
        :param transducer: Optional SLM transducer instance
        :param lang: UI target language
        :return: ANEXO I Markdown text string
        """
        intersections_list = normalized_data.get("intersections_list", [])
        fichas_anexo_i = []

        for row in intersections_list:
            justificativa = None
            if transducer is not None and hasattr(transducer, "generate_report"):
                try:
                    single_payload = MFDPromptBuilder.build_single_intersection_input(row, lang=lang)
                    justificativa = transducer.generate_report(single_payload)
                except Exception as ex_single:
                    logging.warning(f"[MFD_SECTION_BUILDER] Failed SLM justification for intersection {row.get('id')}: {ex_single}")

            ficha_md = MFDTemplateProvider.get_intersection_ficha_template(row, justificativa=justificativa)
            fichas_anexo_i.append(ficha_md)

        anexo_text = "\n\n".join(fichas_anexo_i)
        anexo_text = ReportPostProcessor.enforce_semantic_consistency(anexo_text)
        anexo_text = ReportPostProcessor.sanitize_truncated_text(anexo_text)
        return anexo_text
