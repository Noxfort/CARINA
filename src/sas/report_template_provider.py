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

import os
import json
import logging
import re

class ReportTemplateProvider:
    """
    Dynamically loads and provides all static text templates, bilingual formatting, 
    and traffic engineering equation explanations (LaTeX) from a JSON config file.
    Follows SOLID design principles.
    """
    _templates_cache = None

    @classmethod
    def _load_templates(cls) -> dict:
        """Loads the template JSON file into cache if not already loaded."""
        if cls._templates_cache is not None:
            return cls._templates_cache

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "config", "report_templates.json")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                cls._templates_cache = json.load(f)
                logging.info(f"[TEMPLATE_PROVIDER] Successfully loaded report templates from: {json_path}")
        except Exception as e:
            logging.error(f"[TEMPLATE_PROVIDER] Error loading report templates JSON from {json_path}: {e}")
            # Fallback to an empty dict to prevent crashes, using dynamic keys handling below
            cls._templates_cache = {}

        return cls._templates_cache

    @classmethod
    def get_template_value(cls, key: str, language: str, default: str = "") -> str:
        """Retrieves a bilingual text value from templates using fallback keys."""
        templates = cls._load_templates()
        lang = language.lower()
        
        # Access nested key structure or return default
        item = templates.get(key, {})
        if isinstance(item, dict):
            return item.get(lang, item.get("pt_br", default))
        return default

    @classmethod
    def get_introducao_title(cls, language: str) -> str:
        return cls.get_template_value("introducao_title", language, default="## 1. Introdução e Contexto Executivo")

    @classmethod
    def get_auditoria_title(cls, language: str) -> str:
        return cls.get_template_value("auditoria_title", language, default="## 3. Detalhamento de Auditoria e Decisões por Cruzamento\n\n")

    @classmethod
    def get_equations_section(cls, language: str) -> str:
        return cls.get_template_value("equations_section", language)

    @classmethod
    def get_recommendation_labels(cls, is_add: bool, is_remove: bool, is_keep: bool, is_no_signal: bool, language: str, is_optimize: bool = False) -> str:
        templates = cls._load_templates()
        rec_dict = templates.get("recommendations", {}).get(language.lower(), templates.get("recommendations", {}).get("pt_br", {}))
        
        if is_optimize:
            return rec_dict.get("optimize", "OTIMIZAR SEMÁFORO")
        elif is_add:
            return rec_dict.get("add", "ADICIONAR SEMÁFORO")
        elif is_remove:
            return rec_dict.get("remove", "REMOVER SEMÁFORO")
        elif is_no_signal:
            return rec_dict.get("no_signal", "MANTER NÃO SINALIZADO")
        return rec_dict.get("keep", "MANTER SEMÁFORO")

    @classmethod
    def get_status_label(cls, status_raw: str, language: str) -> str:
        templates = cls._load_templates()
        status_dict = templates.get("status", {}).get(language.lower(), templates.get("status", {}).get("pt_br", {}))
        
        is_active = any(x in status_raw.lower() for x in ["sinalizado", "active", "yes", "true", "1"]) and not any(x in status_raw.lower() for x in ["não", "nao", "un", "no_signal"])
        if is_active:
            return status_dict.get("active", "Sinalizado")
        return status_dict.get("inactive", "Não Sinalizado")

    @classmethod
    def get_intersection_block(cls, j_id: str, status_formatted: str, vol_p: float, vol_s: float, 
                                delay: float, queue: int, sat: float, rec_formatted: str, 
                                justificativa_rica: str, language: str,
                                lanes_p: int = 1, lanes_s: int = 1,
                                speed_p: float = 50.0, speed_s: float = 40.0,
                                len_p: float = 100.0, len_s: float = 100.0) -> str:
        from sas.sas_helpers import formatar_br

        vol_p_str = formatar_br(vol_p, 1)
        vol_s_str = formatar_br(vol_s, 1)
        delay_str = formatar_br(delay, 1)
        sat_str = formatar_br(sat, 2)
        speed_p_str = formatar_br(speed_p, 0)
        speed_s_str = formatar_br(speed_s, 0)
        len_p_str = formatar_br(len_p, 0)
        len_s_str = formatar_br(len_s, 0)

        # Vary sentence starters for justifications in Anexo I if justification is default/robotic
        starters = [
            f"A auditoria viária do cruzamento ID {j_id} evidencia que a saturação no cruzamento é crítica, ",
            f"A avaliação de desempenho no nó viário ID {j_id} demonstra que há saturação crítica no local, ",
            f"O diagnóstico técnico do cruzamento ID {j_id} indica que a saturação viária atingiu nível crítico, ",
            f"A análise operacional do entroncamento ID {j_id} atesta a presença de saturação crítica no cruzamento, "
        ]
        if justificativa_rica and ("A análise de dados revela" in justificativa_rica or "A recomendação de" in justificativa_rica):
            chosen_starter = starters[abs(hash(str(j_id))) % len(starters)]
            justificativa_rica = re.sub(r"^(A\s+análise\s+de\s+dados\s+revela|A\s+recomendação\s+de\s+[^\s]+\s+semáforo\s+é\s+obrigatória|A\s+recomendação\s+técnica\s+é\s+a\s+edição)\s*(que|uma|devido)?\s*([àa]\s+)?(saturação\s+crítica)?\s*(no\s+cruzamento)?\s*(com\s+uma\s+taxa)?\s*", chosen_starter, justificativa_rica, flags=re.IGNORECASE)

        template_str = (
            f"### Cruzamento: ID {j_id}\n"
            f"**Status Atual:** {status_formatted}\n"
            f"**Caracterização Física das Vias:**\n"
            f"  - Via Principal: {lanes_p} faixa(s) | V_reg: {speed_p_str} km/h | Extensão: {len_p_str} m\n"
            f"  - Via Secundária: {lanes_s} faixa(s) | V_reg: {speed_s_str} km/h | Extensão: {len_s_str} m\n"
            f"**Métricas Obtidas:**\n"
            f"  - Volume Medido: {vol_p_str} vph na via principal e {vol_s_str} vph na secundária.\n"
            f"  - Atraso Médio: {delay_str} segundos.\n"
            f"  - Fila Máxima (P95): {queue} veículos.\n"
            f"  - Taxa de Saturação (X): {sat_str}.\n"
            f"Diagnóstico Viário: {rec_formatted}\n"
            f"**Justificativa Técnico-Gerencial:** {justificativa_rica}\n\n"
        )
        return template_str

    @classmethod
    def get_intersection_ficha_template(cls, clean_j_id: str, status_formatted: str, rec_formatted: str,
                                       vol_p: float, vol_s: float, delay: float, queue: int, sat: float,
                                       is_critical: bool, justificativa: str, language: str,
                                       lanes_p: int = 1, lanes_s: int = 1,
                                       speed_p: float = 50.0, speed_s: float = 40.0,
                                       len_p: float = 100.0, len_s: float = 100.0) -> str:
        """Alias wrapper method for get_intersection_block."""
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
    def get_consolidated_summary(cls, total_junctions: int, keep_count: int, remove_count: int, 
                                 add_count: int, no_signal_count: int, language: str, optimize_count: int = 0) -> str:
        lang = (language or "pt_br").lower()
        items = []
        if optimize_count > 0:
            items.append(f"- **Otimizar Semáforo:** {optimize_count} (Reprogramação de ciclo e integração à central semafórica)" if lang == "pt_br" else f"- **Optimize Traffic Light:** {optimize_count}")
        if add_count > 0:
            items.append(f"- **Adicionar Semáforo:** {add_count} (Instalação nova recomendada por saturação crítica)" if lang == "pt_br" else f"- **Add Traffic Light:** {add_count}")
        if keep_count > 0:
            items.append(f"- **Manter Semáforo:** {keep_count} (Preservação da onda verde e operação estável)" if lang == "pt_br" else f"- **Maintain Traffic Light:** {keep_count}")
        if remove_count > 0:
            items.append(f"- **Remover Semáforo:** {remove_count} (Eliminação de atraso artificial)" if lang == "pt_br" else f"- **Remove Traffic Light:** {remove_count}")
        if no_signal_count > 0:
            items.append(f"- **Manter Não Sinalizado:** {no_signal_count} (Fluxo adequado sob sinalização passiva de Parada/Preferência)" if lang == "pt_br" else f"- **Maintain Unsignalized:** {no_signal_count}")
        if not items:
            items.append("- **Operação Estável:** Todos os cruzamentos operando dentro dos limiares normativos.")

        items_str = "\n".join(items)
        if lang == "pt_br":
            return f"Resumo Consolidado de Intervenções e Recomendação de Ações\n\n**Total de Cruzamentos Avaliados:** {total_junctions}\n{items_str}\n\n"
        else:
            return f"Consolidated Summary of Interventions and Recommendations\n\n**Total Intersections Evaluated:** {total_junctions}\n{items_str}\n\n"

    @classmethod
    def get_consolidated_summary_text(cls, total_intersections: int, keep_count: int, remove_count: int,
                                       add_count: int, no_signal_count: int, language: str = "pt_br", optimize_count: int = 0) -> str:
        """Alias wrapper method for get_consolidated_summary."""
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
    def get_conclusions_section(cls, add_count: int, remove_count: int, keep_count: int, 
                                 no_signal_count: int, conclusion_text: str, has_last_report: bool, language: str, optimize_count: int = 0) -> str:
        lang = (language or "pt_br").lower()
        items = []
        item_idx = 1

        if lang == "pt_br":
            header = "### Diretrizes Operacionais por Categoria de Intervenção\n\nCom base no parecer do motor CARINA v1.0 (SAS Engine), recomendam-se as seguintes diretrizes:\n\n"
            if add_count > 0:
                items.append(f"{item_idx}. **Para os cruzamentos a serem adicionados ({add_count} ponto(s)):** Iniciar estudos geotécnicos e infraestrutura elétrica para instalação das colunas semafóricas, priorizando a segurança de manobra.")
                item_idx += 1
            if optimize_count > 0:
                items.append(f"{item_idx}. **Para os cruzamentos a serem otimizados ({optimize_count} ponto(s)):** Reajustar tempos de ciclo, planos de fases e sincronismo de onda verde para mitigar atrasos e saturação crítica.")
                item_idx += 1
            if remove_count > 0:
                items.append(f"{item_idx}. **Para os cruzamentos a serem removidos ({remove_count} ponto(s)):** Executar desligamento programado e transição para sinalização vertical (placas de Pare/Dê a Preferência) para extinguir atrasos artificiais.")
                item_idx += 1
            if keep_count > 0:
                items.append(f"{item_idx}. **Para os cruzamentos a serem mantidos ({keep_count} ponto(s)):** Preservar a integração e os tempos de ciclo vigentes para manter a estabilidade operacional.")
                item_idx += 1
            if no_signal_count > 0:
                items.append(f"{item_idx}. **Para os cruzamentos mantidos sem sinalização ({no_signal_count} ponto(s)):** Preservar o regime de preferência física atual sem alocação de semáforo.")
                item_idx += 1
            if not items:
                items.append("Nenhum cruzamento requer alteração na sinalização atual.")
        else:
            header = "### Operational Directives by Intervention Category\n\nBased on CARINA v1.0 (SAS Engine) diagnostics, the following actions are recommended:\n\n"
            if add_count > 0:
                items.append(f"{item_idx}. **For intersections to be added ({add_count} point(s)):** Initiate electrical and physical layout for traffic signal installation.")
                item_idx += 1
            if optimize_count > 0:
                items.append(f"{item_idx}. **For intersections to be optimized ({optimize_count} point(s)):** Adjust cycle timings, phase plans, and green wave coordination.")
                item_idx += 1
            if remove_count > 0:
                items.append(f"{item_idx}. **For intersections to be removed ({remove_count} point(s)):** Implement scheduled deactivation and transition to passive signage.")
                item_idx += 1
            if keep_count > 0:
                items.append(f"{item_idx}. **For intersections to be maintained ({keep_count} point(s)):** Preserve existing signal timing and green wave coordination.")
                item_idx += 1
            if no_signal_count > 0:
                items.append(f"{item_idx}. **For intersections maintained unsignalized ({no_signal_count} point(s)):** Preserve passive right-of-way control.")
                item_idx += 1
            if not items:
                items.append("No intersections require signalization changes.")

        base_text = header + "\n".join(items) + "\n\n"
            
        if has_last_report and conclusion_text and len(conclusion_text) > 10:
            base_text += f"{conclusion_text}\n"
            
        return base_text

    @classmethod
    def get_layout_translations(cls, language: str) -> dict:
        templates = cls._load_templates()
        translations = templates.get("translations", {})
        return translations.get(language.lower(), translations.get("pt_br", {}))

    @classmethod
    def get_cluster_prefix(cls, language: str = "pt_br") -> str:
        translations = cls.get_layout_translations(language)
        return translations.get("cluster_prefix", "Agrupamento" if language.lower() == "pt_br" else "Cluster")
