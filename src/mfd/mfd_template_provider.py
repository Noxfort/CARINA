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

# File: src/mfd/mfd_template_provider.py
# Author: Gabriel Moraes
# Date: August 12, 2026

from typing import Dict, Any, List
from mfd.mfd_template_repository import MFDTemplateRepository
from mfd.mfd_table_formatter import MFDTableFormatter
from mfd.mfd_justification_resolver import MFDJustificationResolver
from mfd.mfd_audit_sheet_formatter import MFDAuditSheetFormatter

class MFDTemplateProvider:
    """
    Responsibility (Facade Pattern & OCP): Serves as a unified facade for accessing MFD report templates,
    delegating responsibilities to specialized classes and reading document section arrays dynamically from JSON.
    - MFDTemplateRepository: JSON loading and caching
    - MFDTableFormatter: Tables (Section 3) and Consolidated Summaries (Section 4)
    - MFDJustificationResolver: Deterministic technical justifications
    - MFDAuditSheetFormatter: Anexo I Audit Sheets
    Provides 100% backwards compatibility.
    """

    @classmethod
    def get_section_4_equations(cls, lang: str = "pt_br") -> str:
        """
        Returns Section 2: MFD Mathematical Equations & Método DA SILVA Maturation Curriculum with 3 Criteria
        dynamically rendered from JSON lines array.

        :param lang: UI target language code
        :return: Formatted Section 2 Markdown string
        """
        raw_cfg = MFDTemplateRepository.load_templates().get("section_2_equations", {})
        lang_key = (lang or "pt_br").lower()
        cfg = raw_cfg.get(lang_key, raw_cfg.get("pt_br", raw_cfg.get("en", {})))

        lines = cfg.get("lines", [])
        return "\n".join(lines)

    @classmethod
    def get_section_5_synthesis_table(cls, intersections_list: List[Dict[str, Any]], lang: str = "pt_br") -> str:
        """Delegates Section 3 table formatting to MFDTableFormatter."""
        return MFDTableFormatter.get_section_5_synthesis_table(intersections_list, lang=lang)

    @classmethod
    def get_section_6_consolidated_summary(cls, normalized_data: Dict[str, Any], lang: str = "pt_br") -> str:
        """Delegates Section 4 summary formatting to MFDTableFormatter."""
        return MFDTableFormatter.get_section_6_consolidated_summary(normalized_data, lang=lang)

    @classmethod
    def generate_deterministic_justification(cls, row: Dict[str, Any], lang: str = "pt_br") -> str:
        """Delegates technical justification resolution to MFDJustificationResolver."""
        return MFDJustificationResolver.generate_deterministic_justification(row, lang=lang)

    @classmethod
    def get_intersection_audit_sheet_template(cls, row: Dict[str, Any], justification: str = None, lang: str = "pt_br") -> str:
        """Delegates Anexo I Audit Sheet formatting to MFDAuditSheetFormatter."""
        return MFDAuditSheetFormatter.get_intersection_audit_sheet_template(row, justification=justification, lang=lang)

    @classmethod
    def get_intersection_ficha_template(cls, row: Dict[str, Any], justificativa: str = None, lang: str = "pt_br") -> str:
        """Backwards-compatible alias for get_intersection_audit_sheet_template."""
        return cls.get_intersection_audit_sheet_template(row, justification=justificativa, lang=lang)
