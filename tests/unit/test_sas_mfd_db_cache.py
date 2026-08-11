import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.database.database_manager import DatabaseManager
from src.utils.locale_manager_backend import LocaleManagerBackend
from src.mfd.mfd_baseline_manager import MFDReportBaselineManager


@pytest.fixture
def temp_db_manager(tmp_path):
    locale_manager = MagicMock(spec=LocaleManagerBackend)
    db_file = str(tmp_path / "test_carina.db")
    db_mgr = DatabaseManager(locale_manager=locale_manager, db_name=db_file)
    db_mgr.engine.db_type = "sqlite"
    db_mgr.engine.db_path = db_file
    db_mgr.engine._initialize_db()
    return db_mgr


def test_sas_analysis_cache_db_persistence(temp_db_manager):
    scenario = "scenario_test_sas"
    initial_cache = {
        "junction_metrics": {
            "tl_1": {"volume": 120, "delay": 15.5}
        },
        "timestamp": "2026-08-06 10:00:00"
    }

    # 1. Empty cache initially
    assert temp_db_manager.get_sas_analysis_cache(scenario) == {}

    # 2. Save initial cache
    temp_db_manager.save_sas_analysis_cache(scenario, initial_cache)
    retrieved = temp_db_manager.get_sas_analysis_cache(scenario)
    assert retrieved["junction_metrics"]["tl_1"]["volume"] == 120

    # 3. Update cache (UPSERT)
    updated_cache = {
        "junction_metrics": {
            "tl_1": {"volume": 250, "delay": 8.0}
        },
        "timestamp": "2026-08-06 11:00:00"
    }
    temp_db_manager.save_sas_analysis_cache(scenario, updated_cache)
    retrieved_updated = temp_db_manager.get_sas_analysis_cache(scenario)
    assert retrieved_updated["junction_metrics"]["tl_1"]["volume"] == 250
    assert retrieved_updated["timestamp"] == "2026-08-06 11:00:00"


def test_mfd_analysis_baselines_db_persistence(temp_db_manager):
    scenario = "scenario_test_mfd"
    snapshot_run1 = {
        "avg_speed": 12.5,
        "avg_prod": 500.0,
        "timestamp": "Run 1 Baseline"
    }

    snapshot_run2 = {
        "avg_speed": 18.2,
        "avg_prod": 650.0,
        "timestamp": "Run 2 Updated"
    }

    # 1. Initially empty
    last_data, first_data = temp_db_manager.get_mfd_analysis_baselines(scenario)
    assert last_data == {}
    assert first_data == {}

    # 2. Save first run -> Should set both 'last' and 'first'
    temp_db_manager.save_mfd_analysis_baselines(scenario, snapshot_run1)
    last_data, first_data = temp_db_manager.get_mfd_analysis_baselines(scenario)
    assert last_data["timestamp"] == "Run 1 Baseline"
    assert first_data["timestamp"] == "Run 1 Baseline"

    # 3. Save second run -> Should update 'last' but PRESERVE 'first'
    temp_db_manager.save_mfd_analysis_baselines(scenario, snapshot_run2)
    last_data, first_data = temp_db_manager.get_mfd_analysis_baselines(scenario)
    assert last_data["timestamp"] == "Run 2 Updated"
    assert last_data["avg_speed"] == 18.2
    assert first_data["timestamp"] == "Run 1 Baseline"
    assert first_data["avg_speed"] == 12.5


def test_mfd_baseline_manager_fallback(temp_db_manager, tmp_path):
    scenario_dir = str(tmp_path / "results" / "test_fallback_scenario")
    os.makedirs(scenario_dir, exist_ok=True)
    scenario_name = "test_fallback_scenario"

    snapshot = {"avg_speed": 15.0, "status": "ok"}

    # Save via MFDReportBaselineManager with db_manager
    MFDReportBaselineManager.save_baselines(
        scenario_results_dir=scenario_dir,
        current_analysis_snapshot=snapshot,
        scenario_name=scenario_name,
        db_manager=temp_db_manager
    )

    # Verify files created as secondary backup
    assert os.path.exists(os.path.join(scenario_dir, "mfd_last_analysis.json"))
    assert os.path.exists(os.path.join(scenario_dir, "mfd_first_analysis.json"))

    # Load via MFDReportBaselineManager with db_manager
    last_data, first_data = MFDReportBaselineManager.load_baselines(
        scenario_results_dir=scenario_dir,
        scenario_name=scenario_name,
        db_manager=temp_db_manager
    )
    assert last_data["avg_speed"] == 15.0
    assert first_data["avg_speed"] == 15.0
