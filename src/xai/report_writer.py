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

# File: src/xai/report_writer.py
# Author: Gabriel Moraes
# Date: June 19, 2026

from datetime import datetime
from typing import List, Dict, Any
from utils.locale_manager_backend import LocaleManagerBackend

class ReportWriter:
    """
    Responsibility: Format aggregated feature importance information 
    and save as a structured text report.
    """
    def __init__(self, agent_id: str, locale_manager: LocaleManagerBackend) -> None:
        self.agent_id = agent_id
        self.locale_manager = locale_manager

    def write(self, sorted_analysis: List[Dict[str, Any]], output_path: str) -> None:
        data = self.write_to_string(sorted_analysis)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(data)

    def write_to_string(self, sorted_analysis: List[Dict[str, Any]]) -> str:
        lm = self.locale_manager
        lines = []
        lines.append("=" * 60)
        
        title = lm.get_string("xai_report.title", default="XAI Analysis Report - Agent {agent_id}", agent_id=self.agent_id)
        lines.append(title)
        
        subtitle = lm.get_string("xai_report.subtitle", default="Generated on: {timestamp}", timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        lines.append(subtitle)
        
        lines.append("=" * 60 + "\n")
        
        header_desc = lm.get_string("xai_report.header_description", default="This report presents the importance of each sensor (feature) for the agent's decision making, based on the Integrated Gradients method.")
        lines.append(header_desc + "\n")

        lbl_sensor = lm.get_string('xai_report.section_sensor', default="Sensor")
        lbl_importance = lm.get_string('xai_report.section_importance', default="Importance")
        lbl_desc = lm.get_string('xai_report.section_description', default="Description")

        for item in sorted_analysis:
            bar_length = 20
            filled_length = int(item['normalized_importance'] * bar_length)
            bar = '█' * filled_length + '─' * (bar_length - filled_length)
            
            lines.append(f"● {lbl_sensor}: {item['name']}")
            lines.append(f"  {lbl_importance}: {bar} ({item['importance']:.4f})")
            lines.append(f"  {lbl_desc}: {item['description']}")
            lines.append("-" * 60)
            
        return "\n".join(lines)
