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

# File: src/mfd/mfd_report_generator.py
# Author: Gabriel Moraes
# Date: August 9, 2026

import logging
from typing import Dict, Any

from mfd.mfd_data_normalizer import MFDDataNormalizer
from mfd.mfd_plotter import MFDPlotter
from mfd.mfd_section_builder import MFDSectionBuilder
from mfd.mfd_neural_proofreader import MFDNeuralProofreader
from mfd.mfd_subprocess_fallback import MFDSubprocessFallback
from blocks.report_post_processor import ReportPostProcessor

class MFDReportGenerator:
    """
    Responsibility (SRP & Facade Pattern): High-level Orchestrator Facade for MFD report generation.
    Coordinates data normalization, plotting, section building, neural proofreading, and final document assembly.
    """

    @staticmethod
    def generate_report(
        mfd_history_data: dict,
        scenario_results_dir: str = None,
        scenario_name: str = None,
        db_manager=None,
        ui_language: str = None,
        lang: str = None,
        transducer: Any = None
    ) -> Dict[str, Any]:
        """
        Orchestrates MFD optimization analysis report generation.

        :param mfd_history_data: Input MFD simulation history dictionary
        :param scenario_results_dir: Optional output directory path
        :param scenario_name: Optional scenario display name
        :param db_manager: Database manager reference
        :param ui_language: UI language code
        :param lang: Target language code
        :param transducer: Optional loaded SLM Transducer instance
        :return: Completed report result dictionary
        """
        lang = lang or ui_language or "pt_br"

        if not mfd_history_data or not mfd_history_data.get("history"):
            return {
                "status": "error",
                "message": "Dados de simulação MFD insuficientes ou incompletos para auditoria viária."
            }

        # 1. Normalize data and resolve statistics
        history = mfd_history_data.get("history", [])
        peak_prod = mfd_history_data.get("peak_production", 0.0)
        peak_accum = mfd_history_data.get("peak_accumulation", 0.0)

        from mfd.mfd_analyzer import MFDAnalyzer
        summary_stats = MFDAnalyzer.analyze(
            history, peak_prod, peak_accum,
            scenario_results_dir=scenario_results_dir,
            scenario_name=scenario_name,
            db_manager=db_manager
        )

        normalized_data = MFDDataNormalizer.normalize_mfd_data(mfd_history_data, summary_stats=summary_stats, lang=lang)
        stats = normalized_data.get("stats", {})
        stages_data = normalized_data.get("stages_data", {})
        impact_stats = normalized_data.get("impact_stats", {})

        # 2. Generate MFD fundamental diagram curve in Base64 format
        logging.info("[MFD_REPORT_GENERATOR] Generating Macroscopic Fundamental Diagram (MFD) plot base64...")
        img_base64 = MFDPlotter.generate_mfd_curve_base64(mfd_history_data, stages_data, scenario_name=scenario_name)

        # 3. Instantiate or resolve SLM Transducer
        if transducer is None:
            try:
                from slm.semantic_transducer import SemanticTransducer
                st = SemanticTransducer()
                st.load_resources()
                if getattr(st, "model", None) is not None:
                    transducer = st
                else:
                    transducer = None
            except Exception as transducer_err:
                logging.warning(f"[MFD_REPORT_GENERATOR] Could not load in-memory SemanticTransducer: {transducer_err}")
                transducer = None

        # 4. Build narrative sections (1 to 5) and ANEXO I audit sheets
        narrative_text, raw_exec_summary = MFDSectionBuilder.build_narrative_sections(normalized_data, transducer=transducer, lang=lang)
        anexo_content = MFDSectionBuilder.build_anexo_fichas(normalized_data, transducer=transducer, lang=lang)

        # 5. Execute 2nd pass neural proofreading pass on narrative text
        revised_narrative = MFDNeuralProofreader.proofread_narrative(
            narrative_text,
            raw_exec_summary=raw_exec_summary,
            transducer=transducer,
            lang=lang
        )

        # 6. Assemble Final Document with SIGNATURE_BLOCK tag, pagebreak, and ANEXO I
        final_report_text = (
            revised_narrative.strip() +
            "\n\n[SIGNATURE_BLOCK]\n\n<pagebreak>\n\n# ANEXO I – FICHAS DE AUDITORIA DE OTIMIZAÇÃO INDIVIDUALIZADA POR CRUZAMENTO\n\n" +
            anexo_content.strip() +
            "\n\n---\n**Fim do Laudo Técnico Oficial de Auditoria de Otimização Semafórica MFD – Ecossistema CARINA v1.0**\n"
        )
        final_report_text = ReportPostProcessor.enforce_semantic_consistency(final_report_text)

        logging.info(f"[MFD_REPORT_GENERATOR] Relatório de análise MFD compilado com sucesso ({len(final_report_text)} caracteres).")

        return {
            "status": "complete",
            "text_report": final_report_text,
            "image_base64": img_base64,
            "report_text": final_report_text,
            "chart_image_base64": img_base64,
            "docx_path": None,
            "stats": stats,
            "stages_data": stages_data,
            "impact_stats": impact_stats
        }

    @staticmethod
    def _try_subprocess_transducer(payload: Dict[str, Any], device: str = "auto", gpu_layers: str = "16") -> str:
        """Forwarding helper method to MFDSubprocessFallback for backward compatibility."""
        return MFDSubprocessFallback.try_subprocess_transducer(payload, device=device, gpu_layers=gpu_layers)
