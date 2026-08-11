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

# File: src/sas/report_section_builder.py
# Author: Gabriel Moraes
# Date: July 25, 2026

from typing import List, Dict, Any
from sas.report_template_provider import ReportTemplateProvider

ENGINE_NAME = "CARINA v1.0 (SAS Engine)"

class ReportSectionBuilder:
    """Constructs Markdown text for each ABNT report section with dynamic sequential numbering."""

    @staticmethod
    def build_introduction_section(resumo_executivo: str, sec_num: int = 3, time_window_str: str = "") -> str:
        tw_block = f"**Janela Temporal de Coleta:** {time_window_str}\n\n" if time_window_str else ""
        return f"## {sec_num}. INTRODUÇÃO E CONTEXTO EXECUTIVO\n\n{tw_block}{resumo_executivo}\n\n"

    @staticmethod
    def build_equations_section(ui_language: str, sec_num: int = 4) -> str:
        eq_text = ReportTemplateProvider.get_equations_section(ui_language)
        return eq_text.replace("## 4.", f"## {sec_num}.")

    @staticmethod
    def build_synthetic_table_section(table_rows: List[str], sec_num: int = 5) -> str:
        table_str = "\n".join(table_rows)
        return f"## {sec_num}. AUDITORIA SINTÉTICA DA MALHA VIÁRIA (TABELA 1)\n\n{table_str}\n\n"

    @staticmethod
    def build_summary_conclusions_section(resumo_consolidado: str, secao_conclusao: str, sec_num: int = 6) -> str:
        return f"## {sec_num}. RESUMO CONSOLIDADO E RECOMENDAÇÕES DE AÇÃO\n\n{resumo_consolidado}\n\n{secao_conclusao}\n\n"

    @staticmethod
    def build_comparative_section(clean_comp: str, sec_num: int = 7) -> str:
        if clean_comp and len(clean_comp) > 10:
            return f"## {sec_num}. COMPARATIVO COM PERÍODO ANTERIOR\n\n{clean_comp}\n\n"
        return ""

    @staticmethod
    def build_final_opinion_section(
        total_j_count: int, 
        signalized_count: int,
        unsignalized_count: int,
        add_count: int, 
        optimize_count: int,
        keep_count: int, 
        no_signal_count: int,
        slm_synthesis: str = "",
        agency_name: str = "Prefeitura Municipal",
        department_name: str = "Secretaria Municipal de Mobilidade e Trânsito",
        sec_num: int = 8,
        add_junction_ids: str = "",
        optimize_junction_ids: str = ""
    ) -> str:
        """
        Final Opinion Section
        Contains legal/normative pillars with ENGINE_NAME = "CARINA v1.0 (SAS Engine)":
        1. Legal & methodological framework (CONTRAN / MUTCD)
        2. Executive administrative steps
        3. Formal signature block
        """
        slm_part = f"\n\n{slm_synthesis.strip()}" if slm_synthesis and len(slm_synthesis.strip()) > 10 else ""
        clean_dept = department_name.replace("|", "").strip() if department_name else "Secretaria Municipal de Mobilidade e Trânsito"
        clean_agency = agency_name.replace("|", "").strip() if agency_name else "Prefeitura Municipal"

        add_ids_text = f" (IDs: {add_junction_ids})" if add_junction_ids else ""
        opt_ids_text = f" (IDs: {optimize_junction_ids})" if optimize_junction_ids else ""

        unsignal_clause = ""
        if add_count > 0:
            unsignal_clause = (
                f" Constatou-se que {add_count} cruzamento(s) não sinalizado(s){add_ids_text} operam em nível "
                f"crítico de saturação (X > 0,85) ou com warrants normativos atendidos, exigindo a recomendação técnica "
                f"obrigatória de **ADICIONAR SEMÁFORO** (instalação de nova sinalização semafórica)."
            )
        elif no_signal_count > 0:
            unsignal_clause = f" Os {no_signal_count} cruzamento(s) não sinalizados operam em regime de estabilidade sob sinalização passiva existente."

        signal_clause = ""
        if optimize_count > 0:
            signal_clause = (
                f" Para os {optimize_count} cruzamento(s) sinalizado(s) com alta demanda e gargalos operacionais{opt_ids_text}, "
                f"recomenda-se a **OTIMIZAÇÃO E REPROGRAMAÇÃO DOS TEMPOS DE CICLO E FASES**, preservando a coordenação semafórica."
            )
        elif keep_count > 0:
            signal_clause = f" Os {keep_count} cruzamento(s) sinalizados mantêm operação adequada dentro da capacidade do plano semafórico vigente."

        return (
            f"## {sec_num}. CONSIDERAÇÕES FINAIS E PARECER TÉCNICO\n\n"
            f"A presente auditoria técnica de engenharia de tráfego realizada pelo motor **{ENGINE_NAME}** avaliou a infraestrutura operacional da malha viária municipal ({total_j_count} interseções auditadas), fundamentando as diretrizes executivas do parecer a seguir.{slm_part}\n\n"
            f"Atesta-se categoricamente que todos os diagnósticos, modelos de simulação e pareceres emitidos pelo motor **{ENGINE_NAME}** observam em sua plenitude os critérios matemáticos e normativos vigentes estabelecidos pelo **Manual de Sinalização Semafórica do Conselho Nacional de Trânsito (CONTRAN)** e pelo **Manual on Uniform Traffic Control Devices (MUTCD)**.{unsignal_clause}{signal_clause}\n\n"
            f"Como encaminhamento executivo e administrativo, recomenda-se à Administração Municipal:\n"
            f"1. A expedição dos atos normativos e portarias correspondentes;\n"
            f"2. A elaboração dos projetos executivos geotécnicos e elétricos para os cruzamentos indicados para nova sinalização semafórica ou otimização de ciclo;\n"
            f"3. A integração dos equipamentos à Central de Controle Operacional da **{clean_dept}** ({clean_agency}).\n\n"
            f"Submete-se o presente Laudo Técnico emitido pelo motor **{ENGINE_NAME}** à análise e homologação de Vossa Senhoria para os devidos fins de direito e protocolo oficial.\n\n"
            f"---\n\n"
            f"**Motor Analítico:** {ENGINE_NAME}\n"
            f"**Órgão Solicitante:** {clean_agency} / {clean_dept}\n\n"
        )

    @staticmethod
    def build_annex_section(cruzamentos_detalhe: List[str]) -> str:
        return f"## ANEXO I – FICHAS DE AUDITORIA INDIVIDUALIZADA POR CRUZAMENTO\n\n" + "".join(cruzamentos_detalhe)
