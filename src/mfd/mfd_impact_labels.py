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

# File: src/mfd/mfd_impact_labels.py
# Author: Gabriel Moraes
# Date: August 8, 2026

import os
import json
import logging
from typing import Dict, Any

class MFDImpactLabels:
    """
    Responsibility: Load and manage localized evaluation labels dynamically from external JSON configuration
    files to satisfy the Single Responsibility and Open/Closed principles.
    """

    _cached_labels: Dict[str, Dict[str, str]] = None

    DEFAULT_FALLBACK_LABELS = {
        "pt_br": {
            "speed_improved": "MELHORIA SIGNIFICATIVA",
            "prod_expanded": "GANHO DE ESCOAMENTO",
            "queue_reduced": "REDUÇÃO DE FILAS",
            "delay_reduced": "REDUÇÃO DE ATRASO",
            "eff_optimized": "OTIMIZAÇÃO PLENA",
            "stable": "ESTÁVEL"
        },
        "en": {
            "speed_improved": "SIGNIFICANT IMPROVEMENT",
            "prod_expanded": "CAPACITY EXPANSION",
            "queue_reduced": "QUEUE REDUCTION",
            "delay_reduced": "DELAY REDUCTION",
            "eff_optimized": "FULL OPTIMIZATION",
            "stable": "STABLE"
        }
    }

    @classmethod
    def load_labels_config(cls) -> Dict[str, Dict[str, str]]:
        """
        Load evaluation labels from external JSON configuration file with in-memory caching.

        :return: Dict mapping language key to label dictionary
        """
        if cls._cached_labels is not None:
            return cls._cached_labels

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "..", "..", "config", "mfd_impact_labels.json"),
            os.path.join(base_dir, "..", "config", "mfd_impact_labels.json"),
            os.path.join(os.getcwd(), "config", "mfd_impact_labels.json")
        ]

        for json_path in candidates:
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        cls._cached_labels = json.load(f)
                        return cls._cached_labels
                except Exception as e:
                    logging.warning(f"Failed to load MFD impact labels from JSON '{json_path}': {e}.")

        cls._cached_labels = cls.DEFAULT_FALLBACK_LABELS
        return cls._cached_labels

    @classmethod
    def get_labels_for_lang(cls, lang: str = "pt_br") -> Dict[str, str]:
        """
        Normalize language code string and retrieve localized evaluation label mapping from loaded configuration.

        :param lang: Language locale code (e.g., 'pt_br', 'en_us', 'es_es', 'fr_fr', etc.)
        :return: Dictionary of evaluation key -> localized label text
        """
        labels_dict = cls.load_labels_config()
        raw_lang = str(lang).lower()
        lang_key = raw_lang.split("_")[0].split("-")[0]
        if lang_key == "pt":
            lang_key = "pt_br"

        return labels_dict.get(lang_key, labels_dict.get("pt_br", labels_dict.get("en", cls.DEFAULT_FALLBACK_LABELS["en"])))

    @classmethod
    def resolve_metric_evaluations(
        cls,
        speed_delta_pct: float,
        prod_delta_pct: float,
        queue_delta_pct: float,
        delay_delta_pct: float,
        eff_delta_pct: float,
        lang: str = "pt_br"
    ) -> Dict[str, str]:
        """
        Evaluate physical metrics delta and return localized evaluation strings.

        :param speed_delta_pct: Percentage change in average speed
        :param prod_delta_pct: Percentage change in network production
        :param queue_delta_pct: Percentage change in average queue length
        :param delay_delta_pct: Percentage change in average delay
        :param eff_delta_pct: Percentage change in operational efficiency
        :param lang: Language locale code
        :return: Dict mapping metric name to localized evaluation string
        """
        labels = cls.get_labels_for_lang(lang)
        stable = labels.get("stable", "ESTÁVEL")

        return {
            "speed": labels.get("speed_improved", stable) if speed_delta_pct > 0 else stable,
            "production": labels.get("prod_expanded", stable) if prod_delta_pct > 0 else stable,
            "queue": labels.get("queue_reduced", stable) if queue_delta_pct < 0 else stable,
            "delay": labels.get("delay_reduced", stable) if delay_delta_pct < 0 else stable,
            "efficiency": labels.get("eff_optimized", stable) if eff_delta_pct > 0 else stable
        }

def get_impact_labels(lang: str = "pt_br") -> Dict[str, str]:
    """Module-level helper to retrieve impact labels mapping."""
    return MFDImpactLabels.get_labels_for_lang(lang)
