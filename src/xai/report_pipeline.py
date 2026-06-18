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
from xai.captum_analyzer import CaptumAnalyzer

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
        """Runs Captum -> Parses Chart Data -> Runs Transducer."""
        
        # 1. Run Captum (The Math)
        analyzer = CaptumAnalyzer(
            agent=agent,
            scenario_results_dir=self.scenario_results_dir,
            locale_manager=self.locale_manager,
            feature_glossary=None 
        )
        
        captum_result = analyzer.generate_analysis()
        if not captum_result:
            raise RuntimeError(f"Captum mathematical analysis failed for {agent_id}.")

        # 2. Extract Numbers
        raw_attributions = self._parse_captum_text_report(captum_result['text_path'])
        
        if raw_attributions:
            # 3. Trigger Subprocess Compiler
            transducer_input = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "mode": "AUTO",
                "attributions": raw_attributions,
                "language": self.locale_manager.get_language()
            }
            
            input_json_path = os.path.join(self.reports_dir, f"transducer_input_{agent_id}.json")
            final_report_path = os.path.join(self.reports_dir, f"laudo_tecnico_{agent_id}.txt")
            
            try:
                with open(input_json_path, 'w', encoding='utf-8') as f:
                    json.dump(transducer_input, f, indent=4)
                
                logging.info(f"[ReportPipeline] Invoking Semantic Transducer LLM for {agent_id}...")
                
                # Build command without GPU arguments to force exclusive use of CPU
                cmd = [sys.executable, self.transducer_script, "--input", input_json_path, "--output", final_report_path]
                
                proc = subprocess.run(cmd, capture_output=True, text=True)
                
                if proc.returncode == 0 and os.path.exists(final_report_path):
                    logging.info(f"[ReportPipeline] Transducer LLM compilation successful for {agent_id}.")
                    # Override basic file with the rich translated output
                    captum_result['text_path'] = final_report_path
                else:
                    logging.warning(f"[ReportPipeline] Transducer failed. STDERR: {proc.stderr}")
            except Exception as e:
                logging.error(f"[ReportPipeline] LLM Pipeline crashed: {e}")

        # 4. Final Data
        return {
            "status": "complete", 
            "image_path": captum_result.get("image_path"),
            "text_path": captum_result.get("text_path")
        }

    def _parse_captum_text_report(self, report_path: str) -> dict:
        """Helper to rip numbers from the basic auto-generated .txt file."""
        attributions = {}
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Use localized strings for the regex to match the generated file
            sensor_str = re.escape(self.locale_manager.get_string('xai_report.section_sensor', default="Sensor"))
            imp_str = re.escape(self.locale_manager.get_string('xai_report.section_importance', default="Importance"))
            
            pattern = re.compile(rf"{sensor_str}:\s+(.+?)\n.*?{imp_str}:.*?\((\d+\.\d+)\)", re.DOTALL)
            for name, value in pattern.findall(content):
                try: attributions[name.strip()] = float(value)
                except ValueError: continue
            return attributions
        except Exception as e:
            logging.error(f"[ReportPipeline] Failed to parse intermediate report: {e}")
            return {}
