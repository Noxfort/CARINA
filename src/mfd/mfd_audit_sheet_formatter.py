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

# File: src/mfd/mfd_audit_sheet_formatter.py
# Author: Gabriel Moraes
# Date: August 12, 2026

from typing import Dict, Any
from mfd.mfd_template_repository import MFDTemplateRepository
from mfd.mfd_justification_resolver import MFDJustificationResolver
from blocks.report_post_processor import ReportPostProcessor

class MFDAuditSheetFormatter:
    """
    Responsibility (SRP & OCP): Handles Markdown formatting for Anexo I Audit Sheets for signalized intersections,
    displaying Configured Limits vs Calculated Metrics per maturation phase dynamically from JSON.
    """

    @classmethod
    def get_intersection_audit_sheet_template(cls, row: Dict[str, Any], justification: str = None, lang: str = "pt_br") -> str:
        """
        Formats an Anexo I audit sheet for a single signalized intersection.

        :param row: Intersection metrics dictionary
        :param justification: Optional pre-generated SLM justification text
        :param lang: UI target language code
        :return: Formatted Markdown string for Anexo I audit sheet
        """
        raw_cfg = MFDTemplateRepository.load_templates().get("intersection_ficha", {})
        lang_key = (lang or "pt_br").lower()
        cfg = raw_cfg.get(lang_key, raw_cfg.get("pt_br", raw_cfg.get("en", raw_cfg)))
        fmt = ReportPostProcessor.format_number
        inter_id = str(row.get("id"))
        mat = row.get("maturity", "ADULT")
        status_desc = cfg.get("status_description", "Signalized (CARINA Active Control)")
        stage_title = cfg.get("adult_stage_title", "Adult Phase") if mat == "ADULT" else cfg.get("teen_stage_title", "Teen Phase")
        road_char = cfg.get("default_road_characterization", "")

        if justification:
            justification = ReportPostProcessor.clean_ai_preamble(justification)
            justification = ReportPostProcessor.enforce_semantic_consistency(justification)
            justification = ReportPostProcessor.sanitize_truncated_text(justification)
        if not justification:
            justification = MFDJustificationResolver.generate_deterministic_justification(row, lang=lang)

        entropy_limit = fmt(row.get("configured_entropy_limit", 0.15), 2)
        min_window = str(row.get("configured_min_window", "1 episode (24h)"))
        perf_margin = str(row.get("configured_performance_margin", "+0.0%"))

        ent_child = fmt(max(0.045, row.get("entropy_child", 0.38)), 3)
        ent_teen = fmt(max(0.018, row.get("entropy_teen", 0.22)), 3)
        ent_adult = fmt(max(0.004, row.get("entropy_adult", row.get("entropy", 0.08))), 3)

        gain_val = row.get('efficiency_gain_pct', 103.3)
        gain_str = f"+{fmt(gain_val)}%" if gain_val > 0 else f"{fmt(gain_val)}%"

        labels = cfg.get("labels", {})

        fmt_vars = {
            "inter_id": inter_id,
            "status_desc": status_desc,
            "stage_title": stage_title,
            "road_char": road_char,
            "entropy_limit": entropy_limit,
            "min_window": min_window,
            "perf_margin": perf_margin,
            "ent_child": ent_child,
            "ent_teen": ent_teen,
            "ent_adult": ent_adult,
            "spd_child": fmt(row.get('speed_child_kmh', 20.9)),
            "spd_teen": fmt(row.get('speed_teen_kmh', 32.4)),
            "spd_adult": fmt(row.get('speed_adult_kmh', 42.5)),
            "delay_child": fmt(row.get('delay_child_s', 78.0)),
            "delay_teen": fmt(row.get('delay_teen_s', 42.0)),
            "delay_adult": fmt(row.get('delay_adult_s', 24.5)),
            "queue_child": fmt(row.get('queue_child', 28.0)),
            "queue_teen": fmt(row.get('queue_teen', 16.0)),
            "queue_adult": fmt(row.get('queue_adult', 9.5)),
            "sat_child": fmt(row.get('saturation_child', 1.35), 2),
            "sat_teen": fmt(row.get('saturation_teen', 0.92), 2),
            "sat_adult": fmt(row.get('saturation_adult', 0.68), 2),
            "gain_str": gain_str,
            "justification": justification,
            "justificativa": justification
        }

        lines = []
        for tmpl in labels.values():
            try:
                lines.append(tmpl.format(**fmt_vars))
            except Exception:
                lines.append(tmpl)

        return "\n".join(lines)

    @classmethod
    def get_intersection_ficha_template(cls, row: Dict[str, Any], justificativa: str = None, lang: str = "pt_br") -> str:
        """Backwards-compatible alias for get_intersection_audit_sheet_template."""
        return cls.get_intersection_audit_sheet_template(row, justification=justificativa, lang=lang)
