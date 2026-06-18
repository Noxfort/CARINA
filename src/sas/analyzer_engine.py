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

# File: src/sas/analyzer_engine.py (V2 — DB-based Historical Analysis)
# Author: Gabriel Moraes
# Date: April 22, 2026

import logging
import os
import json
import configparser
from collections import defaultdict
from multiprocessing import Queue
import sys
from typing import TYPE_CHECKING, List, Dict

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Imports that are *not* heavy or essential to begin with
from analysis.infrastructure_analyzer import InfrastructureAnalyzer
from rendering.static_map_renderer import StaticMapRenderer
from utils.network_topology_parser import NetworkTopologyParser

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# --- Check availability via direct import (works in frozen mode) ---
SKLEARN_AVAILABLE = False
try:
    import pandas  # noqa: F401
    import sklearn.linear_model  # noqa: F401
    SKLEARN_AVAILABLE = True
    logging.debug("[ANALYZER_ENGINE] Pandas e Scikit-learn detectados.")
except Exception as _e:
    import traceback as _tb
    logging.warning(f"[ANALYZER_ENGINE] Bibliotecas 'pandas' ou 'sklearn' não encontradas. "
                    f"Erro: {type(_e).__name__}: {_e}")
    logging.debug(f"[ANALYZER_ENGINE] Traceback completo:\n{_tb.format_exc()}")


