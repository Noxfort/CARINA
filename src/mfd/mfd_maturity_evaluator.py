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

# File: src/mfd/mfd_maturity_evaluator.py
# Author: Gabriel Moraes
# Date: 2026

import logging
from typing import Dict, Any, List
from utils.locale_manager_backend import LocaleManagerBackend
from mfd.mfd_map_resolver import MFDMapResolver
from mfd.mfd_stage_aggregator import MFDStageAggregator
from mfd.mfd_fallback_factory import MFDFallbackFactory

class MFDMaturityEvaluator:
    """
    High-Level Orchestrator: Evaluates MFD performance data across DA SILVA maturation stages
    (CHILD, TEEN, ADULT). Delegates map discovery to MFDMapResolver, snapshot aggregation to
    MFDStageAggregator, and fallback generation to MFDFallbackFactory.
    Adheres strictly to SOLID architectural design principles (SRP, DIP, OCP).
    """

    @staticmethod
    def extract_maturity_stages(
        mfd_history_data: Dict[str, Any],
        lang: str = "pt_br"
    ) -> Dict[str, Any]:
        """
        Orchestrates the extraction and mathematical evaluation of representative metrics
        for the 3 maturation stages: CHILD (Baseline), TEEN (Intermediate), and ADULT (Mature).
        """
        lm = LocaleManagerBackend()
        if lang == "fr_fr":
            stage_init_label = "Phase Initiale (Enfance)"
            stage_inter_label = "Phase Intermédiaire (Adolescence)"
            stage_mature_label = "Phase Mature (Adulte)"
            level_init_label = "Début du Test (Ligne de Base)"
            level_inter_label = "Milieu du Test (Optimisation)"
            level_mature_label = "Fin du Test (Optimisé)"
        elif lang == "es_es":
            stage_init_label = "Fase Inicial (Infancia)"
            stage_inter_label = "Fase Intermedia (Adolescencia)"
            stage_mature_label = "Fase Madura (Adulto)"
            level_init_label = "Inicio de la Muestra (Línea Base)"
            level_inter_label = "Mitad de la Muestra (Optimización)"
            level_mature_label = "Fin de la Muestra (Optimizado)"
        elif lang == "en_us":
            stage_init_label = "Initial Stage (Child)"
            stage_inter_label = "Intermediate Stage (Teen)"
            stage_mature_label = "Mature Stage (Adult)"
            level_init_label = "Sample Start (Baseline)"
            level_inter_label = "Sample Mid (Optimization)"
            level_mature_label = "Sample End (Optimized)"
        else:
            stage_init_label = lm.get_string("mfd.stage_initial", lang=lang, default="Fase Criança (Linha Base)")
            stage_inter_label = lm.get_string("mfd.stage_intermediate", lang=lang, default="Fase Adolescente (Em Otimização)")
            stage_mature_label = lm.get_string("mfd.stage_mature", lang=lang, default="Fase Adulta (Otimizado)")
            level_init_label = lm.get_string("mfd.level_initial", lang=lang, default="Início da Amostragem (Ponto Zero / Plano Fixo Tradicional)")
            level_inter_label = lm.get_string("mfd.level_intermediate", lang=lang, default="Meio da Amostragem (Aprendizado Ativo / Autonomia Supervisada)")
            level_mature_label = lm.get_string("mfd.level_mature", lang=lang, default="Fim da Amostragem (Estado Estável / Otimizado 24/7)")

        labels_dict = {
            "initial": stage_init_label,
            "intermediate": stage_inter_label,
            "mature": stage_mature_label,
            "level_init": level_init_label,
            "level_inter": level_inter_label,
            "level_mature": level_mature_label
        }

        history = mfd_history_data.get("history", [])
        peak_prod = mfd_history_data.get("peak_production", 0.0)
        peak_accum = mfd_history_data.get("peak_accumulation", 0.0)

        if not history:
            logging.warning("[MFDMaturityEvaluator] Empty history provided. Delegating to MFDFallbackFactory.")
            return MFDFallbackFactory.get_empty_fallback(labels_dict)

        n = len(history)

        child_snaps = []
        teen_snaps = []
        adult_snaps = []

        for h in history:
            stage_found = None
            if "maturity_stage" in h:
                stage_found = h["maturity_stage"]
            elif "intersections" in h and h["intersections"]:
                first_inter = next(iter(h["intersections"].values()), {})
                stage_found = first_inter.get("maturity_stage")

            if stage_found == "CHILD":
                child_snaps.append(h)
            elif stage_found == "TEEN":
                teen_snaps.append(h)
            elif stage_found == "ADULT":
                adult_snaps.append(h)

        if child_snaps or teen_snaps or adult_snaps:
            initial_metrics = MFDStageAggregator.aggregate_snapshots(
                child_snaps or [history[0]],
                level_name=labels_dict["level_init"],
                stage_label=labels_dict["initial"],
                stage_key="initial"
            )
            inter_metrics = MFDStageAggregator.aggregate_snapshots(
                teen_snaps or [history[n // 2]],
                level_name=labels_dict["level_inter"],
                stage_label=labels_dict["intermediate"],
                stage_key="intermediate"
            )
            mature_metrics = MFDStageAggregator.aggregate_snapshots(
                adult_snaps or [history[-1]],
                level_name=labels_dict["level_mature"],
                stage_label=labels_dict["mature"],
                stage_key="mature"
            )
        elif n == 1:
            initial_metrics = MFDStageAggregator.summarize_single_snapshot(history[0], level_name=labels_dict["level_init"], stage_label=labels_dict["initial"], stage_key="initial")
            inter_metrics = MFDStageAggregator.summarize_single_snapshot(history[0], level_name=labels_dict["level_inter"], stage_label=labels_dict["intermediate"], stage_key="intermediate")
            mature_metrics = MFDStageAggregator.summarize_single_snapshot(history[0], level_name=labels_dict["level_mature"], stage_label=labels_dict["mature"], stage_key="mature")
        elif n == 2:
            initial_metrics = MFDStageAggregator.summarize_single_snapshot(history[0], level_name=labels_dict["level_init"], stage_label=labels_dict["initial"], stage_key="initial")
            inter_metrics = MFDStageAggregator.summarize_single_snapshot(history[0], level_name=labels_dict["level_inter"], stage_label=labels_dict["intermediate"], stage_key="intermediate")
            mature_metrics = MFDStageAggregator.summarize_single_snapshot(history[1], level_name=labels_dict["level_mature"], stage_label=labels_dict["mature"], stage_key="mature")
        else:
            idx_initial = 0
            idx_inter = n // 2
            idx_mature = n - 1

            initial_metrics = MFDStageAggregator.summarize_single_snapshot(history[idx_initial], level_name=labels_dict["level_init"], stage_label=labels_dict["initial"], stage_key="initial")
            inter_metrics = MFDStageAggregator.summarize_single_snapshot(history[idx_inter], level_name=labels_dict["level_inter"], stage_label=labels_dict["intermediate"], stage_key="intermediate")
            mature_metrics = MFDStageAggregator.summarize_single_snapshot(history[idx_mature], level_name=labels_dict["level_mature"], stage_label=labels_dict["mature"], stage_key="mature")

        comparison_metrics = MFDStageAggregator.calculate_comparative_metrics(
            initial_metrics=initial_metrics,
            inter_metrics=inter_metrics,
            mature_metrics=mature_metrics
        )

        return {
            "initial": initial_metrics,
            "intermediate": inter_metrics,
            "mature": mature_metrics,
            "comparison_metrics": comparison_metrics,
            "total_steps_recorded": n,
            "peak_production": peak_prod,
            "peak_accumulation": peak_accum
        }

    @staticmethod
    def _discover_signalized_ids() -> List[str]:
        """
        Delegates traffic light topology discovery to MFDMapResolver.
        Maintains backward compatibility.
        """
        return MFDMapResolver.discover_signalized_ids()

    @staticmethod
    def _generate_fallback_intersections(
        stage_key: str = "initial",
        avg_speed: float = 0.0,
        avg_delay: float = 0.0,
        avg_queue: float = 0.0
    ) -> Dict[str, Any]:
        """
        Delegates fallback intersection generation to MFDFallbackFactory.
        Maintains backward compatibility.
        """
        return MFDFallbackFactory.generate_fallback_intersections(
            stage_key=stage_key,
            avg_speed=avg_speed,
            avg_delay=avg_delay,
            avg_queue=avg_queue
        )

    @staticmethod
    def _summarize_stage(
        point: Dict[str, Any],
        level_name: str,
        stage_label: str,
        stage_key: str = "initial"
    ) -> Dict[str, Any]:
        """
        Delegates single snapshot summarization to MFDStageAggregator.
        Maintains backward compatibility.
        """
        return MFDStageAggregator.summarize_single_snapshot(
            point=point,
            level_name=level_name,
            stage_label=stage_label,
            stage_key=stage_key
        )

    @staticmethod
    def _get_empty_fallback(labels_dict: Dict[str, str]) -> Dict[str, Any]:
        """
        Delegates empty fallback generation to MFDFallbackFactory.
        Maintains backward compatibility.
        """
        return MFDFallbackFactory.get_empty_fallback(labels_dict)
