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

# File: src/sas/analyzer_engine.py (V4 — Pure In-Memory Stateless Architecture)
# Author: Gabriel Moraes
# Date: July 03, 2026

import logging
import os
import gc
import json
import configparser
from multiprocessing import Queue
import sys
from typing import TYPE_CHECKING

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from analysis.infrastructure_analyzer import InfrastructureAnalyzer
from rendering.static_map_renderer import StaticMapRenderer

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class AnalyzerEngine:
    """Orchestrates infrastructure analysis statelessly via in-memory IPC queue."""

    def __init__(self, settings: configparser.ConfigParser, db_data_queue: Queue, locale_manager: 'LocaleManagerBackend', sas_result_queue: Queue = None):
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager

        self.analyzer = InfrastructureAnalyzer(self.settings, self.locale_manager)
        self.map_renderer = StaticMapRenderer(self.locale_manager)
        self.db_data_queue = db_data_queue
        self.sas_result_queue = sas_result_queue

        self.scenario_dir = None

        logging.info(lm.get_string("sas_engine.init.engine_created"))

    def run_analysis(self, accumulated_data: dict, sim_duration: float, scenario_name: str,
                     net_file_path: str, run_id: int, calibration_data_points: list = None,
                     db_manager=None):
        """
        Runs the full analysis pipeline.
        
        If db_manager is provided, uses historical data from the database
        (V2 flow). Otherwise falls back to the legacy accumulated_data flow.
        """
        lm = self.locale_manager

        if db_manager is None:
            try:
                from database.database_manager import DatabaseManager
                db_manager = DatabaseManager(self.locale_manager)
            except Exception as e:
                logging.error(f"[ANALYZER_ENGINE] Failed to initialize DatabaseManager: {e}")

        from src.utils.paths import get_base_output_dir
        self.scenario_dir = os.path.join(get_base_output_dir(), "results", scenario_name)
        os.makedirs(self.scenario_dir, exist_ok=True)

        if sim_duration <= 0 or not net_file_path:
            logging.warning(lm.get_string("sas_engine.run.analysis_skipped_no_data"))
            err_res = {"status": "error", "message": lm.get_string("sas_engine.run.analysis_skipped_no_data")}
            if self.sas_result_queue is not None:
                self.sas_result_queue.put(err_res)
            return

        # Check PostgreSQL/DB minimum data time range requirement
        UNIT_TO_SECONDS = {
            'days': 86400,
            'weeks': 604800,
            'months': 2592000,
            'years': 31536000,
        }
        required_seconds = 7 * 86400  # Default 7 days
        try:
            if 'ANALYSIS_SCHEDULE' in self.settings:
                section = self.settings['ANALYSIS_SCHEDULE']
                value = section.getint('analysis_interval_value', 7)
                unit = section.get('analysis_interval_unit', 'days').strip().lower()
                required_seconds = max(value, 1) * UNIT_TO_SECONDS.get(unit, 86400)
        except Exception as e:
            logging.warning(f"[ANALYZER_ENGINE] Could not read analysis frequency from settings: {e}")

        db_time_range = 0.0
        if db_manager is not None:
            db_time_range = db_manager.get_fluid_dynamics_time_range()
            logging.info(f"[ANALYZER_ENGINE] Time span of traffic data in DB: {db_time_range:.1f}s (configured: {required_seconds:.1f}s)")
            
            if db_time_range <= 0 and not accumulated_data:
                err_msg = "Nenhum dado de tráfego disponível no banco de dados nem na sessão ativa."
                logging.warning(f"[ANALYZER_ENGINE] {err_msg}")
                err_res = {"status": "error", "message": err_msg}
                if self.sas_result_queue is not None:
                    self.sas_result_queue.put(err_res)
                return

        from sas.analyzer_data_processor import AnalyzerDataProcessor
        processor = AnalyzerDataProcessor(self.locale_manager)

        # === V2: DB-based flow vs Legacy fallback ===
        if db_manager is not None and db_time_range > 0:
            limit_sec = min(required_seconds, db_time_range)
            processed_data, true_traffic_light_ids = processor.process_historical_data(
                db_manager, net_file_path, limit_seconds=limit_sec
            )
        else:
            processed_data, true_traffic_light_ids = processor.process_accumulated_data(
                accumulated_data, sim_duration, net_file_path
            )

        if not processed_data:
            logging.warning("[ANALYZER_ENGINE] No processed data available for analysis.")
            err_res = {"status": "error", "message": "Nenhum dado de tráfego processado disponível para a análise."}
            if self.sas_result_queue is not None:
                self.sas_result_queue.put(err_res)
            del processor
            return

        # Load previous SAS analysis cache snapshot if present for change detection
        last_analysis_path = os.path.join(self.scenario_dir, "sas_last_analysis.json") if self.scenario_dir else None
        last_analysis_cache = {}
        has_previous_report = False

        if db_manager is not None:
            try:
                last_analysis_cache = db_manager.get_sas_analysis_cache(scenario_name)
                if last_analysis_cache:
                    has_previous_report = True
            except Exception as e:
                logging.warning(f"[ANALYZER_ENGINE] Falha ao carregar cache do banco de dados: {e}")

        # Fallback to local JSON file if cache was not loaded from DB
        if not last_analysis_cache and last_analysis_path and os.path.exists(last_analysis_path):
            try:
                with open(last_analysis_path, "r", encoding="utf-8") as f:
                    last_analysis_cache = json.load(f)
                has_previous_report = True
            except Exception as e:
                logging.warning(f"[ANALYZER_ENGINE] Falha ao carregar cache do relatório anterior em arquivo: {e}")

        # Run fresh stateless analysis for current data
        analysis_result = self.analyzer.analyze_collected_data(
            collected_data=processed_data,
            last_analysis_cache=last_analysis_cache,
            scenario_name=scenario_name,
            true_traffic_light_ids=true_traffic_light_ids
        )

        del processor
        del processed_data
        
        # Save snapshot of current analysis cache for future comparisons (DB primary + file backup)
        if "new_cache_data" in analysis_result:
            new_cache = analysis_result["new_cache_data"]
            if db_manager is not None:
                try:
                    db_manager.save_sas_analysis_cache(scenario_name, new_cache)
                except Exception as e:
                    logging.error(f"[ANALYZER_ENGINE] Falha ao salvar cache do relatório atual no banco: {e}")

            if last_analysis_path:
                try:
                    with open(last_analysis_path, "w", encoding="utf-8") as f:
                        json.dump(new_cache, f, indent=4)
                except Exception as e:
                    logging.error(f"[ANALYZER_ENGINE] Falha ao salvar cache do relatório atual em arquivo: {e}")

        if "analysis_results" in analysis_result and analysis_result["analysis_results"]:
            for j_res in analysis_result["analysis_results"].values():
                if "warrant_details" in j_res:
                    del j_res["warrant_details"]

        gc.collect()

        analysis_result["scenario_dir"] = self.scenario_dir

        try:
            log_payload = { "run_id": run_id, "summary": analysis_result.get("summary", "N/A"), "report_content": analysis_result.get("report_content", "") }
            data_packet = {"type": "log_report", "payload": log_payload}
            self.db_data_queue.put(data_packet)
            logging.info(lm.get_string("sas_engine.run.report_sent_to_db"))
        except Exception as e:
            logging.error(lm.get_string("sas_engine.run.db_queue_error", error=e))

        if "analysis_results" in analysis_result and analysis_result["analysis_results"]:
            self._generate_planning_map(analysis_result["analysis_results"], net_file_path)
            gc.collect()
            
            # Gerar o relatório profissional com a SLM do zero para os dados atuais
            try:
                from sas.report_generator import ReportGenerator
                report_gen = ReportGenerator(self.locale_manager)
                significant_change = analysis_result.get("significant_change", False)

                time_window_str = ""
                if db_manager is not None and hasattr(db_manager, "get_fluid_dynamics_min_max_timestamps"):
                    try:
                        min_dt, max_dt = db_manager.get_fluid_dynamics_min_max_timestamps(limit_seconds=limit_sec)
                        if min_dt and max_dt:
                            dur_min = round((max_dt - min_dt).total_seconds() / 60.0, 1)
                            time_window_str = f"De {min_dt.strftime('%d/%m/%Y %H:%M:%S')} até {max_dt.strftime('%d/%m/%Y %H:%M:%S')} (Duração: {dur_min:.1f} min)"
                    except Exception as ex_tw:
                        logging.warning(f"[ANALYZER_ENGINE] Could not fetch collection time window timestamps: {ex_tw}")
                
                docx_path, generated_text = report_gen.generate_docx_report(
                    analysis_results=analysis_result["analysis_results"],
                    scenario_dir=self.scenario_dir,
                    net_file_path=net_file_path,
                    has_significant_change=significant_change,
                    has_last_report=has_previous_report,
                    time_window_str=time_window_str
                )
                if generated_text:
                    analysis_result["report_content"] = generated_text
            except Exception as e:
                logging.error(f"[ANALYZER_ENGINE] Falha ao invocar o ReportGenerator para o relatório: {e}", exc_info=True)

        pruned_results = {}
        if "analysis_results" in analysis_result and analysis_result["analysis_results"]:
            for j_id, j_res in analysis_result["analysis_results"].items():
                pruned_results[j_id] = {
                    "recommendation": j_res.get("recommendation")
                }

        import time
        ui_payload = {
            "status": "success",
            "timestamp": time.time(),
            "report_content": analysis_result.get("report_content"),
            "scenario_dir": analysis_result.get("scenario_dir"),
            "significant_change": analysis_result.get("significant_change"),
            "analysis_results": pruned_results
        }

        # Envia pela fila IPC 100% em memória
        if self.sas_result_queue is not None:
            try:
                self.sas_result_queue.put(ui_payload)
                logging.info("[ANALYZER_ENGINE] Relatório de análise enviado com sucesso para a fila IPC da UI.")
            except Exception as e:
                logging.error(f"[ANALYZER_ENGINE] Falha ao enviar relatório pela fila IPC: {e}")

        if calibration_data_points:
            from sas.heatmap_calibrator import HeatmapCalibrator
            calibrator = HeatmapCalibrator()
            if calibrator.is_available():
                new_weights = calibrator.calibrate(calibration_data_points)
                if new_weights and self.scenario_dir:
                    calibrator.save_live_weights(self.scenario_dir, new_weights)

        logging.info(lm.get_string("sas_engine.run.analysis_complete"))

    def _generate_planning_map(self, analysis_results: dict, net_file_path: str):
        lm = self.locale_manager
        if not self.scenario_dir or not os.path.exists(self.scenario_dir):
            logging.error("[ANALYZER_ENGINE] Diretório do cenário inválido. Não é possível gerar mapa de planejamento.")
            return

        logging.info(lm.get_string("sas_engine.map.generating"))
        
        icon_requests = {}
        for j_id, r in analysis_results.items():
            rec_str = r.get('recommendation', '').lower()
            if "adicionar" in rec_str or "add" in rec_str:
                icon_requests[j_id] = "add"
            elif "remover" in rec_str or "remove" in rec_str:
                icon_requests[j_id] = "remove"
            elif "não sinalizado" in rec_str or "no_signal" in rec_str or "unsignalized" in rec_str:
                icon_requests[j_id] = "no_signal"
            else:
                icon_requests[j_id] = "existing"

        if net_file_path:
            self.map_renderer.create_map_with_icons(
                net_file_path=net_file_path,
                scenario_results_dir=self.scenario_dir,
                icon_requests=icon_requests,
                output_filename="map_planning.png"
            )
        else:
             logging.warning("[ANALYZER_ENGINE] Caminho do net_file não disponível. Mapa de planejamento não gerado.")