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

# File: src/xai/chart_renderer.py
# Author: Gabriel Moraes
# Date: June 19, 2026

import matplotlib.pyplot as plt
from typing import List, Dict, Any
from utils.locale_manager_backend import LocaleManagerBackend

# Ensure matplotlib does not try to open windows (headless mode)
plt.switch_backend('Agg')

class ChartRenderer:
    """
    Responsibility: Render feature importance charts using matplotlib and save as PNG.
    """
    def __init__(self, agent_id: str, locale_manager: LocaleManagerBackend) -> None:
        self.agent_id = agent_id
        self.locale_manager = locale_manager

    def render(self, sorted_analysis: List[Dict[str, Any]], output_path: str) -> None:
        data = self.render_to_bytes(sorted_analysis)
        with open(output_path, 'wb') as f:
            f.write(data)

    def render_to_bytes(self, sorted_analysis: List[Dict[str, Any]]) -> bytes:
        import io
        names = [x['name'] for x in sorted_analysis[:15]]
        values = [x['importance'] for x in sorted_analysis[:15]]
        
        plt.close('all')
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(names, values, color='skyblue')
        
        xlabel_text = self.locale_manager.get_string("xai_report.chart_xlabel", default="Importance")
        title_text = self.locale_manager.get_string("xai_report.chart_title", default="Feature Importance Analysis - Agent {agent_id}", agent_id=self.agent_id)
        
        ax.set_xlabel(xlabel_text)
        ax.set_title(title_text)
        ax.invert_yaxis()
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        return buf.getvalue()
