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

# File: src/blocks/report_post_processor.py
# Author: Gabriel Moraes
# Date: August 9, 2026

from typing import Any
from blocks.report_number_formatter import ReportNumberFormatter
from blocks.report_text_sanitizer import ReportTextSanitizer
from blocks.report_semantic_cleaner import ReportSemanticCleaner

class ReportPostProcessor:
    """
    Responsibility (SRP): Global Facade for ABNT report post-processing, coordinating
    number formatting, LLM text sanitization, and semantic consistency cleaning.
    """

    @staticmethod
    def get_configured_distance_unit() -> str:
        return ReportNumberFormatter.get_configured_distance_unit()

    @staticmethod
    def get_configured_time_unit() -> str:
        return ReportNumberFormatter.get_configured_time_unit()

    @staticmethod
    def get_configured_decimal_separator() -> str:
        return ReportNumberFormatter.get_configured_decimal_separator()

    @staticmethod
    def get_configured_thousands_separator() -> str:
        return ReportNumberFormatter.get_configured_thousands_separator()

    @classmethod
    def format_number(cls, val: Any, decimal_places: int = 1) -> str:
        return ReportNumberFormatter.format_number(val, decimal_places=decimal_places)

    @classmethod
    def clean_ai_preamble(cls, text: str) -> str:
        return ReportTextSanitizer.clean_ai_preamble(text)

    @classmethod
    def format_executive_summary(cls, raw_summary: str, intervention_rate: float) -> str:
        return ReportTextSanitizer.format_executive_summary(raw_summary, intervention_rate)

    @staticmethod
    def deduplicate_justification_paragraphs(text: str) -> str:
        return ReportTextSanitizer.deduplicate_justification_paragraphs(text)

    @classmethod
    def sanitize_zero_maintenance_protocol(cls, text: str, keep_count: int) -> str:
        return ReportTextSanitizer.sanitize_zero_maintenance_protocol(text, keep_count)

    @staticmethod
    def sanitize_truncated_text(text: str) -> str:
        return ReportTextSanitizer.sanitize_truncated_text(text)

    @classmethod
    def enforce_semantic_consistency(cls, text: str, is_signalized: bool = True) -> str:
        return ReportSemanticCleaner.enforce_semantic_consistency(text, is_signalized=is_signalized)
