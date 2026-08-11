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

# File: src/sas/docx_report_assembler.py
# Author: Gabriel Moraes
# Date: July 21, 2026

import os
import logging
from datetime import datetime

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    logging.warning("[DOCX_ASSEMBLER] python-docx not installed. Reports cannot be generated in .docx format.")

from sas.report_template_provider import ReportTemplateProvider
from blocks.markdown_to_docx import render_markdown_to_docx

class DocxReportAssembler:
    """
    Handles the physical document formatting, styles, alignments, image embedding,
    and compilation of markdown report text into a professional .docx Word document.
    """
    
    @classmethod
    def assemble_docx_to_path(cls, target_path: str, scenario_dir: str, report_text: str, ui_language: str = "pt_br", mode: str = "MFD") -> str:
        """
        Compiles the report text into a Word document using the modular src/blocks/ pipeline
        and saves it directly to target_path. Returns target_path on success.
        """
        try:
            from blocks.structured_report_builder import StructuredReportBuilder
            from utils.settings_manager import SettingsManager

            lang_dict = ReportTemplateProvider.get_layout_translations(ui_language)

            # Load user formatting preferences from settings.ini via SettingsManager
            user_settings = {}
            try:
                user_settings = SettingsManager().load_settings()
            except Exception as e:
                logging.warning(f"[DOCX_ASSEMBLER] Failed to load user settings via SettingsManager: {e}")

            logo_path = user_settings.get("report_logo_path") or user_settings.get("xai_logo_path", "")
            secretary_name = user_settings.get("report_secretary_name") or user_settings.get("xai_secretary_name") or "Dr. Gabriel Moraes"
            secretary_title = user_settings.get("report_secretary_title") or user_settings.get("xai_secretary_title") or "Secretário de Mobilidade e Trânsito"
            agency_name = user_settings.get("report_agency_name") or user_settings.get("xai_agency_name") or "Prefeitura Municipal / Secretaria de Trânsito"
            department_name = user_settings.get("report_department_name") or user_settings.get("xai_department_name") or "Departamento de Mobilidade Inteligente"
            
            if mode == "MFD":
                report_title = "LAUDO TÉCNICO DE DESEMPENHO E OTIMIZAÇÃO MFD"
                engine_ver = "CARINA v1.0 (MFD Engine)"
                conf_txt = "Este laudo foi gerado de forma determinística pelo motor de otimização CARINA MFD. Ele atesta as métricas de performance macroscópica da rede de tráfego analisada."
            else:
                report_title = user_settings.get("report_title") or user_settings.get("xai_report_title") or lang_dict.get("main_title", "LAUDO TÉCNICO DE ENGENHARIA DE TRÁFEGO E AUDITORIA DE INFRAESTRUTURA")
                engine_ver = "CARINA v1.0 (Neuro-Symbolic)"
                conf_txt = "Este documento foi consolidado de forma determinística pelo motor Neuro-Simbólico CARINA XAI. Ele atesta as condições puras da leitura de topologia e do comportamento da rede neural."

            font_name = user_settings.get("report_font_name") or user_settings.get("xai_font_name") or "Arial"

            def _parse_float(val, default):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            font_size = _parse_float(user_settings.get("report_font_size") or user_settings.get("xai_font_size"), 11.0)
            margin_top = _parse_float(user_settings.get("report_margin_top") or user_settings.get("xai_margin_top"), 1.0)
            margin_bottom = _parse_float(user_settings.get("report_margin_bottom") or user_settings.get("xai_margin_bottom"), 1.0)
            margin_left = _parse_float(user_settings.get("report_margin_left") or user_settings.get("xai_margin_left"), 1.0)
            margin_right = _parse_float(user_settings.get("report_margin_right") or user_settings.get("xai_margin_right"), 1.0)
            line_spacing = _parse_float(user_settings.get("report_line_spacing") or user_settings.get("xai_line_spacing"), 1.15)
            alignment = user_settings.get("report_alignment") or user_settings.get("xai_alignment") or "justify"

            block_order_str = user_settings.get("report_block_order") or user_settings.get("xai_block_order") or "header,title,metadata,chart,content,signature"
            block_order = [b.strip() for b in block_order_str.split(",") if b.strip()]

            builder = StructuredReportBuilder(
                block_order=block_order
            )

            map_path = os.path.join(scenario_dir, "map_planning.png")
            if not os.path.exists(map_path):
                map_path = os.path.join(scenario_dir, "maps", "map_planning.png")

            raw_scenario = os.path.basename(scenario_dir)
            if not raw_scenario or any(k in raw_scenario.lower() for k in ["hft", "live", "session"]):
                scenario_name = "Sessão de Operação em Tempo Real"
            else:
                scenario_name = raw_scenario.replace("_", " ").title()

            context = {
                "agent_id": "CARINA AI Control Engine",
                "scenario": scenario_name,
                "engine_version": engine_ver,
                "text_content": report_text,
                "image_path": map_path,
                "results_dir": scenario_dir
            }

            config = {
                "mode": mode,
                "title": report_title,
                "logo_path": logo_path,
                "agency_name": agency_name,
                "department_name": department_name,
                "secretary_name": secretary_name,
                "secretary_title": secretary_title,
                "ordinance_enabled": user_settings.get("report_ordinance_enabled"),
                "ordinance_number": user_settings.get("report_ordinance_number"),
                "city": user_settings.get("report_city"),
                "state_uf": user_settings.get("report_state_uf"),
                "chart_title": lang_dict.get("section_1_title", "Mapa de Planejamento e Topologia Viária"),
                "chart_caption": "Figura 1: Representação gráfica da rede viária analisada e sinalização semafórica.",
                "content_title": lang_dict.get("section_2_title", "2. Detalhamento de Auditoria e Parecer Técnico"),
                "content_fallback": "Nenhum parecer técnico foi gerado.",
                "conformity_text": conf_txt,
                "font_name": font_name,
                "font_size": font_size,
                "margin_top": margin_top,
                "margin_bottom": margin_bottom,
                "margin_left": margin_left,
                "margin_right": margin_right,
                "line_spacing": line_spacing,
                "alignment": alignment
            }

            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
            success = builder.generate_report(target_path, context, config)

            if not success:
                raise RuntimeError(f"Failed to generate structured DOCX report using blocks at {target_path}")

            logging.info(f"[DOCX_ASSEMBLER] DOCX report successfully generated using blocks pipeline at: {target_path}")
            return target_path

        except Exception as e:
            logging.error(f"[DOCX_ASSEMBLER] Error assembling .docx document to {target_path}: {e}", exc_info=True)
            raise e

    @staticmethod
    def assemble_docx(scenario_dir: str, report_text: str, ui_language: str) -> str:
        """
        Compiles the report text into a Word document and saves it in the scenario directory.
        Returns the absolute path of the generated .docx file.
        """
        docx_path = os.path.join(scenario_dir, "Laudo_Tecnico_Oficial.docx")
        return DocxReportAssembler.assemble_docx_to_path(docx_path, scenario_dir, report_text, ui_language)
