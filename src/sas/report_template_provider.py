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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/sas/report_template_provider.py
# Author: Gabriel Moraes
# Date: July 21, 2026

from typing import Dict, Any
from sas.template_repository import TemplateRepository
from sas.recommendation_label_resolver import RecommendationLabelResolver
from sas.intersection_block_formatter import IntersectionBlockFormatter
from sas.summary_directive_builder import SummaryDirectiveBuilder

class ReportTemplateProvider:
    """
    Responsibility (Facade Pattern / SOLID): Global facade providing static report templates, 
    bilingual formatting, and Markdown blocks by delegating to specialized sub-components 
    (TemplateRepository, RecommendationLabelResolver, IntersectionBlockFormatter, SummaryDirectiveBuilder).
    Follows SOLID design principles.
    """

    @classmethod
    def _load_templates(cls) -> dict:
        """Delegates to TemplateRepository."""
        return TemplateRepository.load_templates()

    @classmethod
    def get_template_value(cls, key: str, language: str, default: str = "") -> str:
        """Delegates to TemplateRepository."""
        return TemplateRepository.get_template_value(key, language, default=default)

    @classmethod
    def get_introducao_title(cls, language: str) -> str:
        """Delegates to TemplateRepository."""
        return cls.get_template_value("introducao_title", language, default="## 1. Introdução e Contexto Executivo")

    @classmethod
    def get_auditoria_title(cls, language: str) -> str:
        """Delegates to TemplateRepository."""
        return cls.get_template_value("auditoria_title", language, default="## 3. Detalhamento de Auditoria e Decisões por Cruzamento\n\n")

    @classmethod
    def get_equations_section(cls, language: str) -> str:
        """Delegates to TemplateRepository."""
        return cls.get_template_value("equations_section", language)

    @classmethod
    def get_recommendation_labels(
        cls,
        is_add: bool,
        is_remove: bool,
        is_keep: bool,
        is_no_signal: bool,
        language: str,
        is_optimize: bool = False
    ) -> str:
        """Delegates to RecommendationLabelResolver."""
        return RecommendationLabelResolver.get_recommendation_labels(
            is_add=is_add,
            is_remove=is_remove,
            is_keep=is_keep,
            is_no_signal=is_no_signal,
            language=language,
            is_optimize=is_optimize
        )

    @classmethod
    def get_status_label(cls, status_raw: str, language: str) -> str:
        """Delegates to RecommendationLabelResolver."""
        return RecommendationLabelResolver.get_status_label(status_raw, language)

    @classmethod
    def get_intersection_block(
        cls,
        j_id: str,
        status_formatted: str,
        vol_p: float,
        vol_s: float,
        delay: float,
        queue: int,
        sat: float,
        rec_formatted: str,
        justificativa_rica: str,
        language: str,
        lanes_p: int = 1,
        lanes_s: int = 1,
        speed_p: float = 50.0,
        speed_s: float = 40.0,
        len_p: float = 100.0,
        len_s: float = 100.0
    ) -> str:
        """Delegates to IntersectionBlockFormatter."""
        return IntersectionBlockFormatter.get_intersection_block(
            j_id=j_id,
            status_formatted=status_formatted,
            vol_p=vol_p,
            vol_s=vol_s,
            delay=delay,
            queue=queue,
            sat=sat,
            rec_formatted=rec_formatted,
            justificativa_rica=justificativa_rica,
            language=language,
            lanes_p=lanes_p,
            lanes_s=lanes_s,
            speed_p=speed_p,
            speed_s=speed_s,
            len_p=len_p,
            len_s=len_s
        )

    @classmethod
    def get_intersection_ficha_template(
        cls,
        clean_j_id: str,
        status_formatted: str,
        rec_formatted: str,
        vol_p: float,
        vol_s: float,
        delay: float,
        queue: int,
        sat: float,
        is_critical: bool,
        justificativa: str,
        language: str,
        lanes_p: int = 1,
        lanes_s: int = 1,
        speed_p: float = 50.0,
        speed_s: float = 40.0,
        len_p: float = 100.0,
        len_s: float = 100.0
    ) -> str:
        """Alias wrapper method delegating to get_intersection_block."""
        return cls.get_intersection_block(
            j_id=clean_j_id,
            status_formatted=status_formatted,
            vol_p=vol_p,
            vol_s=vol_s,
            delay=delay,
            queue=queue,
            sat=sat,
            rec_formatted=rec_formatted,
            justificativa_rica=justificativa,
            language=language,
            lanes_p=lanes_p,
            lanes_s=lanes_s,
            speed_p=speed_p,
            speed_s=speed_s,
            len_p=len_p,
            len_s=len_s
        )

    @classmethod
    def get_consolidated_summary(
        cls,
        total_junctions: int,
        keep_count: int,
        remove_count: int,
        add_count: int,
        no_signal_count: int,
        language: str,
        optimize_count: int = 0
    ) -> str:
        """Delegates to SummaryDirectiveBuilder."""
        return SummaryDirectiveBuilder.get_consolidated_summary(
            total_junctions=total_junctions,
            keep_count=keep_count,
            remove_count=remove_count,
            add_count=add_count,
            no_signal_count=no_signal_count,
            language=language,
            optimize_count=optimize_count
        )

    @classmethod
    def get_consolidated_summary_text(
        cls,
        total_intersections: int,
        keep_count: int,
        remove_count: int,
        add_count: int,
        no_signal_count: int,
        language: str = "pt_br",
        optimize_count: int = 0
    ) -> str:
        """Alias wrapper method delegating to get_consolidated_summary."""
        return cls.get_consolidated_summary(
            total_junctions=total_intersections,
            keep_count=keep_count,
            remove_count=remove_count,
            add_count=add_count,
            no_signal_count=no_signal_count,
            optimize_count=optimize_count,
            language=language
        )

    @classmethod
    def get_conclusions_section(
        cls,
        add_count: int,
        remove_count: int,
        keep_count: int,
        no_signal_count: int,
        conclusion_text: str,
        has_last_report: bool,
        language: str,
        optimize_count: int = 0
    ) -> str:
        """Delegates to SummaryDirectiveBuilder."""
        return SummaryDirectiveBuilder.get_conclusions_section(
            add_count=add_count,
            remove_count=remove_count,
            keep_count=keep_count,
            no_signal_count=no_signal_count,
            conclusion_text=conclusion_text,
            has_last_report=has_last_report,
            language=language,
            optimize_count=optimize_count
        )

    @classmethod
    def get_layout_translations(cls, language: str) -> dict:
        """Delegates to TemplateRepository."""
        return TemplateRepository.get_layout_translations(language)

    @classmethod
    def get_cluster_prefix(cls, language: str = "pt_br") -> str:
        """Delegates to TemplateRepository."""
        return TemplateRepository.get_cluster_prefix(language)
