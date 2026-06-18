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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/utils/safety_rules.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import json
import os
import logging

class SafetyRules:
    _rules = None

    @classmethod
    def get_rules(cls) -> dict:
        if cls._rules is None:
            rules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "safety_rules.json"))
            try:
                with open(rules_path, "r", encoding="utf-8") as f:
                    cls._rules = json.load(f)
                logging.info(f"[SafetyRules] Regras de segurança carregadas de {rules_path}")
            except Exception as e:
                logging.warning(f"[SafetyRules] Falha ao carregar safety_rules.json ({e}). Usando fallback padrão de engenharia.")
                cls._rules = {
                    "green_time_seconds": 10.0,
                    "yellow_time_seconds": 4.0,
                    "all_red_time_seconds": 3.0,
                    "red_time_seconds": 15.0
                }
        return cls._rules

    @classmethod
    def get_green(cls) -> float:
        return float(cls.get_rules().get("green_time_seconds", 10.0))

    @classmethod
    def get_yellow(cls) -> float:
        return float(cls.get_rules().get("yellow_time_seconds", 4.0))

    @classmethod
    def get_all_red(cls) -> float:
        return float(cls.get_rules().get("all_red_time_seconds", 3.0))

    @classmethod
    def get_red(cls) -> float:
        return float(cls.get_rules().get("red_time_seconds", 15.0))
