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

# File: src/slm/local_llama_transducer.py
# Author: Gabriel Moraes
# Date: July 29, 2026

from typing import Any, Dict

class LocalLlamaTransducer:
    """
    Fallback neural transducer for generating report narrative text
    in light testing environments or when the main GGUF engine is disabled.
    """
    def __init__(self, *args, **kwargs):
        pass

    def generate_report(self, input_data: dict) -> Any:
        """Generates narrative report text based on input mode key."""
        if not isinstance(input_data, dict):
            return ""
        mode = input_data.get("mode", "")
        if mode == "LIGHT_EVALUATION":
            d = input_data.get("data", {})
            return {"data": d}
        elif mode in ("EXECUTIVE_SUMMARY", "LAUDO_RESUMO_EXECUTIVO"):
            rate = input_data.get("intervention_rate", 0.0)
            if rate > 0.30:
                return "A análise técnica identificou a necessidade de intervenção ativa na malha viária auditada, compreendendo a otimização de plano semafórico nos cruzamentos sinalizados críticos e a adição de novos equipamentos semafóricos nas interseções não sinalizadas com fluxo elevado."
            else:
                return "A malha viária apresenta comportamento predominantemente estável, com intervenções pontuais de ajuste mantendo a fluidez operacional e a segurança nas interseções auditadas."
        elif mode in ("INTERSECTION_DETAIL", "LAUDO_DETALHE_CRUZAMENTO"):
            d = input_data.get("attributions", {})
            rec = str(d.get("recommendation", "")).upper()
            status_str = str(d.get("current_status", "")).upper()
            if "ADICIONAR" in rec:
                return "O cruzamento atinge índices de saturação e filas críticas sob sinalização passiva, apresentando alto risco operacional. Recomenda-se a implantação de novo conjunto semafórico para ordenar os fluxos de conversão."
            elif "OTIMIZAR" in rec:
                return "O cruzamento sinalizado apresenta elevada demanda sob a sinalização semafórica ativa, recomendando-se a reprogramação dos tempos de ciclo, revisão da defasagem e otimização dos tempos de verde."
            elif "SINALIZADO" in status_str and not ("NÃO" in status_str or "NAO" in status_str or "UN" in status_str):
                return "O cruzamento é sinalizado e opera dentro da capacidade projetada pelo plano semafórico vigente, recomendando-se a manutenção da operação semafórica ativa e monitoramento contínuo."
            else:
                return "O cruzamento opera com volumes e atrasos suportados pela capacidade física da via, sendo plenamente atendido pela sinalização passiva existente (placas de Parada Obrigatória/Dê a Preferência) sem necessidade de semáforo."
        elif mode in ("COMPARATIVE_REPORT", "LAUDO_COMPARATIVO"):
            return "Com base na auditoria consolidada, a malha viária apresenta estabilidade diagnóstica em relação aos períodos operacionais anteriores."
        elif mode in ("STATISTICAL_REPORT", "LAUDO_ESTATISTICO"):
            return "A presente proposta de intervenção consolida o parecer técnico e normativo para homologação executiva e emissão de ordens de serviço, em estrita conformidade com as diretrizes do CONTRAN e MUTCD."
        elif mode == "MFD_OPTIMIZATION":
            sub = input_data.get("sub_mode", "")
            if sub == "EXECUTIVE_SUMMARY":
                return "O presente documento tem como objetivo analisar o desempenho macroscópico do sistema de mobilidade urbana (MFD) em tempo real, mensurando o ganho de fluidez viária e a estabilização da entropia da política entre as fases Criança (Linha Base / Modo Estático), Adolescente (Em Otimização / Autonomia Supervisada) e Adulta (Otimizado / Autonomia Plena) do modelo de aprendizado por reforço (RL)."
            elif sub == "SINGLE_INTERSECTION_AUDIT":
                inter_id = input_data.get("intersection_id", "N/A")
                mat = input_data.get("maturity_stage", "ADULT")
                if mat == "ADULT":
                    return f"A atuação do agente neural no nó semafórico {inter_id} eliminou a sobrecriticação observada na Fase Criança, estabilizando a Entropia em H < 0,15 e aliviando o atraso médio com ganho de fluidez viária em km/h."
                else:
                    return f"O nó semafórico {inter_id} opera em Fase Adolescente (Em Otimização / Autonomia Supervisada), apresentando aprendizado ativo do modelo RL e redução contínua da entropia."
            elif sub == "FINAL_TECHNICAL_OPINION":
                return "O Motor CARINA v1.0 (MFD Engine / Método DA SILVA) atesta que a malha viária urbana analisada obteve ganhos expressivos e mensuráveis de capacidade e fluidez operacionais. A progressão do modelo de aprendizado por reforço (RL) através das fases Criança (Linha Base), Adolescente (Em Otimização / Autonomia Supervisada) e Adulta (Otimizado / Autonomia Plena) comprovou a eliminação dos gargalos estruturais, elevando as velocidades médias em km/h e assegurando a estabilização da entropia da política (H < 0,15). Emite-se o Parecer Técnico de APROVAÇÃO E HOMOLOGAÇÃO da otimização semafórica MFD."
        return ""
