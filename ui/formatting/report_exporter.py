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

# File: ui/formatting/report_exporter.py
# Author: Gabriel Moraes
# Date: 2026-07-01

import os
import base64
import tempfile
from typing import Any
import flet as ft
from ui.handlers.locale_manager import LocaleManager
from blocks.structured_report_builder import StructuredReportBuilder
from src.utils.settings_manager import SettingsManager

class ReportExporter:
    """
    Service handler that orchestrates configuration fetching, temporary image writing,
    and invocation of StructuredReportBuilder to export DOCX reports.
    """
    @staticmethod
    def export_report(
        page: ft.Page,
        locale_manager: LocaleManager,
        save_path: str,
        image_base64: str,
        text_content: str,
        results_dir: str,
        mode: str,  # "XAI", "MFD", or "PLANNING"
        agent_id: str = None
    ) -> bool:
        if not save_path.lower().endswith(".docx"):
            save_path += ".docx"

        tmp_img_path = None
        try:
            # Fallback search if image_base64 is empty
            if (not image_base64 or image_base64.strip() == "") and results_dir:
                if mode == "PLANNING":
                    possible_paths = [
                        os.path.join(results_dir, "map_planning.png"),
                        os.path.join(results_dir, "maps", "map_planning.png")
                    ]
                elif mode == "MFD":
                    possible_paths = [
                        os.path.join(results_dir, "mfd_curve.png"),
                        os.path.join(results_dir, "plots", "mfd_curve.png")
                    ]
                else:
                    possible_paths = [
                        os.path.join(results_dir, "xai_importance.png"),
                        os.path.join(results_dir, "plots", "xai_importance.png")
                    ]
                for p in possible_paths:
                    if os.path.exists(p) and os.path.getsize(p) > 0:
                        try:
                            with open(p, "rb") as img_f:
                                image_base64 = base64.b64encode(img_f.read()).decode("utf-8")
                            break
                        except Exception as e:
                            logging.warning(f"[REPORT_EXPORTER] Failed to read fallback image {p}: {e}")

            # Create temporary file for chart image if base64 is available
            if image_base64 and image_base64.strip() != "":
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                    tmp_img.write(base64.b64decode(image_base64))
                    tmp_img_path = tmp_img.name

            settings = SettingsManager().load_settings()

            def get_cfg(key: str, fallback_key: str, json_key: str, default_val: str) -> str:
                val = settings.get(key) or settings.get(fallback_key)
                if val is not None and str(val).strip() != "":
                    return str(val)
                return locale_manager.get_string(f"xai_report.report_defaults.{json_key}", default=default_val)

            if mode == "XAI":
                title_key = "report_title"
                fallback_title_key = "xai_report_title"
                json_title_key = "title"
                default_title = "LAUDO TÉCNICO DE EXPLICABILIDADE DE IA (XAI)"
            elif mode == "MFD":
                title_key = "report_title_mfd"
                fallback_title_key = "xai_report_title_mfd"
                json_title_key = "title_mfd"
                default_title = "LAUDO TÉCNICO DE DESEMPENHO E OTIMIZAÇÃO MFD"
            else:
                title_key = "report_title_planning"
                fallback_title_key = "planning_report_title"
                json_title_key = "title_planning"
                default_title = "LAUDO DESCRITIVO DE TRÁFEGO E INFRAESTRUTURA"

            config = {
                "logo_path": settings.get("report_logo_path") or settings.get("xai_logo_path"),
                "secretary_name": get_cfg("report_secretary_name", "xai_secretary_name", "secretary_name", "Dr. Gabriel Moraes"),
                "secretary_title": get_cfg("report_secretary_title", "xai_secretary_title", "secretary_title", "Secretário de Mobilidade e Trânsito"),
                "agency_name": get_cfg("report_agency_name", "xai_agency_name", "agency_name", "Prefeitura Municipal / Secretaria de Trânsito"),
                "department_name": get_cfg("report_department_name", "xai_department_name", "department_name", "Departamento de Mobilidade Inteligente"),
                "ordinance_enabled": settings.get("report_ordinance_enabled"),
                "ordinance_number": settings.get("report_ordinance_number"),
                "city": settings.get("report_city"),
                "state_uf": settings.get("report_state_uf"),
                "title": get_cfg(title_key, fallback_title_key, json_title_key, default_title),
                "font_name": get_cfg("report_font_name", "xai_font_name", "font_name", "Arial"),
                "font_size": float(get_cfg("report_font_size", "xai_font_size", "font_size", "11")),
                "margin_top": float(get_cfg("report_margin_top", "xai_margin_top", "margin_top", "3.0")),
                "margin_bottom": float(get_cfg("report_margin_bottom", "xai_margin_bottom", "margin_bottom", "2.0")),
                "margin_left": float(get_cfg("report_margin_left", "xai_margin_left", "margin_left", "3.0")),
                "margin_right": float(get_cfg("report_margin_right", "xai_margin_right", "margin_right", "2.0")),
                "line_spacing": float(get_cfg("report_line_spacing", "xai_line_spacing", "line_spacing", "1.15")),
                "alignment": get_cfg("report_alignment", "xai_alignment", "alignment", "justify"),
                "locale_manager": locale_manager,
                "mode": mode
            }

            if mode == "PLANNING":
                config["metadata_title"] = locale_manager.get_string("structured_report.planning_metadata_title", default="1. IDENTIFICAÇÃO E AMBIENTE OPERACIONAL")
                config["chart_title"] = locale_manager.get_string("structured_report.planning_chart_title", default="2. MAPA DE PLANEJAMENTO TÁTICO")
                config["chart_caption"] = locale_manager.get_string("structured_report.planning_chart_caption", default="Figura 1 – Mapa com Recomendações Espaciais da Malha Viária.")
                config["content_fallback"] = locale_manager.get_string("structured_report.planning_content_fallback", default="Nenhum laudo analítico de planejamento disponível.")
                config["conformity_text"] = locale_manager.get_string("structured_report.planning_conformity_text", default="Este documento foi consolidado pelo motor analítico CARINA SAS com base nos warrants técnicos (MUTCD / CONTRAN). Ele atesta as recomendações de engenharia de tráfego para a malha.")
            elif mode == "MFD":
                config["metadata_title"] = locale_manager.get_string("structured_report.mfd_metadata_title", default="1. IDENTIFICAÇÃO E AMBIENTE OPERACIONAL")
                config["chart_title"] = locale_manager.get_string("structured_report.mfd_chart_title", default="3. VISUALIZAÇÃO DO DIAGRAMA FUNDAMENTAL MACROSCÓPICO (MFD)")
                config["chart_caption"] = locale_manager.get_string("structured_report.mfd_chart_caption", default="Figura 1 – Curva de otimização MFD exibindo produção versus acumulação da malha viária.")
                config["content_fallback"] = locale_manager.get_string("structured_report.mfd_content_fallback", default="Nenhum laudo analítico MFD disponível.")
                config["conformity_text"] = locale_manager.get_string("structured_report.mfd_conformity_text", default="Este laudo foi gerado de forma determinística pelo motor de otimização CARINA v1.0 (MFD Engine). Todos os cálculos foram executados por equações matemáticas auditáveis em Python e redigidos sob validação estrita de integridade técnico-gerencial.")

            block_order_str = get_cfg("report_block_order", "xai_block_order", "block_order", "header,title,metadata,chart,content,signature")
            block_order = [b.strip() for b in block_order_str.split(",") if b.strip()]

            # Clean pipe '|' residues from strings
            def clean_str(val: Any) -> str:
                if val is None:
                    return ""
                return str(val).replace("|", "").strip()

            config["agency_name"] = clean_str(config.get("agency_name"))
            config["secretary_name"] = clean_str(config.get("secretary_name"))
            config["secretary_title"] = clean_str(config.get("secretary_title"))
            config["department_name"] = clean_str(config.get("department_name"))

            raw_scenario = os.path.basename(results_dir or "")
            if not raw_scenario or any(k in raw_scenario.lower() for k in ["hft", "live", "session"]):
                scenario_clean = "Sessão de Operação em Tempo Real"
            else:
                scenario_clean = raw_scenario.replace("_", " ").title()

            from blocks.report_post_processor import ReportPostProcessor
            cleaned_text_content = ReportPostProcessor.enforce_semantic_consistency(text_content) if text_content else ""

            engine_str = "CARINA v1.0 (MFD Engine)" if mode == "MFD" else ("CARINA v1.0 (SAS Engine)" if mode == "PLANNING" else "CARINA v1.0 (XAI Engine)")

            context = {
                "scenario": clean_str(scenario_clean),
                "engine_version": engine_str,
                "image_path": tmp_img_path,
                "text_content": cleaned_text_content,
                "results_dir": results_dir
            }
            if agent_id is not None:
                context["agent_id"] = clean_str(agent_id)

            if mode == "PLANNING":
                lbl_scenario = locale_manager.get_string("structured_report.planning_label_scenario", default="Cenário de Operação:")
                lbl_engine = locale_manager.get_string("structured_report.planning_label_engine", default="Motor Analítico SAS:")
                context["metadata_rows"] = [
                    (clean_str(lbl_scenario), clean_str(context.get("scenario", "N/A"))),
                    (clean_str(lbl_engine), clean_str(context.get("engine_version", "CARINA v1.0.0")))
                ]
            elif mode == "MFD":
                lbl_scenario = locale_manager.get_string("structured_report.mfd_label_scenario", default="Cenário de Operação:")
                lbl_engine = locale_manager.get_string("structured_report.mfd_label_engine", default="Motor Analítico:")
                context["metadata_rows"] = [
                    (clean_str(lbl_scenario), clean_str(context.get("scenario", "N/A"))),
                    (clean_str(lbl_engine), clean_str(context.get("engine_version", "CARINA v1.0 (MFD Engine)")))
                ]

            # Use StructuredReportBuilder modular block pipeline for ALL report modes (XAI, MFD, PLANNING)
            builder = StructuredReportBuilder(block_order=block_order)
            success = builder.generate_report(save_path, context, config)

            if success:
                success_msg = locale_manager.get_string("xai_viewer.export_success", default="Laudo exportado com sucesso para: {path}", path=save_path)
                page.snack_bar = ft.SnackBar(content=ft.Text(success_msg))
                page.snack_bar.open = True
            else:
                error_msg = locale_manager.get_string("xai_viewer.export_error", default="Erro ao gerar o laudo técnico.")
                page.snack_bar = ft.SnackBar(content=ft.Text(error_msg))
                page.snack_bar.open = True
            page.update()
            return success

        except Exception as ex:
            catch_msg = locale_manager.get_string("xai_viewer.export_catch_error", default="Erro ao exportar laudo: {error}", error=str(ex))
            page.snack_bar = ft.SnackBar(content=ft.Text(catch_msg))
            page.snack_bar.open = True
            page.update()
            return False
        finally:
            if tmp_img_path and os.path.exists(tmp_img_path):
                try:
                    os.remove(tmp_img_path)
                except:
                    pass
