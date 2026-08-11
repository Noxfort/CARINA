# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# File: tests/unit/test_sas_report_generator.py

import pytest
from unittest.mock import MagicMock, patch

from sas.report_generator import ReportGenerator
from sas.report_transducer_factory import ReportTransducerFactory
from sas.report_intersection_processor import ReportIntersectionProcessor
from sas.report_table_builder import ReportTableBuilder


def test_report_transducer_factory_fallback():
    """Verify that ReportTransducerFactory returns a valid transducer instance."""
    transducer = ReportTransducerFactory.create_transducer()
    assert transducer is not None
    assert hasattr(transducer, "generate_report")
    ReportTransducerFactory.release_transducer(transducer)


def test_report_intersection_processor():
    """Verify intersection processing and geometry extraction."""
    mock_data = {
        "id": "J1",
        "data": {
            "vol_primary_val": 450.0,
            "vol_secondary_val": 120.0,
            "avg_delay": 18.5,
            "queue_p95": 4,
            "saturation_ratio": 0.65,
            "lanes_primary": 2,
            "lanes_secondary": 1
        },
        "recommendation": "Otimizar tempo de ciclo",
        "status": "Sinalizado"
    }

    stats = {
        "critical_j_ids": set(),
        "total_junctions": 1
    }

    res = ReportIntersectionProcessor.process_single_intersection("J1", mock_data, stats, "pt_br")
    assert res["clean_j_id"] == "J1"
    assert res["vol_primary_val"] == 450.0
    assert res["vol_secondary_val"] == 120.0
    assert res["lanes_p"] == 2
    assert res["lanes_s"] == 1


def test_report_generator_execution():
    """Verify high-level report generation workflow execution."""
    junctions_data = {
        "J1": {
            "id": "J1",
            "data": {
                "vol_primary_val": 500.0,
                "vol_secondary_val": 150.0,
                "avg_delay": 12.0,
                "queue_p95": 3,
                "saturation_ratio": 0.55
            },
            "recommendation": "Manter",
            "status": "Sinalizado"
        }
    }

    result_tuple = ReportGenerator.generate_report(junctions_data=junctions_data)
    assert isinstance(result_tuple, tuple)
    assert len(result_tuple) == 2
    assert result_tuple[0] is None
    assert isinstance(result_tuple[1], str)
    assert len(result_tuple[1]) > 0
    assert "Síntese de Auditoria da Malha Viária" in result_tuple[1]
