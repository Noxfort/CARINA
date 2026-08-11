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

# File: tests/unit/test_mfd_new_report.py
# Author: Gabriel Moraes
# Date: July 31, 2026

import pytest
from mfd.mfd_maturity_evaluator import MFDMaturityEvaluator
from mfd.mfd_impact_calculator import MFDImpactCalculator
from mfd.mfd_report_generator import MFDReportGenerator

def test_mfd_maturity_evaluator():
    """Verify that maturity stages are correctly segmented into initial, intermediate, and mature."""
    history_mock = [
        {"speed": 5.0, "production": 100.0, "accumulation": 200.0, "efficiency": 0.5, "queue": 10.0, "delay": 50.0},
        {"speed": 7.5, "production": 150.0, "accumulation": 300.0, "efficiency": 0.75, "queue": 8.0, "delay": 35.0},
        {"speed": 10.0, "production": 200.0, "accumulation": 400.0, "efficiency": 0.95, "queue": 5.0, "delay": 20.0}
    ]
    data = {
        "history": history_mock,
        "peak_production": 200.0,
        "peak_accumulation": 400.0
    }

    stages = MFDMaturityEvaluator.extract_maturity_stages(data)
    assert "initial" in stages
    assert "intermediate" in stages
    assert "mature" in stages

    assert stages["initial"]["avg_speed"] == 5.0
    assert stages["intermediate"]["avg_speed"] == 7.5
    assert stages["mature"]["avg_speed"] == 10.0

def test_mfd_impact_calculator():
    """Verify that physical conversions, deltas, and socio-environmental impacts are correctly computed."""
    history_mock = [
        {"speed": 5.0, "production": 100.0, "accumulation": 200.0, "efficiency": 0.5, "queue": 10.0, "delay": 50.0},
        {"speed": 7.5, "production": 150.0, "accumulation": 300.0, "efficiency": 0.75, "queue": 8.0, "delay": 35.0},
        {"speed": 10.0, "production": 200.0, "accumulation": 400.0, "efficiency": 0.95, "queue": 5.0, "delay": 20.0}
    ]
    data = {
        "history": history_mock,
        "peak_production": 200.0,
        "peak_accumulation": 400.0
    }
    stages = MFDMaturityEvaluator.extract_maturity_stages(data)
    impacts = MFDImpactCalculator.calculate_full_impacts(stages, history_mock)

    assert "comparative_table" in impacts
    assert "socio_environmental" in impacts

    comp = impacts["comparative_table"]
    assert comp["speed_kmh"]["initial"] == 18.0 # 5.0 m/s * 3.6
    assert comp["speed_kmh"]["mature"] == 36.0  # 10.0 m/s * 3.6
    assert comp["speed_kmh"]["delta_pct"] == 100.0

    socio = impacts["socio_environmental"]
    assert socio["man_hours_saved_daily"] >= 0.0
    assert socio["speed_gain_mature_pct"] >= 0.0
    assert socio["delay_reduction_mature_pct"] >= 0.0

def test_mfd_multilingual_support():
    """Verify that stage and evaluation labels adapt dynamically to any interface language (pt_br, fr_fr, es_es, en_us)."""
    history_mock = [
        {"speed": 5.0, "production": 100.0, "accumulation": 200.0, "efficiency": 0.5, "queue": 10.0, "delay": 50.0},
        {"speed": 10.0, "production": 200.0, "accumulation": 400.0, "efficiency": 0.95, "queue": 5.0, "delay": 20.0}
    ]
    data = {"history": history_mock, "peak_production": 200.0, "peak_accumulation": 400.0}

    # French (fr_fr)
    stages_fr = MFDMaturityEvaluator.extract_maturity_stages(data, lang="fr_fr")
    assert stages_fr["initial"]["stage_label"] == "Phase Initiale (Enfance)"
    impacts_fr = MFDImpactCalculator.calculate_full_impacts(stages_fr, history_mock, lang="fr_fr")
    assert impacts_fr["comparative_table"]["speed_kmh"]["evaluation"] == "AMÉLIORATION SIGNIFICATIVE"

    # Spanish (es_es)
    stages_es = MFDMaturityEvaluator.extract_maturity_stages(data, lang="es_es")
    assert stages_es["initial"]["stage_label"] == "Fase Inicial (Infancia)"
    impacts_es = MFDImpactCalculator.calculate_full_impacts(stages_es, history_mock, lang="es_es")
    assert impacts_es["comparative_table"]["speed_kmh"]["evaluation"] == "MEJORA SIGNIFICATIVA"

    # Portuguese (pt_br)
    stages_pt = MFDMaturityEvaluator.extract_maturity_stages(data, lang="pt_br")
    assert stages_pt["initial"]["stage_label"] == "Fase Criança (Linha Base)"
    impacts_pt = MFDImpactCalculator.calculate_full_impacts(stages_pt, history_mock, lang="pt_br")
    assert impacts_pt["comparative_table"]["speed_kmh"]["evaluation"] == "MELHORIA SIGNIFICATIVA"

def test_mfd_report_generator_execution():
    """Verify that MFDReportGenerator executes cleanly and returns a completed report dictionary."""
    history_mock = [
        {"speed": 5.0, "production": 100.0, "accumulation": 200.0, "efficiency": 0.5, "queue": 10.0, "delay": 50.0},
        {"speed": 10.0, "production": 200.0, "accumulation": 400.0, "efficiency": 0.95, "queue": 5.0, "delay": 20.0}
    ]
    data = {
        "history": history_mock,
        "peak_production": 200.0,
        "peak_accumulation": 400.0
    }

    res = MFDReportGenerator.generate_report(data)
    assert res["status"] == "complete"
    assert "text_report" in res
    assert len(res["text_report"]) > 0
