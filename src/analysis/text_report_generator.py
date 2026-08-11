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

# File: src/analysis/text_report_generator.py (V2 — Traffic Engineering Metrics)
# Author: Gabriel Moraes
# Date: July 25, 2026

import sys
import os
from typing import TYPE_CHECKING, Dict, Any

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from analysis.text_report_formatter import TextReportFormatter

class TextReportGenerator:
    """Formats analysis results into a professional text report."""

    def __init__(self, analysis_results: Dict[str, Any], analysis_params: Dict[str, Any], scenario_name: str, locale_manager: 'LocaleManagerBackend'):
        self.results = analysis_results
        self.params = analysis_params
        self.scenario_name = scenario_name
        self.locale_manager = locale_manager

    def generate_txt_report(self) -> str:
        """Delegates the complete report formatting to TextReportFormatter."""
        return TextReportFormatter.format_txt_report(
            results=self.results,
            params=self.params,
            scenario_name=self.scenario_name,
            locale_manager=self.locale_manager
        )