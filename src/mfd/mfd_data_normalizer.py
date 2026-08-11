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

# File: src/mfd/mfd_data_normalizer.py
# Author: Gabriel Moraes
# Date: 2026

import logging
from typing import Dict, Any, List

from mfd.mfd_maturity_evaluator import MFDMaturityEvaluator
from mfd.mfd_impact_calculator import MFDImpactCalculator

class MFDDataNormalizer:
    """
    Responsibility: Normalize raw MFD history data into structured, compact statistical payloads
    and DA SILVA 3-stage maturity metrics (CHILD Baseline, TEEN Optimizing, ADULT Fully Optimized).
    """

    @staticmethod
    def normalize_mfd_data(mfd_history_data: Dict[str, Any], summary_stats: Dict[str, Any] = None, lang: str = "pt_br") -> Dict[str, Any]:
        """
        Normalizes history data, extracts stage snapshots, and computes per-intersection and global stats.
        """
        history = mfd_history_data.get("history", [])
        peak_prod = mfd_history_data.get("peak_production", 0.0)
        peak_accum = mfd_history_data.get("peak_accumulation", 0.0)

        logging.info(f"[MFD_NORMALIZER] Normalizando {len(history)} amostras da curva MFD e calculando maturação em 3 estágios DA SILVA (CHILD/TEEN/ADULT)...")

        if summary_stats is None:
            summary_stats = {}

        # 1. Extract Representative Stage Snapshots
        stages_data = MFDMaturityEvaluator.extract_maturity_stages(mfd_history_data, lang=lang)

        # 2. Compute Physical and Socio-Environmental Impact Metrics
        impact_stats = MFDImpactCalculator.calculate_full_impacts(stages_data, history, lang=lang)

        # 3. Process Intersections Table — Filter to ONLY signalized intersections under active CARINA control
        raw_intersections = impact_stats.get("intersections_table", [])
        intersections_list = [row for row in raw_intersections if row.get("is_signalized", True)]
        
        signalized_count = len(intersections_list)
        adult_count = sum(1 for row in intersections_list if row.get("maturity") == "ADULT")
        teen_count = signalized_count - adult_count

        stats = {
            "total_intersections": signalized_count,
            "signalized_count": signalized_count,
            "unsignalized_count": 0,
            "adult_count": adult_count,
            "teen_count": teen_count,
            "peak_production": peak_prod,
            "peak_accumulation": peak_accum,
            "total_steps": len(history)
        }

        logging.info(f"[MFD_NORMALIZER] Dados MFD normalizados com sucesso: {signalized_count} cruzamentos semafóricos sob controle ativo CARINA auditados ({adult_count} na Fase Adulta).")

        return {
            "stages_data": stages_data,
            "impact_stats": impact_stats,
            "intersections_list": intersections_list,
            "summary_stats": summary_stats,
            "stats": stats
        }
