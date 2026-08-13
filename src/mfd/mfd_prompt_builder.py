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

# File: src/mfd/mfd_prompt_builder.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import os
import json
import logging
from typing import Dict, Any, List

class MFDPromptBuilder:
    """
    Responsibility (SRP & OCP): Build compact, lightweight prompt payloads (< 350 tokens) for SLM Transducer inference.
    All attribute schemas, stage descriptions, and numeric fallbacks are loaded dynamically from config/mfd_prompts.json.
    Follows SOLID Open/Closed Principle (OCP).
    """

    _prompts_cache: Dict[str, Any] = None

    @classmethod
    def _load_prompts_config(cls) -> Dict[str, Any]:
        """Loads prompt configurations, verdict texts, and attribute schemas from config/mfd_prompts.json with caching."""
        if cls._prompts_cache is not None:
            return cls._prompts_cache

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "config", "mfd_prompts.json")

        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    cls._prompts_cache = json.load(f)
                    logging.info(f"[MFDPromptBuilder] Loaded prompt configs from {json_path}")
                    return cls._prompts_cache
            except Exception as e:
                logging.warning(f"[MFDPromptBuilder] Failed to load JSON '{json_path}': {e}. Using fallback.")

        cls._prompts_cache = {}
        return cls._prompts_cache

    @classmethod
    def get_stage_description(cls, stage_key: str, lang: str = "pt_br") -> str:
        """Resolves stage description string from JSON configuration across languages."""
        cfg = cls._load_prompts_config()
        stages = cfg.get("stage_descriptions", {})
        lang_key = (lang or "pt_br").lower()

        stage_obj = stages.get(stage_key, stages.get("ADULT", {}))
        if isinstance(stage_obj, dict):
            return stage_obj.get(lang_key, stage_obj.get("pt_br", stage_obj.get("en", "")))
        return str(stage_obj)

    @classmethod
    def _resolve_path_value(cls, source: Any, path: Any, default: Any = None) -> Any:
        """Helper to safely resolve dot-separated paths or list of paths from source dictionary."""
        if isinstance(path, list):
            for p in path:
                val = cls._resolve_path_value(source, p, None)
                if val is not None and val != "":
                    return val
            return default

        if not isinstance(path, str):
            return default

        parts = path.split('.')
        curr = source
        for part in parts:
            if isinstance(curr, dict):
                curr = curr.get(part)
            else:
                return default
        return curr if curr is not None else default

    @classmethod
    def _build_attributes_from_schema(
        cls,
        schema_key: str,
        source_data: Dict[str, Any],
        custom_values: Dict[str, Any] = None,
        lang: str = "pt_br"
    ) -> Dict[str, Any]:
        """Dynamically maps source data into attribute dictionary using external JSON schema."""
        cfg = cls._load_prompts_config()
        schema = cfg.get("attribute_schemas", {}).get(schema_key, {})
        lang_key = (lang or "pt_br").lower()
        custom_values = custom_values or {}

        resolved_attributes = {}

        for attr_name, field_def in schema.items():
            if attr_name in custom_values:
                resolved_attributes[attr_name] = custom_values[attr_name]
                continue

            custom_type = field_def.get("custom_type")
            if custom_type and custom_type in custom_values:
                resolved_attributes[attr_name] = custom_values[custom_type]
                continue

            default_val = field_def.get("default")
            default_key = field_def.get("default_key")

            if default_key:
                def_obj = cfg.get(default_key, {})
                if isinstance(def_obj, dict):
                    default_val = def_obj.get(lang_key, def_obj.get("pt_br", ""))
                else:
                    default_val = str(def_obj)

            path = field_def.get("path")
            if path:
                val = cls._resolve_path_value(source_data, path, default_val)
                resolved_attributes[attr_name] = val
            else:
                resolved_attributes[attr_name] = default_val

        return resolved_attributes

    @classmethod
    def build_executive_summary_input(cls, normalized_data: Dict[str, Any], lang: str = "pt_br") -> Dict[str, Any]:
        """Builds a compact summary payload for Section 3 Executive Summary."""
        cfg = cls._load_prompts_config()
        engine_name = cfg.get("engine_name", "CARINA v1.0 (MFD Engine)")
        summary_stats = normalized_data.get("summary_stats", {})

        summary_data = cls._build_attributes_from_schema("executive_summary", normalized_data, lang=lang)
        if summary_stats:
            summary_data.update(summary_stats)

        return {
            "mode": "MFD_OPTIMIZATION",
            "language": lang,
            "sub_mode": "EXECUTIVE_SUMMARY",
            "engine_name": engine_name,
            "attributions": summary_data,
            "first_analysis_timestamp": summary_stats.get("comparison_since_first_analysis", {}).get("first_analysis_timestamp")
        }

    @classmethod
    def build_single_intersection_input(cls, inter_row: Dict[str, Any], lang: str = "pt_br") -> Dict[str, Any]:
        """Builds a compact payload for a single intersection DA SILVA maturation justification."""
        cfg = cls._load_prompts_config()
        engine_name = cfg.get("engine_name", "CARINA v1.0 (MFD Engine)")
        inter_verdicts = cfg.get("verdicts", {}).get("intersection", {})
        lang_key = (lang or "pt_br").lower()

        mat = inter_row.get("maturity", "ADULT")
        stage_desc = cls.get_stage_description(mat, lang=lang)
        gain = inter_row.get("efficiency_gain_pct", 0.0)

        verdict_obj = inter_verdicts.get("positive" if gain > 0 else "negative", {})
        verdict = verdict_obj.get(lang_key, verdict_obj.get("pt_br", verdict_obj.get("en", ""))) if isinstance(verdict_obj, dict) else str(verdict_obj)

        custom_vals = {
            "stage_description": stage_desc,
            "intersection_verdict": verdict
        }

        attr = cls._build_attributes_from_schema("single_intersection", inter_row, custom_values=custom_vals, lang=lang)

        return {
            "mode": "MFD_OPTIMIZATION",
            "language": lang,
            "sub_mode": "SINGLE_INTERSECTION_AUDIT",
            "engine_name": engine_name,
            "attributions": attr
        }

    @classmethod
    def build_final_opinion_input(cls, normalized_data: Dict[str, Any], lang: str = "pt_br") -> Dict[str, Any]:
        """Builds a compact synthesis payload for Section 7 Final Technical Opinion."""
        cfg = cls._load_prompts_config()
        engine_name = cfg.get("engine_name", "CARINA v1.0 (MFD Engine)")
        opinion_cfg = cfg.get("verdicts", {}).get("final_opinion", {})
        lang_key = (lang or "pt_br").lower()

        impacts = normalized_data.get("impact_stats", {})
        comp = impacts.get("comparative_table", {})
        speed_gain = comp.get("speed_kmh", {}).get("delta_pct", 103.3)

        outcome = opinion_cfg.get("positive_outcome" if speed_gain > 0 else "negative_outcome", "APROVAÇÃO_E_HOMOLOGAÇÃO")
        verdict_obj = opinion_cfg.get("positive_verdict" if speed_gain > 0 else "negative_verdict", {})
        verdict = verdict_obj.get(lang_key, verdict_obj.get("pt_br", verdict_obj.get("en", ""))) if isinstance(verdict_obj, dict) else str(verdict_obj)

        custom_vals = {
            "final_opinion_outcome": outcome,
            "final_opinion_verdict": verdict
        }

        attr = cls._build_attributes_from_schema("final_opinion", normalized_data, custom_values=custom_vals, lang=lang)

        return {
            "mode": "MFD_OPTIMIZATION",
            "language": lang,
            "sub_mode": "FINAL_TECHNICAL_OPINION",
            "engine_name": engine_name,
            "attributions": attr
        }

    @classmethod
    def build_conclusions_input(cls, normalized_data: Dict[str, Any], lang: str = "pt_br") -> Dict[str, Any]:
        """Builds a compact payload for Section 6 Conclusions and Impact Valuation."""
        cfg = cls._load_prompts_config()
        engine_name = cfg.get("engine_name", "CARINA v1.0 (MFD Engine)")
        conc_cfg = cfg.get("verdicts", {}).get("conclusions", {})
        lang_key = (lang or "pt_br").lower()

        impacts = normalized_data.get("impact_stats", {})
        comp = impacts.get("comparative_table", {})
        speed_gain = comp.get("speed_kmh", {}).get("delta_pct", 103.3)

        verdict_obj = conc_cfg.get("positive_verdict" if speed_gain > 0 else "negative_verdict", {})
        verdict = verdict_obj.get(lang_key, verdict_obj.get("pt_br", verdict_obj.get("en", ""))) if isinstance(verdict_obj, dict) else str(verdict_obj)

        custom_vals = {
            "conclusions_verdict": verdict
        }

        attr = cls._build_attributes_from_schema("conclusions", normalized_data, custom_values=custom_vals, lang=lang)

        return {
            "mode": "MFD_OPTIMIZATION",
            "language": lang,
            "sub_mode": "CONCLUSIONS",
            "engine_name": engine_name,
            "attributions": attr
        }
