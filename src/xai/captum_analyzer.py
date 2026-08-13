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

# File: src/xai/captum_analyzer.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import os
import torch
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from utils.locale_manager_backend import LocaleManagerBackend
from agents.local_agent import LocalAgent

# Import single responsibility classes from respective modular files
from xai.captum_model_wrapper import CaptumModelWrapper
from xai.captum_attribution_engine import CaptumAttributionEngine
from xai.feature_aggregator import FeatureAggregator
from xai.chart_renderer import ChartRenderer
from xai.report_writer import ReportWriter

class CaptumAnalyzer:
    """
    Orchestrator for XAI (Explainable AI) analysis.
    Coordinates mathematical attribution calculation, semantic grouping,
    chart rendering, and text report writing by invoking dedicated single-responsibility components.
    """
    def __init__(self, agent: LocalAgent, scenario_results_dir: str, locale_manager: Optional[LocaleManagerBackend] = None, feature_glossary: Optional[Any] = None, output_dir: Optional[str] = None) -> None:
        """
        Initializes the Captum Analyzer Orchestrator.
        Note: locale_manager is optional and defaults to LocaleManagerBackend() to preserve backward compatibility.
        """
        self.agent = agent
        self.locale_manager = locale_manager if locale_manager is not None else LocaleManagerBackend()
        
        # --- Memory and Sub-Component Orchestration ---
        self.device = torch.device("cpu")
        self.attribution_engine = CaptumAttributionEngine(self.agent, self.device)
        self.aggregator = FeatureAggregator(self.agent, self.locale_manager, feature_glossary)
        self.chart_renderer = ChartRenderer(self.agent.id, self.locale_manager)
        self.report_writer = ReportWriter(self.agent.id, self.locale_manager)
        
        # --- Output paths ---
        self.output_dir = output_dir if output_dir is not None else os.path.join(scenario_results_dir, "captum", "reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.output_path_png = os.path.join(self.output_dir, f"xai_report_{agent.id}_{timestamp}.png")
        self.output_path_txt = os.path.join(self.output_dir, f"xai_report_{agent.id}_{timestamp}.txt")

    def generate_analysis(self) -> Optional[Dict[str, str]]:
        original_mode_is_training = self.agent.policy_net.training
        
        try:
            self.agent.policy_net.eval()
            
            # 1. Compute Raw Importances using the attribution engine
            importances = self.attribution_engine.compute_importances()
            if importances is None:
                logging.warning(self.locale_manager.get_string("captum_analyzer.run.empty_memory_warning", default="Memory empty for agent {agent_id}", agent_id=self.agent.id))
                return None
            
            # 2. Group & Aggregate feature importances
            sorted_analysis = self.aggregator.aggregate(importances)
            
            # 3. Generate Chart (PNG)
            self.chart_renderer.render(sorted_analysis, self.output_path_png)

            # 4. Generate Text Report (TXT)
            self.report_writer.write(sorted_analysis, self.output_path_txt)
            
            logging.info(self.locale_manager.get_string("captum_analyzer.run.text_report_success", default="Text report saved to {path}", path=self.output_path_txt))

            return {
                "image_path": os.path.abspath(self.output_path_png),
                "text_path": os.path.abspath(self.output_path_txt)
            }

        except Exception as e:
            logging.error(self.locale_manager.get_string("captum_analyzer.run.analysis_error", default="Analysis failed: {error}", error=e), exc_info=True)
            return None
        finally:
            if original_mode_is_training: 
                self.agent.policy_net.train()

    def generate_analysis_in_memory(self) -> Optional[Dict[str, Any]]:
        """Runs the entire analysis pipeline completely in memory, avoiding disk writes."""
        original_mode_is_training = self.agent.policy_net.training
        
        try:
            self.agent.policy_net.eval()
            
            # 1. Compute Raw Importances using the attribution engine
            importances = self.attribution_engine.compute_importances()
            if importances is None:
                logging.warning(self.locale_manager.get_string("captum_analyzer.run.empty_memory_warning", default="Memory empty for agent {agent_id}", agent_id=self.agent.id))
                return {
                    "has_tensor_data": False,
                    "message": "Atenção: Ausência de dados de amostragem dos tensores de tráfego no buffer de memória.",
                    "image_base64": "",
                    "text_report": "Atenção: Não há dados de amostragem dos tensores de tráfego acumulados na memória do agente para realizar a análise pericial de explicabilidade matemática.",
                    "sorted_analysis": []
                }
            
            # 2. Group & Aggregate feature importances
            sorted_analysis = self.aggregator.aggregate(importances)
            
            # 3. Generate Chart (PNG) directly to bytes and encode to base64
            import base64
            img_bytes = self.chart_renderer.render_to_bytes(sorted_analysis)
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

            # 4. Generate Text Report (TXT) in memory
            raw_text = self.report_writer.write_to_string(sorted_analysis)

            return {
                "image_base64": img_base64,
                "text_report": raw_text,
                "sorted_analysis": sorted_analysis
            }

        except Exception as e:
            logging.error(self.locale_manager.get_string("captum_analyzer.run.analysis_error", default="Analysis failed: {error}", error=e), exc_info=True)
            return None
        finally:
            if original_mode_is_training: 
                self.agent.policy_net.train()