class AnalyzerEngine:
    """Executes infrastructure analysis using historical database data."""

    def __init__(self, settings: configparser.ConfigParser, db_data_queue: Queue, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager

        self.analyzer = InfrastructureAnalyzer(self.settings, self.locale_manager)
        self.map_renderer = StaticMapRenderer(self.locale_manager)
        self.topology_parser = NetworkTopologyParser(self.locale_manager)
        self.db_data_queue = db_data_queue

        self.scenario_dir = None
        self.analysis_dir = None
        self.cache_path = None
        self.ui_status_path = None

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

        if sim_duration <= 0 or not net_file_path:
            logging.warning(lm.get_string("sas_engine.run.analysis_skipped_no_data"))
            return

        from src.utils.paths import get_base_output_dir
        self.scenario_dir = os.path.join(get_base_output_dir(), "results", scenario_name)
        self.analysis_dir = os.path.join(self.scenario_dir, "infrastructure_analysis")
        os.makedirs(self.analysis_dir, exist_ok=True)
        self.cache_path = os.path.join(self.analysis_dir, "analysis_cache.json")
        self.ui_status_path = os.path.join(self.analysis_dir, "analysis_status.json")

        # === V2: DB-based flow ===
        if db_manager is not None:
            processed_data, true_traffic_light_ids = self._process_historical_data(
                db_manager, net_file_path
            )
        else:
            # === Legacy fallback ===
            processed_data, true_traffic_light_ids = self._process_accumulated_data(
                accumulated_data, sim_duration, net_file_path
            )

        if not processed_data:
            logging.warning("[ANALYZER_ENGINE] No processed data available for analysis.")
            return

        last_analysis_cache = self._load_cache()

        analysis_result = self.analyzer.analyze_collected_data(
            collected_data=processed_data,
            last_analysis_cache=last_analysis_cache,
            scenario_name=scenario_name,
            true_traffic_light_ids=true_traffic_light_ids
        )

        try:
            log_payload = { "run_id": run_id, "summary": analysis_result.get("summary", "N/A"), "report_content": analysis_result.get("report_content", "") }
            data_packet = {"type": "log_report", "payload": log_payload}
            self.db_data_queue.put(data_packet)
            logging.info(lm.get_string("sas_engine.run.report_sent_to_db"))
        except Exception as e:
            logging.error(lm.get_string("sas_engine.run.db_queue_error", error=e))

        if "analysis_results" in analysis_result and analysis_result["analysis_results"]:
            self._generate_planning_map(analysis_result["analysis_results"], net_file_path)
            
            # NOVO: Gerar o relatório profissional em .docx com LLM (Temperature=0.0)
            try:
                from sas.report_generator import ReportGenerator
                report_gen = ReportGenerator(self.locale_manager)
                report_gen.generate_docx_report(
                    analysis_results=analysis_result["analysis_results"],
                    scenario_dir=self.scenario_dir,
                    net_file_path=net_file_path
                )
            except Exception as e:
                logging.error(f"[ANALYZER_ENGINE] Falha ao invocar o ReportGenerator para o .docx: {e}", exc_info=True)

        self._save_cache(analysis_result.get("new_cache_data", {}))
        self._notify_ui(analysis_result)

        # Only attempts to calibrate if SKLEARN_AVAILABLE is True AND there is data
        if SKLEARN_AVAILABLE and calibration_data_points:
            new_weights = self._calibrate_heatmap_weights(calibration_data_points)
            if new_weights:
                self._save_live_weights(new_weights)

        logging.info(lm.get_string("sas_engine.run.analysis_complete"))

    def _process_historical_data(self, db_manager, net_file_path: str) -> tuple[dict, list]:
        """
        Queries the database for historical traffic samples and groups them
        by junction (primary/secondary edges) using the network topology.
        
        This is the V2 data processing pipeline that replaces
        _process_accumulated_data for optimization analysis.
        """
        lm = self.locale_manager
        logging.info("[ANALYZER_ENGINE] Processing historical data from database...")

        # 1. Parse topology
        junction_types, junction_incoming_edges = self.topology_parser.build(net_file_path)
        if not junction_types or not junction_incoming_edges:
            logging.error(lm.get_string("sas_engine.topology.cannot_continue_error"))
            return {}, []

        true_traffic_light_ids = [j_id for j_id, j_type in junction_types.items() if j_type == 'traffic_light']

        # 2. Query all traffic samples from DB
        all_samples = db_manager.query_traffic_history()
        if not all_samples:
            logging.warning("[ANALYZER_ENGINE] No traffic samples found in database.")
            return {}, true_traffic_light_ids

        logging.info(f"[ANALYZER_ENGINE] Retrieved {len(all_samples)} traffic samples from database.")

        # 3. Index samples by edge_id for fast lookup
        samples_by_edge = defaultdict(list)
        for sample in all_samples:
            samples_by_edge[sample['edge_id']].append(sample)

        # 4. Group by junction: primary vs secondary edges
        processed_data = {}
        for j_id, incoming_edges in junction_incoming_edges.items():
            if not incoming_edges:
                continue

            # Sort incoming edges by number of lanes (most lanes = primary)
            sorted_edges = sorted(incoming_edges.items(), key=lambda item: item[1]['num_lanes'], reverse=True)
            max_lanes = sorted_edges[0][1]['num_lanes'] if sorted_edges else 0

            primary_edges = {}
            secondary_edges = {}

            for edge_id, edge_data in sorted_edges:
                edge_samples = samples_by_edge.get(edge_id, [])
                if not edge_samples:
                    continue

                # Enrich samples with topology data if not already present
                for s in edge_samples:
                    if s.get('edge_length') is None:
                        s['edge_length'] = edge_data.get('length', 0)
                    if s.get('num_lanes') is None:
                        s['num_lanes'] = edge_data.get('num_lanes', 1)
                    if s.get('speed_limit') is None:
                        s['speed_limit'] = edge_data.get('speed_limit', 13.89)

                if edge_data['num_lanes'] == max_lanes:
                    primary_edges[edge_id] = edge_samples
                else:
                    secondary_edges[edge_id] = edge_samples

            # Only include junctions that have data
            if primary_edges or secondary_edges:
                processed_data[j_id] = {
                    'primary_edges': primary_edges,
                    'secondary_edges': secondary_edges,
                    'conflict_events': 0,
                    'type': junction_types.get(j_id, 'unknown'),
                }

        logging.info(f"[ANALYZER_ENGINE] Processed {len(processed_data)} junctions from historical data.")
        return processed_data, true_traffic_light_ids

    def _process_accumulated_data(self, accumulated_data: dict, sim_duration: float, net_file_path: str) -> tuple[dict, list]:
        """Legacy data processing from simulation DataCollector."""
        lm = self.locale_manager
        logging.info(lm.get_string("sas_engine.run.processing_data"))

        junction_types, junction_incoming_edges = self.topology_parser.build(net_file_path)

        if not junction_types or not junction_incoming_edges:
            logging.error(lm.get_string("sas_engine.topology.cannot_continue_error"))
            return {}, []

        true_traffic_light_ids = [j_id for j_id, j_type in junction_types.items() if j_type == 'traffic_light']

        processed_data = {}
        sim_duration_hours = sim_duration / 3600.0 if sim_duration > 0 else 1.0

        for j_id, incoming_edges in junction_incoming_edges.items():
            if not incoming_edges: continue
            sorted_edges = sorted(incoming_edges.items(), key=lambda item: item[1]['num_lanes'], reverse=True)
            max_lanes = sorted_edges[0][1]['num_lanes'] if sorted_edges else 0
            primary_lanes, secondary_lanes = [], []
            for edge_id, edge_data in sorted_edges:
                if edge_data['num_lanes'] == max_lanes: primary_lanes.extend(edge_data['lanes'])
                else: secondary_lanes.extend(edge_data['lanes'])

            primary_vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in primary_lanes)
            secondary_vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in secondary_lanes)
            secondary_wait_time = sum(accumulated_data.get('total_waiting_time_per_lane', {}).get(lane, 0) for lane in secondary_lanes)

            vol_primary = int(primary_vehicles / sim_duration_hours)
            vol_secondary = int(secondary_vehicles / sim_duration_hours)
            avg_delay_secondary = (secondary_wait_time / secondary_vehicles) if secondary_vehicles > 0 else 0

            # Wrap legacy data into the V2 format for compatibility
            processed_data[j_id] = {
                'primary_edges': {},
                'secondary_edges': {},
                'conflict_events': accumulated_data.get('conflict_events_per_junction', {}).get(j_id, 0),
                'type': junction_types.get(j_id, 'unknown'),
                # Legacy fields (for backward compatibility with reports)
                "volume": vol_primary,
                "vol_secondary": vol_secondary,
                "avg_delay": avg_delay_secondary,
            }

        logging.info(lm.get_string("sas_engine.run.data_processed", count=len(processed_data)))
        return processed_data, true_traffic_light_ids

    def _calibrate_heatmap_weights(self, data_points: List[Dict]) -> Dict | None:
        try:
            import pandas as pd
            from sklearn.linear_model import LinearRegression
        except ImportError:
             logging.error("[ANALYZER_ENGINE] Falha ao importar pandas/sklearn DENTRO da calibração.")
             return None

        logging.info(f"[ANALYZER_ENGINE] Iniciando calibração do mapa de calor com {len(data_points)} pontos de dados.")
        if len(data_points) < 100:
            logging.warning(f"[ANALYZER_ENGINE] Dados insuficientes para calibração (< 100 pontos, temos {len(data_points)}). Abortando.")
            return None
        try:
            df = pd.DataFrame(data_points)
            df.replace([float('inf'), -float('inf')], float('nan'), inplace=True)
            df.dropna(inplace=True)

            if df.empty or len(df) < 2:
                logging.warning("[ANALYZER_ENGINE] Nenhum dado válido restante após a limpeza ou dados insuficientes. Abortando calibração.")
                return None

            features = ['occupancy', 'waiting_time', 'flow']
            target = 'bad_events'

            if not all(feat in df.columns for feat in features) or target not in df.columns:
                 logging.error(f"[ANALYZER_ENGINE] Colunas necessárias ({features + [target]}) não encontradas no DataFrame. Colunas presentes: {df.columns.tolist()}. Abortando calibração.")
                 return None

            X = df[features]
            y = df[target]

            if X.isnull().values.any() or y.isnull().values.any():
                 logging.warning("[ANALYZER_ENGINE] Dados NaN encontrados mesmo após dropna. Abortando calibração.")
                 return None
            if not pd.api.types.is_numeric_dtype(y):
                 logging.warning(f"[ANALYZER_ENGINE] Coluna target '{target}' não é numérica. Abortando calibração.")
                 return None
            if not all(pd.api.types.is_numeric_dtype(X[col]) for col in X.columns):
                 logging.warning(f"[ANALYZER_ENGINE] Uma ou mais colunas de features não são numéricas. Abortando calibração.")
                 return None

            model = LinearRegression(positive=False)
            model.fit(X, y)

            coef_occupancy = max(0.0, model.coef_[0])
            coef_waiting = max(0.0, model.coef_[1])
            coef_flow = model.coef_[2]

            total_abs_weight = abs(coef_occupancy) + abs(coef_waiting) + abs(coef_flow)
            if total_abs_weight > 1e-6:
                 norm_factor = 3.0 / total_abs_weight
                 coef_occupancy *= norm_factor
                 coef_waiting *= norm_factor
                 coef_flow *= norm_factor

            new_weights = {
                'weight_occupancy': round(coef_occupancy, 4),
                'weight_waiting_time': round(coef_waiting, 4),
                'weight_flow': round(-abs(coef_flow), 4)
            }

            logging.info(f"[ANALYZER_ENGINE] Calibração concluída. Novos pesos do mapa de calor: {new_weights}")
            return new_weights

        except Exception as e:
            logging.error(f"[ANALYZER_ENGINE] Erro durante a calibração do mapa de calor: {e}", exc_info=True)
            return None

    def _save_live_weights(self, weights: Dict):
        if not self.scenario_dir or not os.path.exists(self.scenario_dir):
            logging.error("[ANALYZER_ENGINE] Diretório do cenário não definido ou não existe. Não é possível salvar pesos.")
            return

        live_weights_path = os.path.join(self.scenario_dir, "heatmap_weights_live.json")
        try:
            with open(live_weights_path, "w", encoding="utf-8") as f:
                json.dump(weights, f, indent=4)
            logging.info(f"[ANALYZER_ENGINE] Pesos do mapa de calor ao vivo salvos em: {live_weights_path}")
        except IOError as e:
            logging.error(f"[ANALYZER_ENGINE] Falha ao salvar os pesos do mapa de calor ao vivo: {e}")

    def _generate_planning_map(self, analysis_results: dict, net_file_path: str):
        lm = self.locale_manager
        if not self.scenario_dir or not os.path.exists(self.scenario_dir):
            logging.error("[ANALYZER_ENGINE] Diretório do cenário inválido. Não é possível gerar mapa de planejamento.")
            return

        logging.info(lm.get_string("sas_engine.map.generating"))
        rec_add = lm.get_string("warrant_evaluator.rec_add")
        rec_remove = lm.get_string("warrant_evaluator.rec_remove")
        icon_requests = {
            j_id: "add" if rec_add in r.get('recommendation', '') else "remove" if rec_remove in r.get('recommendation', '') else "existing"
            for j_id, r in analysis_results.items()
        }
        if net_file_path:
            self.map_renderer.create_map_with_icons(
                net_file_path=net_file_path,
                scenario_results_dir=self.scenario_dir,
                icon_requests=icon_requests,
                output_filename="map_planning.png"
            )
        else:
             logging.warning("[ANALYZER_ENGINE] Caminho do net_file não disponível. Mapa de planejamento não gerado.")


    def _load_cache(self) -> dict:
        if not self.cache_path or not os.path.exists(self.cache_path): return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f: return json.load(f)
        except (json.JSONDecodeError, IOError): return {}

    def _save_cache(self, cache_data: dict):
        if not cache_data or not self.cache_path: return
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f: json.dump(cache_data, f, indent=4)
        except IOError: logging.error(self.locale_manager.get_string("sas_engine.cache.save_error"))

    def _notify_ui(self, analysis_result: dict):
        if not analysis_result or not analysis_result.get("analysis_results") or not self.ui_status_path: return
        try:
            os.makedirs(os.path.dirname(self.ui_status_path), exist_ok=True)
            with open(self.ui_status_path, "w", encoding="utf-8") as f: json.dump(analysis_result, f, indent=4)
        except IOError: logging.error(self.locale_manager.get_string("sas_engine.ui.status_save_error"))