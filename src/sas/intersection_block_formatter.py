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

# File: src/sas/intersection_block_formatter.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import re
from sas.template_repository import TemplateRepository

class IntersectionBlockFormatter:
    """
    Responsibility (SRP): Formats individual intersection Markdown blocks (Anexo I) 
    and handles justification sentence starters variation via Regex.
    Follows SOLID principles.
    """

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
        """
        Formats individual intersection Markdown audit sheet block.

        :param j_id: Intersection identifier
        :param status_formatted: Formatted signalized status label
        :param vol_p: Measured volume on major street (veh/h)
        :param vol_s: Measured volume on minor street (veh/h)
        :param delay: Average delay (seconds)
        :param queue: Maximum queue P95 (vehicles)
        :param sat: Saturation ratio (X)
        :param rec_formatted: Formatted recommendation label
        :param justificativa_rica: Detailed technical justification string
        :param language: Target language code
        :param lanes_p: Number of lanes on major street
        :param lanes_s: Number of lanes on minor street
        :param speed_p: Speed limit on major street (km/h)
        :param speed_s: Speed limit on minor street (km/h)
        :param len_p: Street length on major street (m)
        :param len_s: Street length on minor street (m)
        :return: Completed Markdown intersection block string
        """
        from sas.sas_helpers import formatar_br

        vol_p_str = formatar_br(vol_p, 1)
        vol_s_str = formatar_br(vol_s, 1)
        delay_str = formatar_br(delay, 1)
        sat_str = formatar_br(sat, 2)
        speed_p_str = formatar_br(speed_p, 0)
        speed_s_str = formatar_br(speed_s, 0)
        len_p_str = formatar_br(len_p, 0)
        len_s_str = formatar_br(len_s, 0)

        templates = TemplateRepository.load_templates()
        lang_key = (language or "pt_br").lower()

        # Load justification starters from JSON configuration
        starters_dict = templates.get("justification_starters", {})
        starters = starters_dict.get(lang_key, starters_dict.get("pt_br", []))

        if not starters:
            starters = [
                f"A auditoria viária do cruzamento ID {j_id} evidencia que a saturação no cruzamento é crítica, ",
                f"A avaliação de desempenho no nó viário ID {j_id} demonstra que há saturação crítica no local, ",
                f"O diagnóstico técnico do cruzamento ID {j_id} indica que a saturação viária atingiu nível crítico, ",
                f"A análise operacional do entroncamento ID {j_id} atesta a presença de saturação crítica no cruzamento, "
            ]

        # Load justification replacement rules (triggers and regex) from JSON config
        rules_dict = templates.get("justification_replacement_rules", {})
        lang_rules = rules_dict.get(lang_key, rules_dict.get("pt_br", {}))
        trigger_phrases = lang_rules.get(
            "trigger_phrases",
            ["A análise de dados revela", "A recomendação de", "A recomendação técnica"]
        )
        regex_pattern = lang_rules.get(
            "regex_pattern",
            r"^(A\s+análise\s+de\s+dados\s+revela|A\s+recomendação\s+de\s+[^\s]+\s+semáforo\s+é\s+obrigatória|A\s+recomendação\s+técnica\s+é\s+a\s+edição)\s*(que|uma|devido)?\s*([àa]\s+)?(saturação\s+crítica)?\s*(no\s+cruzamento)?\s*(com\s+uma\s+taxa)?\s*"
        )

        if justificativa_rica and starters and any(phrase in justificativa_rica for phrase in trigger_phrases):
            chosen_starter_raw = starters[abs(hash(str(j_id))) % len(starters)]
            chosen_starter = chosen_starter_raw.format(j_id=j_id) if "{j_id}" in chosen_starter_raw else chosen_starter_raw
            justificativa_rica = re.sub(
                regex_pattern,
                chosen_starter,
                justificativa_rica,
                flags=re.IGNORECASE
            )

        template_block_dict = templates.get("intersection_block", {})
        template_str = template_block_dict.get(lang_key, template_block_dict.get("pt_br", ""))

        if not template_str:
            template_str = (
                f"### Cruzamento: ID {{j_id}}\n"
                f"**Status Atual:** {{status_formatted}}\n"
                f"**Caracterização Física das Vias:**\n"
                f"  - Via Principal: {{lanes_p}} faixa(s) | V_reg: {{speed_p_str}} km/h | Extensão: {{len_p_str}} m\n"
                f"  - Via Secundária: {{lanes_s}} faixa(s) | V_reg: {{speed_s_str}} km/h | Extensão: {{len_s_str}} m\n"
                f"**Métricas Obtidas:**\n"
                f"  - Volume Medido: {{vol_p_str}} vph na via principal e {{vol_s_str}} vph na secundária.\n"
                f"  - Atraso Médio: {{delay_str}} segundos.\n"
                f"  - Fila Máxima (P95): {{queue}} veículos.\n"
                f"  - Taxa de Saturação (X): {{sat_str}}.\n"
                f"Diagnóstico Viário: {{rec_formatted}}\n"
                f"**Justificativa Técnico-Gerencial:** {{justificativa_rica}}\n\n"
            )

        try:
            return template_str.format(
                j_id=j_id,
                status_formatted=status_formatted,
                lanes_p=lanes_p,
                lanes_s=lanes_s,
                speed_p_str=speed_p_str,
                speed_s_str=speed_s_str,
                len_p_str=len_p_str,
                len_s_str=len_s_str,
                vol_p_str=vol_p_str,
                vol_s_str=vol_s_str,
                delay_str=delay_str,
                queue=queue,
                sat_str=sat_str,
                rec_formatted=rec_formatted,
                justificativa_rica=justificativa_rica,
                vol_p=vol_p,
                vol_s=vol_s,
                delay=delay,
                sat=sat
            )
        except Exception:
            return template_str
