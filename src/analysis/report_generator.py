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

# File: src/analysis/report_generator.py (V2 — Traffic Engineering Metrics)
# Author: Gabriel Moraes
# Date: April 22, 2026

from datetime import datetime
import sys
import os
from typing import TYPE_CHECKING

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class ReportGenerator:
    """Formats analysis results into a professional text report."""

    def __init__(self, analysis_results: dict, analysis_params: dict, scenario_name: str, locale_manager: 'LocaleManagerBackend'):
        self.results = analysis_results
        self.params = analysis_params
        self.scenario_name = scenario_name
        self.locale_manager = locale_manager

    def generate_txt_report(self) -> str:
        """Generates the complete formatted report as a string."""
        lm = self.locale_manager
        analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        add_count = len([r for r in self.results.values() if lm.get_string("warrant_evaluator.rec_add") in r['recommendation']])
        remove_count = len([r for r in self.results.values() if lm.get_string("warrant_evaluator.rec_remove") in r['recommendation']])
        keep_count = len([r for r in self.results.values() if lm.get_string("warrant_evaluator.rec_keep") in r['recommendation']])
        
        p = self.params
        report = [
            lm.get_string("report_generator.header.title1"),
            lm.get_string("report_generator.header.title2"),
            lm.get_string("report_generator.header.title3"),
            f"\n{lm.get_string('report_generator.general_data.title')}",
            "----------------------------------------------------------------------",
            f"* {lm.get_string('report_generator.general_data.scenario')}:         {self.scenario_name}",
            f"* {lm.get_string('report_generator.general_data.date')}:           {analysis_date}",
            f"* Fonte de Dados: Banco de Dados Histórico (traffic_samples)",
            f"\n{lm.get_string('report_generator.summary.title')}",
            "----------------------------------------------------------------------",
            f"* {lm.get_string('report_generator.summary.junctions_analyzed')}: {len(self.results)}",
            f"* {lm.get_string('report_generator.summary.recommendations', add=add_count, remove=remove_count, keep=keep_count)}",
            f"\n{lm.get_string('report_generator.parameters.title')}",
            "----------------------------------------------------------------------",
            f"* {lm.get_string('report_generator.parameters.min_vol_primary')}:   {p.get('min_volume_primary', 'N/A')} vph",
            f"* {lm.get_string('report_generator.parameters.min_vol_secondary')}:  {p.get('min_volume_secondary', 'N/A')} vph",
            f"* {lm.get_string('report_generator.parameters.unacceptable_delay')}:         {p.get('unacceptable_delay', 'N/A')} segundos",
            f"* Fila Máxima P95:                  {p.get('max_queue_p95', 'N/A')} veículos",
            f"* Saturação Crítica (X):            {p.get('saturation_critical', 'N/A')}",
            f"* Fluxo Ideal por Faixa (F_ideal):  {p.get('ideal_flow_per_lane', 'N/A')} vph",
            f"\n  Fórmulas Utilizadas:",
            f"  - Volume: q = k × (v × 3.6)  [veh/km × km/h = vph]",
            f"  - Atraso: D = L/v_real - L/v_limite  [segundos]",
            f"  - Fila:   Percentil 95 (P95) do queue_length",
            f"  - Saturação: X = q / (N × F_ideal)  [adimensional]",
            f"\n\n{lm.get_string('report_generator.detailed_rec.title1')}",
            f"{lm.get_string('report_generator.detailed_rec.title2')}",
            f"{lm.get_string('report_generator.detailed_rec.title3')}"
        ]

        for j_id, result in sorted(self.results.items()):
            w = result['warrants']
            d = result['data']
            
            satisfied_str = lm.get_string('report_generator.junction.warrant_satisfied')
            not_satisfied_str = lm.get_string('report_generator.junction.warrant_not_satisfied')
            
            # Determine warrant icons
            w1_icon = '✔️' if w.get('volume') else '❌'
            w2_icon = '✔️' if w.get('delay') else '❌'
            w3_icon = '✔️' if w.get('queue_p95') else '❌'
            w4_icon = '✔️' if w.get('saturation') else '❌'

            report.extend([
                f"\n----------------------------------------------------------------------",
                f">>> {lm.get_string('report_generator.junction.title', id=j_id)}",
                f"----------------------------------------------------------------------",
                f"* {lm.get_string('report_generator.junction.recommendation')}:     {result.get('recommendation', 'N/A')}",
                f"* {lm.get_string('report_generator.junction.current_status')}:         {result.get('current_status', 'N/A')}",
                f"* {lm.get_string('report_generator.junction.justification')}:  {result.get('justification', 'N/A')}",
                f"",
                f"* {lm.get_string('report_generator.junction.warrants_analysis')}:",
                f"  - [{w1_icon}] W1 - Volume (q = k×v×3.6): {satisfied_str if w.get('volume') else not_satisfied_str}",
                f"  - [{w2_icon}] W2 - Atraso Real (D = L/v_real - L/v_lim): {satisfied_str if w.get('delay') else not_satisfied_str}",
                f"  - [{w3_icon}] W3 - Fila P95: {satisfied_str if w.get('queue_p95') else not_satisfied_str}",
                f"  - [{w4_icon}] W4 - Saturação (X = q/C): {satisfied_str if w.get('saturation') else not_satisfied_str}",
                f"",
                f"* {lm.get_string('report_generator.junction.observed_data')}:",
                f"  - Volume Primário (q):        {d.get('vol_primary_val', 0):.1f} vph (limiar: {p.get('min_volume_primary', 'N/A')} vph)",
                f"  - Volume Secundário (q):      {d.get('vol_secondary_val', 0):.1f} vph (limiar: {p.get('min_volume_secondary', 'N/A')} vph)",
                f"  - Atraso Real (D):            {d.get('avg_delay', 0):.2f} s (limiar: {p.get('unacceptable_delay', 'N/A')} s)",
                f"  - Fila P95:                   {d.get('queue_p95', 0)} veículos (limiar: {p.get('max_queue_p95', 'N/A')})",
                f"  - Grau de Saturação (X):      {d.get('saturation_ratio', 0):.4f} (limiar: {p.get('saturation_critical', 'N/A')})",
            ])

        report.extend([
            f"\n\n{lm.get_string('report_generator.footer.title1')}",
            f"{lm.get_string('report_generator.footer.title2')}",
            f"{lm.get_string('report_generator.footer.title3')}",
            lm.get_string('report_generator.footer.generated_by')
        ])
        
        return "\n".join(report)