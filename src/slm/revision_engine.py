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

# File: src/slm/revision_engine.py
# Author: Gabriel Moraes
# Date: July 29, 2026

import os
import json
import logging
from typing import Any
from slm.output_sanitizer import SLMOutputSanitizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SLM_REVISION] - %(levelname)s - %(message)s')

class SLMRevisionEngine:
    """
    Executes 2nd Pass Neural Proofreading in a 100% clean memory context window.
    Strictly corrects typos and grammar while enforcing anti-hallucination boundary rules.
    """

    @staticmethod
    def load_revision_prompt(language: str = "pt_br") -> str:
        """Loads prompt from src/prompts/slm_revision_prompts.json."""
        prompts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "slm_revision_prompts.json")
        default_inst = "Você é um Revisor Linguístico Técnico. Corrija o texto com máxima elegância e formalidade, preservando integralmente números, datas e recomendações."
        
        lang_key = str(language).lower()
        if lang_key.startswith("pt"):
            lang_key = "pt_br"
        elif lang_key.startswith("en"):
            lang_key = "en"
        elif lang_key.startswith("es"):
            lang_key = "es"

        try:
            if os.path.exists(prompts_file):
                with open(prompts_file, "r", encoding="utf-8") as f:
                    rev_db = json.load(f)
                    rev_opts = rev_db.get("OFFICIAL_TEXT_REVISION", {})
                    return rev_opts.get(lang_key, rev_opts.get("pt_br", rev_opts.get("en", default_inst)))
        except Exception as e:
            logging.warning(f"[SLMRevisionEngine] Could not load slm_revision_prompts.json: {e}")
        return default_inst

    @staticmethod
    def review_text(model: Any, draft_text: str, language: str = "pt_br") -> str:
        """
        Runs proofreading inference on model using clean memory context.
        Enforces length boundary checks to reject hallucinatory expansions or deletions.
        """
        if not draft_text or len(draft_text.strip()) < 10:
            return draft_text

        instruction = SLMRevisionEngine.load_revision_prompt(language)
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": f"TEXTO_PARA_REVISAR:\n{draft_text}"}
        ]

        draft_len = len(draft_text.strip())
        logging.info(f"[SLM_REVISION] Starting 2nd Pass Neural Proofreading on {draft_len} chars of narrative text...")

        try:
            # Estimate prompt tokens and dynamically scale max_tokens
            prompt_str = f"<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>user\nTEXTO_PARA_REVISAR:\n{draft_text}<|im_end|>\n"
            try:
                prompt_tokens = len(model.tokenize(prompt_str.encode('utf-8')))
            except Exception:
                prompt_tokens = int(len(prompt_str) / 3.5)

            n_ctx = 8192
            safety_buffer = 128
            max_gen_tokens = n_ctx - prompt_tokens - safety_buffer
            max_tokens = max(512, min(4096, max_gen_tokens))

            logging.info(f"[SLM_REVISION] Proofreading Prompt Tokens: {prompt_tokens}, Dynamic max_tokens: {max_tokens}")

            outputs = model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.0,
                repeat_penalty=1.05
            )
            raw_revised = outputs["choices"][0]["message"]["content"]
            revised_text = SLMOutputSanitizer.sanitize(raw_revised)
            
            # Anti-hallucination check: if revision deleted >60%, expanded >100%, or hallucinated mock Cruzamento A, fallback to draft
            if "Cruzamento A" in revised_text or "Cruzamento B" in revised_text or "| Cruzamento" in revised_text:
                logging.warning("[SLM_REVISION] Mock table hallucination detected in revision. Falling back to original draft.")
                return draft_text.strip()

            if len(revised_text) < draft_len * 0.4 or len(revised_text) > draft_len * 2.0:
                logging.warning(f"[SLM_REVISION] Extreme output length change detected ({len(revised_text)} vs {draft_len}). Falling back to original draft.")
                return draft_text.strip()

            logging.info(f"[SLM_REVISION] Neural proofreading completed successfully ({len(revised_text)} chars generated).")
            return revised_text
        except Exception as e:
            logging.warning(f"[SLM_REVISION] Neural revision failed: {e}. Returning original draft.")
            return draft_text.strip()
