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

# File: src/slm/prompt_builder.py
# Author: Gabriel Moraes
# Date: July 29, 2026

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SLM_PROMPT] - %(levelname)s - %(message)s')

class SLMPromptBuilder:
    """
    Constructs chat-template formatted prompts for Qwen3 / GGUF models from input payload
    and loads system instruction databases (slm_prompts.json).
    """

    @staticmethod
    def load_prompts_db() -> Dict[str, Any]:
        """Loads system prompt database from src/prompts/slm_prompts.json."""
        prompts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "slm_prompts.json")
        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"[SLMPromptBuilder] Could not load slm_prompts.json: {e}")
            return {}

    @staticmethod
    def build_chat_messages(input_data: Dict[str, Any], prompts_db: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """
        Constructs system and user chat messages for LLM inference.
        """
        if prompts_db is None:
            prompts_db = SLMPromptBuilder.load_prompts_db()

        timestamp = input_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        mode = input_data.get("mode", "AUTO")
        raw_language = str(input_data.get("language", "pt_br")).lower()

        lang_key = raw_language.split("_")[0].split("-")[0]
        if lang_key == "pt":
            lang_key = "pt_br"

        attributions = input_data.get("attributions", {})

        speed_unit = input_data.get("speed_unit")
        if not speed_unit and isinstance(attributions, dict):
            speed_unit = attributions.get("speed_unit")

        mode_prompts = prompts_db.get(mode, {})
        instruction = mode_prompts.get(lang_key, mode_prompts.get(raw_language, mode_prompts.get("pt_br", mode_prompts.get("en", "You are a Senior Traffic Engineer for CARINA v1.0."))))

        sub_mode = input_data.get("sub_mode", "")
        if (mode == "MFD_OPTIMIZATION" and sub_mode) or mode == "SINGLE_INTERSECTION_AUDIT":
            if sub_mode == "EXECUTIVE_SUMMARY":
                instruction = "Você atua como Engenheiro de Tráfego Sênior do motor CARINA v1.0 (MFD Engine). Escreva um resumo executivo narrativo curto (2 parágrafos) analisando a mobilidade urbana da cidade com base nas estatísticas fornecidas. REGRA ABSOLUTA DE DADOS: A SLM NÃO DEDUZ OU CALCULA NÚMEROS. Todos os valores (velocidades, atrasos, ganhos %, contagens) são calculados pelo Python e passados no DATA_PAYLOAD. Use EXCLUSIVAMENTE os números exatos recebidos. PROIBIDO gerar títulos, marcas, tabelas, placeholders [VALOR_EXATO_DO_JSON] ou listas de cruzamentos fictícios como Cruzamento A/B/C."
            elif sub_mode == "CONCLUSIONS":
                instruction = "Você atua como Engenheiro de Tráfego Sênior do motor CARINA v1.0 (MFD Engine). Escreva APENAS um parágrafo narrativo curto de síntese das conclusões da malha. REGRA ABSOLUTA: É PROIBIDO gerar títulos de relatório (# LAUDO TÉCNICO DE DESEMPENHO), introduções, seções numeradas (1, 2, 3, 4, 5, 6, 7), tabelas ou pareceres conflitantes. Se o atraso medido for 0.0s, declare que o tráfego operou em fluxo livre sem retenções. PROIBIDO inventar números de atrasos fictícios (como 25s para 12s) ou contradições."
            elif sub_mode == "FINAL_TECHNICAL_OPINION":
                instruction = "Você atua como Engenheiro de Tráfego Sênior do motor CARINA v1.0 (MFD Engine). Escreva um parecer técnico final conclusivo e sintetizado (1 a 2 parágrafos) recomendando a homologação técnica da otimização semafórica MFD. REGRA ABSOLUTA DE DADOS: A SLM NÃO DEDUZ OU CALCULA NÚMEROS. Todos os números são calculados pelo Python e passados no DATA_PAYLOAD. Use EXCLUSIVAMENTE os números exatos recebidos. PROIBIDO gerar títulos (# LAUDO TÉCNICO DE DESEMPENHO), tabelas, relatórios completos, seções numeradas, placeholders ou listas de cruzamentos fictícios."
            elif sub_mode == "SINGLE_INTERSECTION_AUDIT" or mode == "SINGLE_INTERSECTION_AUDIT":
                instruction = "Você atua como Engenheiro de Tráfego Sênior do motor CARINA v1.0 (MFD Engine). Escreva APENAS uma justificativa técnico-gerencial concisa e objetiva (máximo 2 parágrafos curtos) para a ficha individual do cruzamento semafórico. CONCEITO DE IA: As fases Criança/Adolescente/Adulta referem-se EXCLUSIVAMENTE ao nível de autonomia do algoritmo de Aprendizado por Reforço (RL). PROIBIDO qualquer menção a faixas etárias de pessoas, pedestres ou tipos de veículos 'adultos/crianças'. REGRA ABSOLUTA: É PROIBIDO gerar títulos de relatório, introdução, metodologia, seções numeradas (1, 2, 3, 4), cabeçalhos de laudo ou placeholders como [VALOR_EXATO_DO_JSON] ou [Inserir ...]. Substitua e use EXCLUSIVAMENTE os números reais fornecidos no DATA_PAYLOAD."

        # Build prompt string
        input_str = f"TIMESTAMP: [{timestamp}]\nMODE: [{mode}]\nLANGUAGE: [{raw_language}]\n"
        input_str += f"IMPORTANT DIRECTIVE: Write the report text entirely and exclusively in the requested language [{raw_language}]. Strictly forbid answering in English unless LANGUAGE is en.\n"

        if speed_unit:
            input_str += f"SPEED_UNIT: [{speed_unit}]\n"

        if isinstance(attributions, dict):
            input_str += f"DATA_PAYLOAD: {json.dumps(attributions, ensure_ascii=False)}"
        else:
            input_str += f"DATA_PAYLOAD: {str(attributions)}"

        last_report = input_data.get("last_report_text")
        if last_report:
            if len(last_report) > 4000:
                last_report = "... " + last_report[-4000:]
            input_str += f"\nLAST_REPORT_TEXT: {last_report}"

        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": input_str}
        ]

        return messages
