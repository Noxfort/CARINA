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

import os
import json
import logging
from typing import Dict, Any, List, Tuple
from mfd.mfd_template_provider import MFDTemplateProvider
from mfd.mfd_prompt_builder import MFDPromptBuilder
from mfd.mfd_subprocess_fallback import MFDSubprocessFallback
from blocks.report_post_processor import ReportPostProcessor

class MFDSectionBuilder:
    """
    Responsibility (SRP & OCP): Construct structured Markdown document sections (1 to 5 and Anexo I)
    for MFD performance and optimization reports. Loads section headers and narrative fallbacks from JSON.
    """

    _fallbacks_cache: Dict[str, Any] = None

    @classmethod
    def _load_fallbacks_config(cls) -> Dict[str, Any]:
        """Loads narrative fallbacks from config/mfd_section_fallbacks.json with caching and fallback."""
        if cls._fallbacks_cache is not None:
            return cls._fallbacks_cache

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "config", "mfd_section_fallbacks.json")

        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    cls._fallbacks_cache = json.load(f)
                    logging.info(f"[MFDSectionBuilder] Loaded fallbacks from {json_path}")
                    return cls._fallbacks_cache
            except Exception as e:
                logging.warning(f"[MFDSectionBuilder] Failed to load JSON '{json_path}': {e}. Using fallback.")

        cls._fallbacks_cache = {}
        return cls._fallbacks_cache

    @classmethod
    def _get_section_title(cls, title_key: str, lang: str = "pt_br") -> str:
        """Resolves section title markdown header from JSON configuration across languages."""
        cfg = cls._load_fallbacks_config()
        titles = cfg.get("section_titles", {})
        lang_key = (lang or "pt_br").lower()

        title_obj = titles.get(title_key, {})
        if isinstance(title_obj, dict):
            return title_obj.get(lang_key, title_obj.get("pt_br", title_obj.get("en", "")))
        return str(title_obj)

    @classmethod
    def _get_fallback_text(cls, section_key: str, outcome_key: str, lang: str = "pt_br") -> str:
        """Resolves section narrative fallback string from JSON configuration across languages."""
        cfg = cls._load_fallbacks_config()
        sec_cfg = cfg.get(section_key, {})
        lang_key = (lang or "pt_br").lower()

        outcome_obj = sec_cfg.get(outcome_key, {})
        if isinstance(outcome_obj, dict):
            return outcome_obj.get(lang_key, outcome_obj.get("pt_br", outcome_obj.get("en", "")))
        return str(outcome_obj)

    @classmethod
    def build_executive_intro(cls, normalized_data: Dict[str, Any], transducer: Any = None, lang: str = "pt_br") -> Tuple[str, str]:
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

        if not raw_exec_summary or len(raw_exec_summary.strip()) < 20:
            try:
                raw_exec_summary = MFDSubprocessFallback.try_subprocess_transducer(summary_payload)
            except Exception as sub_err:
                logging.debug(f"[MFD_SECTION_BUILDER] Subprocess fallback failed: {sub_err}")

        lang_key = (lang or "pt_br").lower()
        if not raw_exec_summary or len(raw_exec_summary.strip()) < 20 or "Não foi possível" in raw_exec_summary or "DATA_PAYLOAD" in raw_exec_summary:
            mature_spd = f"{spd.get('mature', 42.5):.1f}" if isinstance(spd.get('mature'), float) else str(spd.get('mature', 42.5))
            spd_gain_str = f"+{speed_gain:.1f}" if speed_gain > 0 else f"{speed_gain:.1f}"

            outcome_key = "positive" if speed_gain > 0 else "negative"
            fallback_tmpl = cls._get_fallback_text("executive_summary", outcome_key, lang=lang)

            try:
                raw_exec_summary = fallback_tmpl.format(mature_speed=mature_spd, speed_gain=spd_gain_str)
            except Exception:
                raw_exec_summary = fallback_tmpl

        clean_intro = ReportPostProcessor.clean_ai_preamble(raw_exec_summary)
        intro_title = cls._get_section_title("section_1_intro", lang=lang)
        intro_section = f"{intro_title}\n{clean_intro}"
        return intro_section, raw_exec_summary

    @classmethod
    def build_narrative_sections(cls, normalized_data: Dict[str, Any], transducer: Any = None, lang: str = "pt_br") -> Tuple[str, str]:
        """
        Assemble the full narrative text (Sections 1 through 5).

        :param normalized_data: Normalized MFD data dictionary
        :param transducer: Optional SLM transducer instance
        :param lang: UI target language
        :return: Tuple of (narrative_markdown_text, raw_executive_summary)
        """
        intersections_list = normalized_data.get("intersections_list", [])

        intro_section, raw_exec_summary = cls.build_executive_intro(normalized_data, transducer=transducer, lang=lang)
        equations_section = MFDTemplateProvider.get_section_4_equations(lang=lang)
        synthesis_table_section = MFDTemplateProvider.get_section_5_synthesis_table(intersections_list, lang=lang)
        consolidated_section = MFDTemplateProvider.get_section_6_consolidated_summary(normalized_data, lang=lang)

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

        if not raw_final_opinion or len(raw_final_opinion.strip()) < 20:
            try:
                raw_final_opinion = MFDSubprocessFallback.try_subprocess_transducer(opinion_payload)
            except Exception as sub_err:
                logging.debug(f"[MFD_SECTION_BUILDER] Subprocess fallback failed: {sub_err}")

        impacts = normalized_data.get("impact_stats", {})
        comp = impacts.get("comparative_table", {})
        speed_gain = comp.get("speed_kmh", {}).get("delta_pct", 0.0)

        if not raw_final_opinion or len(raw_final_opinion.strip()) < 20:
            outcome_key = "positive" if speed_gain > 0 else "negative"
            raw_final_opinion = cls._get_fallback_text("final_opinion", outcome_key, lang=lang)

        clean_final_opinion = ReportPostProcessor.clean_ai_preamble(raw_final_opinion)
        final_opinion_title = cls._get_section_title("section_5_final_opinion", lang=lang)

        narrative_lines = [
            intro_section,
            equations_section,
            synthesis_table_section,
            consolidated_section,
            final_opinion_title,
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
            justification = None
            single_payload = MFDPromptBuilder.build_single_intersection_input(row, lang=lang)
            if transducer is not None and hasattr(transducer, "generate_report"):
                try:
                    justification = transducer.generate_report(single_payload)
                except Exception as ex_single:
                    logging.warning(f"[MFD_SECTION_BUILDER] Failed SLM justification for intersection {row.get('id')}: {ex_single}")

            if not justification or len(justification.strip()) < 20:
                try:
                    justification = MFDSubprocessFallback.try_subprocess_transducer(single_payload)
                except Exception:
                    justification = None

            ficha_md = MFDTemplateProvider.get_intersection_audit_sheet_template(row, justification=justification, lang=lang)
            fichas_anexo_i.append(ficha_md)

        anexo_text = "\n\n".join(fichas_anexo_i)
        anexo_text = ReportPostProcessor.enforce_semantic_consistency(anexo_text)
        anexo_text = ReportPostProcessor.sanitize_truncated_text(anexo_text)
        return anexo_text
