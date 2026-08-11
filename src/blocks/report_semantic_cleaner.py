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

# File: src/blocks/report_semantic_cleaner.py
# Author: Gabriel Moraes
# Date: August 9, 2026

import os
import json
import logging
import re
from blocks.report_number_formatter import ReportNumberFormatter

class ReportSemanticCleaner:
    """
    Responsibility (SRP): Enforces ABNT semantic consistency, unit masking, ABNT bold labels,
    RL maturation purges, demographic hallucination purges, and list renumbering via rules in config/semantic_rules.json.
    """

    _semantic_rules_cache = None

    @classmethod
    def _load_semantic_rules(cls) -> dict:
        """Loads semantic consistency rules from config/semantic_rules.json into cache."""
        if cls._semantic_rules_cache is not None:
            return cls._semantic_rules_cache

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "config", "semantic_rules.json")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                cls._semantic_rules_cache = json.load(f)
                logging.info(f"[REPORT_SEMANTIC_CLEANER] Loaded semantic rules from: {json_path}")
        except Exception as e:
            logging.error(f"[REPORT_SEMANTIC_CLEANER] Error loading semantic_rules.json from {json_path}: {e}")
            cls._semantic_rules_cache = {}

        return cls._semantic_rules_cache

    @staticmethod
    def _parse_flags(flags_list: list) -> int:
        flags = 0
        if not flags_list:
            return flags
        for f in flags_list:
            if f.upper() == "IGNORECASE":
                flags |= re.IGNORECASE
            elif f.upper() == "MULTILINE":
                flags |= re.MULTILINE
            elif f.upper() == "DOTALL":
                flags |= re.DOTALL
        return flags

    @classmethod
    def _apply_rule_list(cls, text: str, rule_list: list, replacements_dict: dict = None) -> str:
        if not text or not rule_list:
            return text
        for rule in rule_list:
            pattern = rule.get("pattern", "")
            replacement = rule.get("replacement", "")
            if replacements_dict:
                for k, v in replacements_dict.items():
                    pattern = pattern.replace(f"{{{k}}}", str(v))
                    replacement = replacement.replace(f"{{{k}}}", str(v))
            flags = cls._parse_flags(rule.get("flags", []))
            text = re.sub(pattern, replacement, text, flags=flags)
        return text

    @classmethod
    def enforce_semantic_consistency(cls, text: str, is_signalized: bool = True) -> str:
        """Enforces unit masking, status semantics, lexical/grammatical rules, decimal separators, and ABNT formatting."""
        if not text:
            return ""

        dist_unit = ReportNumberFormatter.get_configured_distance_unit()
        time_unit = ReportNumberFormatter.get_configured_time_unit()

        rules_data = cls._load_semantic_rules()

        # 1. Apply general lexical and grammatical rules
        lexical_rules = rules_data.get("lexical_and_grammar", [])
        text = cls._apply_rule_list(text, lexical_rules)

        # 2. Apply RL maturation tag purges
        rl_rules = rules_data.get("rl_maturation_purges", [])
        text = cls._apply_rule_list(text, rl_rules)

        # 3. Apply demographic and human age hallucination purges
        demographic_rules = rules_data.get("demographic_purges", [])
        text = cls._apply_rule_list(text, demographic_rules)

        # 4. Apply ABNT bold label markers
        abnt_bold_rules = rules_data.get("abnt_bold_label_markers", [])
        text = cls._apply_rule_list(text, abnt_bold_rules)

        # 5. Apply unit masking rules dynamically
        unit_rules = rules_data.get("unit_masking_templates", [])
        text = cls._apply_rule_list(text, unit_rules, {"time_unit": time_unit, "dist_unit": dist_unit})

        # 6. Apply status semantics for unsignalized vs signalized intersections
        status_rules = rules_data.get("status_rules", {})
        if not is_signalized:
            unsig_rules = status_rules.get("unsignalized", [])
            text = cls._apply_rule_list(text, unsig_rules)
        else:
            sig_rules = status_rules.get("signalized", [])
            text = cls._apply_rule_list(text, sig_rules)

        # 7. Apply metadata purges
        metadata_purges = rules_data.get("metadata_purges", [])
        text = cls._apply_rule_list(text, metadata_purges)

        # 8. Decimal separator formatting & double-comma thousands fix
        dec_sep = ReportNumberFormatter.get_configured_decimal_separator()
        if dec_sep == '.':
            # Fix double comma e.g. 2,241,86 -> 2,241.86
            text = re.sub(r"(\b\d{1,3}),(\d{3}),(\d{2})\b", r"\1,\2.\3", text)
            text = re.sub(r"(\b\d+),(\d{1,2})\b", r"\1.\2", text)
        else:
            # Fix double comma e.g. 2,241,86 -> 2.241,86 or 5,354,6 -> 5.354,6
            text = re.sub(r"(\b\d{1,3}),(\d{3}),(\d{1,2})\b", r"\1.\2,\3", text)
            # Fix 4-digit numbers with comma used as thousands before 'segundos' (e.g., 1,582 segundos -> 1.582,0 segundos)
            text = re.sub(r"\b(\d{1,3}),(\d{3})\s*(segundos|s)\b", r"\1.\2,0 \3", text, flags=re.IGNORECASE)
            # Only convert single dots to commas if NOT part of a thousands separator (e.g. 450.0 -> 450,0; but NOT 5.354,6)
            text = re.sub(r"(\b\d+)\.(\d{1,2})(?!\d|,\d)", r"\1,\2", text)
            text = re.sub(r"\bCARINA\s+v1,0\b", "CARINA v1.0 (SAS Engine)", text, flags=re.IGNORECASE)
            text = re.sub(r"\bv1,0\b", "v1.0", text, flags=re.IGNORECASE)

        # 9. Renumber protocol lists starting strictly at 1 if the first item starts with a higher number
        def _renumber_list_from_one(m: re.Match) -> str:
            lines = m.group(0).split('\n')
            new_lines = []
            cur_idx = 1
            for line in lines:
                sub_match = re.match(r"^(\s*)\d+(\.\s+.*)$", line)
                if sub_match:
                    new_lines.append(f"{sub_match.group(1)}{cur_idx}{sub_match.group(2)}")
                    cur_idx += 1
                else:
                    new_lines.append(line)
            return '\n'.join(new_lines)

        text = re.sub(r"(?:^\s*\d+\.\s+.*\n?){2,}", _renumber_list_from_one, text, flags=re.MULTILINE)

        return text
