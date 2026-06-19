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

# File: src/xai/report_pipeline.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import os
import sys
import json
import time
import re
import subprocess
import logging
from typing import Dict, Any

from agents.local_agent import LocalAgent
from utils.locale_manager_backend import LocaleManagerBackend
from utils.settings_manager import SettingsManager
from xai.captum_analyzer import CaptumAnalyzer
from xai.structured_report_builder import XaiStructuredReportBuilder

class ReportPipeline:
    """
    Responsibility: Take a reconstructed Agent, execute the Captum Math Analyzer,
    parse its findings, and pipe the mathematical data into the LLM Semantic Transducer.
    """
    def __init__(self, scenario_results_dir: str, reports_dir: str):
        self.scenario_results_dir = scenario_results_dir
        self.reports_dir = reports_dir
        self.locale_manager = LocaleManagerBackend()
        
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.transducer_script = os.path.join(project_root, 'src', 'xai', 'semantic_transducer.py')

    def generate_full_report(self, agent: LocalAgent, agent_id: str) -> Dict[str, Any]:
        """Runs Captum -> Parses Chart Data -> Runs Transducer in memory, returns encoded data."""
        
        # 1. Run Captum (The Math) in memory
        analyzer = CaptumAnalyzer(
            agent=agent,
            scenario_results_dir=self.scenario_results_dir,
            locale_manager=self.locale_manager,
            feature_glossary=None
        )
        
        captum_result = analyzer.generate_analysis_in_memory()
        if not captum_result:
            raise RuntimeError(f"Captum mathematical analysis failed for {agent_id}.")

        # 2. Extract Numbers from memory text report
        raw_attributions = self._parse_captum_text_report_content(captum_result['text_report'])
        
        final_report_text = ""
        if raw_attributions:
            # 3. Trigger Subprocess Compiler via stdin/stdout
            transducer_input = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "mode": "AUTO",
                "attributions": raw_attributions,
                "language": self.locale_manager.get_language()
            }
            
            try:
                logging.info(f"[ReportPipeline] Invoking Semantic Transducer LLM for {agent_id} in memory...")
                
                cmd = [sys.executable, self.transducer_script]
                proc = subprocess.run(
                    cmd,
                    input=json.dumps(transducer_input),
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                
                if proc.returncode == 0:
                    logging.info(f"[ReportPipeline] Transducer LLM compilation successful for {agent_id}.")
                    final_report_text = proc.stdout.strip()
                else:
                    logging.warning(f"[ReportPipeline] Transducer failed. STDERR: {proc.stderr}")
            except Exception as e:
                logging.error(f"[ReportPipeline] LLM Pipeline crashed: {e}")
        
        # If transducer report wasn't generated/failed, fall back to basic text report
        if not final_report_text:
            final_report_text = captum_result.get("text_report", "")
                
        return {
            "status": "complete",
            "image_base64": captum_result.get("image_base64"),
            "text_content": final_report_text
        }

    def _parse_captum_text_report_content(self, content: str) -> dict:
        """Helper to rip numbers from the basic auto-generated text report content."""
        attributions = {}
        try:
            # Use localized strings for the regex to match the generated file
            sensor_str = re.escape(self.locale_manager.get_string('xai_report.section_sensor', default="Sensor"))
            imp_str = re.escape(self.locale_manager.get_string('xai_report.section_importance', default="Importance"))
            
            pattern = re.compile(rf"{sensor_str}:\s+(.+?)\n.*?{imp_str}:.*?\((\d+\.\d+)\)", re.DOTALL)
            for name, value in pattern.findall(content):
                try: attributions[name.strip()] = float(value)
                except ValueError: continue
            return attributions
        except Exception as e:
            logging.error(f"[ReportPipeline] Failed to parse intermediate report content: {e}")
            return {}

    def _parse_captum_text_report(self, report_path: str) -> dict:
        """Helper to rip numbers from the basic auto-generated .txt file (legacy)."""
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self._parse_captum_text_report_content(content)
        except Exception as e:
            logging.error(f"[ReportPipeline] Failed to read report file: {e}")
            return {}
