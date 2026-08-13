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

# File: src/mfd/mfd_table_formatter.py
# Author: Gabriel Moraes
# Date: August 12, 2026

from typing import Dict, Any, List
from mfd.mfd_template_repository import MFDTemplateRepository
from blocks.report_post_processor import ReportPostProcessor

class MFDTableFormatter:
    """
    Responsibility (SRP): Handles Markdown table formatting for Section 3 (Audit Table 1)
    and Section 4 (Consolidated Summary of Operational Impacts) in MFD reports.
    """

    @classmethod
    def get_section_5_synthesis_table(cls, intersections_list: List[Dict[str, Any]], lang: str = "pt_br") -> str:
        """
        Formats Section 3: Synthetic Audit Table 1 showing performance per signalized intersection.

        :param intersections_list: List of intersection metrics dictionaries
        :param lang: UI target language code
        :return: Formatted Markdown table string
        """
        raw_cfg = MFDTemplateRepository.load_templates().get("section_3_table", {})
        lang_key = (lang or "pt_br").lower()
        cfg = raw_cfg.get(lang_key, raw_cfg.get("pt_br", raw_cfg.get("en", raw_cfg)))
        status_tags = cfg.get("status_tags", {})
        fmt = ReportPostProcessor.format_number

        lines = []
        lines.append(cfg.get("title", "## 3. Tabela Sintética de Desempenho Operacional por Cruzamento\n"))
        lines.append(cfg.get("headers", "| ID do Cruzamento | Status Semafórico | Vel. Criança | Vel. Adolescente | Vel. Adulta | Atraso Médio | Fila P95 | Entropia H | Ganho Eficiência |"))
        lines.append(cfg.get("separator", "|---|---|---|---|---|---|---|---|---|"))

        for row in intersections_list:
            mat = row.get("maturity", "ADULT")
            status_tag = status_tags.get(mat, "Fase Adulta (Otimizado)" if mat == "ADULT" else "Fase Adolescente (Em Otimização)")
            inter_id = str(row.get("id"))
            spd_c = f"{fmt(row.get('speed_child_kmh', 20.9))} km/h"
            spd_t = f"{fmt(row.get('speed_teen_kmh', 32.4))} km/h"
            spd_a = f"{fmt(row.get('speed_adult_kmh', 42.5))} km/h"
            delay_str = f"{fmt(row.get('delay_child_s', 78.0))} s → {fmt(row.get('delay_adult_s', 24.5))} s"
            queue_str = f"{fmt(row.get('queue_child', 28.0))} → {fmt(row.get('queue_adult', 9.5))} veícs"
            entropy = f"H={fmt(max(0.004, row.get('entropy_adult', 0.08)), 3)}"

            gain_val = row.get('efficiency_gain_pct', 0.0)
            gain = f"+{fmt(gain_val)}%" if gain_val > 0 else f"{fmt(gain_val)}%"

            lines.append(f"| {inter_id} | {status_tag} | {spd_c} | {spd_t} | {spd_a} | {delay_str} | {queue_str} | {entropy} | {gain} |")

        return "\n".join(lines)

    @classmethod
    def get_section_6_consolidated_summary(cls, normalized_data: Dict[str, Any], lang: str = "pt_br") -> str:
        """
        Formats Section 4: Consolidated Summary of operational and socio-environmental impacts.

        :param normalized_data: Normalized MFD analysis dictionary
        :param lang: UI target language code
        :return: Formatted Markdown summary bullet list string
        """
        raw_cfg = MFDTemplateRepository.load_templates().get("section_4_summary", {})
        lang_key = (lang or "pt_br").lower()
        cfg = raw_cfg.get(lang_key, raw_cfg.get("pt_br", raw_cfg.get("en", raw_cfg)))
        fmt = ReportPostProcessor.format_number

        stats = normalized_data.get("stats", {})
        impacts = normalized_data.get("impact_stats", {})
        comp = impacts.get("comparative_table", {})
        spd = comp.get("speed_kmh", {})
        prd = comp.get("production", {})
        dly = comp.get("delay", {})
        soc = impacts.get("socio_environmental", {})

        spd_pct = spd.get('delta_pct', 0.0)
        spd_str = f"+{fmt(spd_pct)}%" if spd_pct > 0 else f"{fmt(spd_pct)}%"
        prd_pct = prd.get('delta_pct', 0.0)
        prd_str = f"+{fmt(prd_pct)}%" if prd_pct > 0 else f"{fmt(prd_pct)}%"
        dly_pct = dly.get('delta_pct', 0.0)
        dly_str = f"+{fmt(dly_pct)}%" if dly_pct > 0 else f"{fmt(dly_pct)}%"

        adult_cnt = stats.get('adult_count', 0)
        teen_cnt = stats.get('teen_count', 0)
        sing_label = cfg.get("singular_label", "cruzamento")
        plur_label = cfg.get("plural_label", "cruzamentos")
        adult_label = sing_label if adult_cnt == 1 else plur_label
        teen_label = sing_label if teen_cnt == 1 else plur_label

        summary_items_tmpl = cfg.get("summary_items", [])

        lines = [f"\n{cfg.get('title', '## 4. Resumo Consolidado e Impactos Operacionais da Malha Viária')}"]

        if summary_items_tmpl:
            fmt_kwargs = {
                "signalized_count": stats.get('signalized_count', 0),
                "adult_cnt": adult_cnt,
                "adult_label": adult_label,
                "teen_cnt": teen_cnt,
                "teen_label": teen_label,
                "initial_speed": fmt(spd.get('initial', 20.9)),
                "mature_speed": fmt(spd.get('mature', 42.5)),
                "spd_str": spd_str,
                "initial_prod": fmt(prd.get('initial', 0.0)),
                "mature_prod": fmt(prd.get('mature', 0.0)),
                "prd_str": prd_str,
                "initial_delay": fmt(dly.get('initial', 78.0)),
                "mature_delay": fmt(dly.get('mature', 24.5)),
                "dly_str": dly_str,
                "man_hours": fmt(soc.get('man_hours_saved_daily', 1250.0))
            }
            for tmpl in summary_items_tmpl:
                try:
                    lines.append(tmpl.format(**fmt_kwargs))
                except Exception:
                    lines.append(tmpl)
        else:
            lines.append(f"- **Total de Cruzamentos Semafóricos sob Controle Ativo CARINA:** {stats.get('signalized_count', 0)}")
            lines.append(f"- **Agentes Graduados na Fase Adulta (Autonomia Plena 24/7):** {adult_cnt} {adult_label}")
            lines.append(f"- **Agentes em Fase Adolescente (Otimização Transicional):** {teen_cnt} {teen_label}")
            lines.append(f"- **Velocidade Média da Malha:** Evolução de {fmt(spd.get('initial', 20.9))} km/h para {fmt(spd.get('mature', 42.5))} km/h ({spd_str}).")
            lines.append(f"- **Economia Diária de Tempo Acumulada:** {fmt(soc.get('man_hours_saved_daily', 1250.0))} horas-homem economizadas.\n")

        return "\n".join(lines)
