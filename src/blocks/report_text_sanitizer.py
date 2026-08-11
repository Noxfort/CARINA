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

# File: src/blocks/report_text_sanitizer.py
# Author: Gabriel Moraes
# Date: August 9, 2026

import os
import json
import logging
import re

class ReportTextSanitizer:
    """
    Responsibility (SRP): Sanitizes raw LLM output text by stripping conversational preambles,
    placeholders, duplicate paragraphs, zero-maintenance protocol lines, and truncated sentence ends.
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
                logging.info(f"[REPORT_TEXT_SANITIZER] Loaded semantic rules from: {json_path}")
        except Exception as e:
            logging.error(f"[REPORT_TEXT_SANITIZER] Error loading semantic_rules.json from {json_path}: {e}")
            cls._semantic_rules_cache = {}

        return cls._semantic_rules_cache

    @classmethod
    def clean_ai_preamble(cls, text: str) -> str:
        """Strips AI conversational greetings, intro preambles, self-identifications, and residual placeholders."""
        if not text:
            return ""
        if "Cruzamento A" in text or "Cruzamento B" in text or "| Cruzamento" in text:
            return ""
        
        rules_data = cls._load_semantic_rules()
        ai_rules = rules_data.get("ai_preamble_rules", {})

        # Strip literal placeholder artifacts
        placeholders = ai_rules.get("placeholders", [
            r"\[VALOR_EXATO_DO_JSON\]\s*",
            r"\[Valor Exato Fornecido\]\s*",
            r"\[Inserir[^\n\]]*\]\s*",
            r"\[N/A - Dados não fornecidos[^\n\]]*\]\s*"
        ])
        for ph in placeholders:
            text = re.sub(ph, "", text, flags=re.IGNORECASE)

        line_patterns = ai_rules.get("line_match_patterns", [
            r"^(Com certeza|Certamente|Com base|Aqui está|Segue|Como (um|uma)? (assistente|engenheiro|ia)|Olá|Prezado|Analisando os dados|Em resposta ao)",
            r"^(Aqui (está|segue) (o|a) (relatório|laudo|parecer|análise)|Segue abaixo)",
            r"^#*\s*\d*\.?\s*(LAUDO TÉCNICO|INTRODUÇÃO|METODOLOGIA|ANÁLISE|CRITÉRIOS|TABELA|RESUMO|ANEXO)"
        ])

        compiled_line_res = [re.compile(pat, flags=re.IGNORECASE) for pat in line_patterns]

        lines = text.strip().split("\n")
        cleaned_lines = []
        for line in lines:
            l_strip = line.strip()
            if any(pat.match(l_strip) for pat in compiled_line_res):
                continue
            cleaned_lines.append(line)
        result = "\n".join(cleaned_lines).strip()

        header_pattern = ai_rules.get("header_sub_pattern", r"^#*\s*\d*\.?\s*(Introdução|Resumo Executivo|Parecer Técnico|Considerações Finais|Ficha)[^\n]*\n?")
        result = re.sub(header_pattern, "", result, flags=re.IGNORECASE).strip()
        return result

    @classmethod
    def format_executive_summary(cls, raw_summary: str, intervention_rate: float) -> str:
        """Enforces a strict single-paragraph executive summary based on intervention rate."""
        _ = cls.clean_ai_preamble(raw_summary)
        rules_data = cls._load_semantic_rules()
        summary_cfg = rules_data.get("executive_summary", {})

        threshold = summary_cfg.get("high_intervention_threshold", 0.30)
        high_text = summary_cfg.get(
            "high_intervention_text",
            "A análise identificou que expressiva parcela da malha viária opera acima dos limites normativos de saturação, exigindo plano de intervenção prioritária para a readequação semafórica e mitigação dos gargalos identificados."
        )
        stable_text = summary_cfg.get(
            "stable_intervention_text",
            "A malha viária apresenta comportamento predominantemente estável, com intervenções pontuais de ajuste mantendo a fluidez operacional e a segurança nas interseções auditadas."
        )

        if intervention_rate > threshold:
            return high_text
        else:
            return stable_text

    @staticmethod
    def deduplicate_justification_paragraphs(text: str) -> str:
        """Ensures that a justification block contains exactly one concise paragraph."""
        if not text:
            return ""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            return ""
        return paragraphs[0]

    @classmethod
    def sanitize_zero_maintenance_protocol(cls, text: str, keep_count: int) -> str:
        """Omits maintenance directive lines from Section 8 protocol if keep_count == 0."""
        if not text or keep_count > 0:
            return text

        rules_data = cls._load_semantic_rules()
        proto_cfg = rules_data.get("zero_maintenance_protocol", {})

        main_pattern = proto_cfg.get("pattern", r"manutenção\s+do\s+plano\s+semafórico")
        keywords = proto_cfg.get("keywords", ["0,85", "0.85", "<=", "manter"])

        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            if re.search(main_pattern, line, flags=re.IGNORECASE) and any(kw in line.lower() for kw in keywords):
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    @staticmethod
    def sanitize_truncated_text(text: str) -> str:
        """Ensures that document text does not end abruptly mid-sentence."""
        if not text:
            return text
        text = text.strip()
        if not text.endswith(('.', '!', '?', ':', '```', '---')):
            last_punct = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
            if last_punct > len(text) * 0.7:
                text = text[:last_punct + 1]
            else:
                text += "."
        return text
