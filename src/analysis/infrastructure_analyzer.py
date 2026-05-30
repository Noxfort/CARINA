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

# File: src/analysis/infrastructure_analyzer.py (V2 — DB-based Historical Analysis)
# Author: Gabriel Moraes
# Date: April 22, 2026

import logging
import configparser
from datetime import datetime
import sys
import os
from typing import TYPE_CHECKING

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from analysis.warrant_evaluator import WarrantEvaluator
from analysis.report_generator import ReportGenerator

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class InfrastructureAnalyzer:
    """
    Orchestrates the analysis of traffic data using the WarrantEvaluator V2.
    
    Now operates on historical data from the database instead of accumulated
    simulation data. The data arrives pre-grouped by junction with primary
    and secondary edge sample lists.
    """
    def __init__(self, settings: configparser.ConfigParser, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        self.analysis_params = {}
        self._load_analysis_parameters()
        self.scenario_name = lm.get_string("infra_analyzer.unknown_scenario")
        logging.info(lm.get_string("infra_analyzer.analyzer_created"))

    def _load_analysis_parameters(self):
        """
        Defines traffic engineering analysis thresholds as internal constants.
        These are standardized values based on MUTCD warrant criteria and
        fundamental traffic engineering principles.
        """
        self.analysis_params = {
            'min_volume_primary': 500,         # vph — MUTCD Warrant 1 threshold
            'min_volume_secondary': 150,       # vph — MUTCD Warrant 1 minor street
            'unacceptable_delay': 90.0,        # seconds — Warrant 2 delay threshold
            'max_queue_p95': 15,               # vehicles — P95 queue limit
            'saturation_critical': 0.85,       # X ratio — V/C collapse threshold
            'ideal_flow_per_lane': 1800,       # vph/lane — HCM ideal saturated flow
            'conflict_threshold': 10,          # events — Warrant 4 safety threshold
            'removal_threshold_percent': 60.0, # % — volume below which removal is recommended
            'change_threshold_percent': 5.0    # % — significant change detection
        }

    def analyze_collected_data(self, collected_data: dict, last_analysis_cache: dict, scenario_name: str, true_traffic_light_ids: list) -> dict:
        """
        Orchestrates the analysis pipeline.
        
        Args:
            collected_data: Dict of {junction_id: junction_data} where junction_data
                            contains 'primary_edges' and 'secondary_edges' with sample lists.
            last_analysis_cache: Previous analysis results for change detection.
            scenario_name: Name of the current scenario.
            true_traffic_light_ids: List of junction IDs that currently have traffic lights.
            
        Returns:
            Dict with report_content, significant_change, summary, new_cache_data, analysis_results.
        """
        self.scenario_name = scenario_name
        lm = self.locale_manager
        
        evaluator = WarrantEvaluator(self.analysis_params, true_traffic_light_ids, lm)
        
        analysis_results = {}
        for j_id, j_data in collected_data.items():
            result = evaluator.evaluate(j_id, j_data)
            if result:
                analysis_results[j_id] = result
        
        last_metrics = last_analysis_cache.get("junction_metrics", {})
        significant_change, summary = self._compare_with_cache(collected_data, last_metrics)
        
        report_generator = ReportGenerator(analysis_results, self.analysis_params, self.scenario_name, lm)
        report_content = report_generator.generate_txt_report()
        
        new_cache_data = {
            "last_analysis_timestamp": datetime.now().isoformat(),
            "analysis_parameters": self.analysis_params,
            "junction_metrics": collected_data
        }

        return {
            "report_content": report_content,
            "significant_change": significant_change,
            "summary": summary,
            "new_cache_data": new_cache_data,
            "analysis_results": analysis_results
        }

    def _compare_with_cache(self, current_metrics: dict, last_metrics: dict) -> tuple[bool, str]:
        """Compares current metrics with previous ones to detect changes."""
        lm = self.locale_manager
        if not last_metrics:
            return True, lm.get_string("infra_analyzer.summary_first_run")

        change_threshold = self.analysis_params.get('change_threshold_percent', 5.0)
        changed_junctions = []

        for j_id, new_data in current_metrics.items():
            if j_id not in last_metrics:
                changed_junctions.append(lm.get_string("infra_analyzer.change_new_junction", id=j_id))
                continue

        if changed_junctions:
            changes_str = ', '.join(changed_junctions)
            return True, lm.get_string("infra_analyzer.summary_changes_detected", changes=changes_str)
        
        return False, lm.get_string("infra_analyzer.summary_no_changes")