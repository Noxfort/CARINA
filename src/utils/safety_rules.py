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
                    "min_green_time_seconds": 10.0,
                    "yellow_time_seconds": 4.0,
                    "all_red_time_seconds": 2.0
                }
        return cls._rules

    @classmethod
    def get_min_green(cls) -> float:
        return float(cls.get_rules().get("min_green_time_seconds", 10.0))

    @classmethod
    def get_yellow(cls) -> float:
        return float(cls.get_rules().get("yellow_time_seconds", 4.0))

    @classmethod
    def get_all_red(cls) -> float:
        return float(cls.get_rules().get("all_red_time_seconds", 2.0))
