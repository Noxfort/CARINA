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

# File: tests/unit/test_sas_helpers.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import pytest
from unittest.mock import MagicMock, patch
from sas.analyzer_data_processor import AnalyzerDataProcessor
from sas.heatmap_calibrator import HeatmapCalibrator
from utils.locale_manager_backend import LocaleManagerBackend

def test_heatmap_calibrator_not_enough_data():
    calibrator = HeatmapCalibrator()
    # 99 points is less than the required minimum of 100
    points = [{"occupancy": 0.5, "waiting_time": 10.0, "flow": 2.0, "bad_events": 1} for _ in range(99)]
    res = calibrator.calibrate(points)
    assert res is None

def test_heatmap_calibrator_success():
    calibrator = HeatmapCalibrator()
    if not calibrator.is_available():
        pytest.skip("Pandas/Sklearn not available in this environment")
    
    import random
    points = []
    for _ in range(110):
        points.append({
            "occupancy": random.uniform(0.1, 0.9),
            "waiting_time": random.uniform(5.0, 50.0),
            "flow": random.uniform(1.0, 10.0),
            "bad_events": random.uniform(0.0, 5.0)
        })
    
    res = calibrator.calibrate(points)
    assert res is not None
    assert "weight_occupancy" in res
    assert "weight_waiting_time" in res
    assert "weight_flow" in res
    assert res["weight_occupancy"] >= 0.0
    assert res["weight_waiting_time"] >= 0.0
    assert res["weight_flow"] <= 0.0


def test_analyzer_data_processor_init():
    lm = MagicMock(spec=LocaleManagerBackend)
    processor = AnalyzerDataProcessor(lm)
    assert processor.locale_manager == lm
    assert processor.topology_parser is not None


def test_analysis_orchestrator_hft_rich_update():
    from sas.analysis_orchestrator import AnalysisOrchestrator
    from multiprocessing import Queue
    import configparser
    
    # Mock dependencies
    sas_queue = Queue()
    db_queue = Queue()
    settings = configparser.ConfigParser()
    settings['ANALYSIS_SCHEDULE'] = {
        'analysis_interval_value': '1',
        'analysis_interval_unit': 'days'
    }
    
    lm = MagicMock(spec=LocaleManagerBackend)
    lm.get_string.return_value = "mocked_string"
    
    # We patch DatabaseManager constructor to not try to connect to real db
    with patch("sas.analysis_orchestrator.DatabaseManager") as mock_db_mgr_cls:
        mock_db_mgr = MagicMock()
        mock_db_mgr_cls.return_value = mock_db_mgr
        
        # Instantiate orchestrator
        orchestrator = AnalysisOrchestrator(sas_queue, settings, db_queue, lm)
        orchestrator.initial_delay = 10
        orchestrator.frequency = 60
        
        # Mock engine.run_analysis
        orchestrator.engine = MagicMock()
        
        # Mock os.path.exists and os.listdir to pretend maps dir exists and contains net file
        with patch("os.path.exists", return_value=True), \
             patch("os.listdir", return_value=["test.net.xml"]):
            
            # Send a packet that triggers HFT mode but is before delay
            hft_packet = ("hft_rich_update", {"sim_time": 5})
            sas_queue.put(hft_packet)
            
            # We also send None to stop the orchestrator loop
            sas_queue.put(None)
            
            orchestrator.run()
            
            # Since sim_time (5) < initial_delay (10), run_analysis should NOT have been called
            orchestrator.engine.run_analysis.assert_not_called()
            
            # Now let's test when we exceed the delay and frequency
            sas_queue.put(("hft_rich_update", {"sim_time": 75}))
            sas_queue.put(None)
            
            # We mock DB manager connection behavior
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = (42,) # Mock run_id = 42
            mock_db_mgr.engine.get_connection.return_value = mock_conn
            mock_db_mgr.engine.db_type = "sqlite"
            
            orchestrator.run()
            
            # Since sim_time (75) >= initial_delay (10) and interval (75 - 0 >= 60), run_analysis should be called!
            orchestrator.engine.run_analysis.assert_called_once()
            
            # Let's verify the arguments passed to run_analysis
            args, kwargs = orchestrator.engine.run_analysis.call_args
            assert kwargs["sim_duration"] == 75
            assert kwargs["scenario_name"] == "hft_live_session"
            assert kwargs["run_id"] == 42
            assert kwargs["db_manager"] == mock_db_mgr


def test_analysis_orchestrator_trigger_analysis():
    from sas.analysis_orchestrator import AnalysisOrchestrator
    from multiprocessing import Queue
    import configparser
    
    # Mock dependencies
    sas_queue = Queue()
    db_queue = Queue()
    settings = configparser.ConfigParser()
    settings['ANALYSIS_SCHEDULE'] = {
        'analysis_interval_value': '1',
        'analysis_interval_unit': 'days'
    }
    
    lm = MagicMock(spec=LocaleManagerBackend)
    lm.get_string.return_value = "mocked_string"
    
    with patch("sas.analysis_orchestrator.DatabaseManager") as mock_db_mgr_cls:
        mock_db_mgr = MagicMock()
        mock_db_mgr_cls.return_value = mock_db_mgr
        
        # Instantiate orchestrator
        orchestrator = AnalysisOrchestrator(sas_queue, settings, db_queue, lm)
        orchestrator.last_net_file_path = "mock.net.xml"
        orchestrator.last_sim_time = 500
        
        # Mock engine.run_analysis
        orchestrator.engine = MagicMock()
        
        # We mock DB manager connection behavior
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (100,) # Mock run_id = 100
        mock_db_mgr.engine.get_connection.return_value = mock_conn
        mock_db_mgr.engine.db_type = "sqlite"
        
        # Send a trigger_analysis packet
        sas_queue.put(("trigger_analysis", {}))
        sas_queue.put(None)
        
        orchestrator.run()
        
        # run_analysis should be called immediately regardless of frequency/delay
        orchestrator.engine.run_analysis.assert_called_once()
        args, kwargs = orchestrator.engine.run_analysis.call_args
        assert kwargs["scenario_name"] == "hft_live_session"
        assert kwargs["net_file_path"] == "mock.net.xml"
        assert kwargs["run_id"] == 100
        assert kwargs["sim_duration"] == 500
        assert kwargs["db_manager"] == mock_db_mgr

def test_analyzer_engine_db_duration_validation(tmp_path):
    from sas.analyzer_engine import AnalyzerEngine
    import configparser
    import json
    
    settings = configparser.ConfigParser()
    settings['ANALYSIS_SCHEDULE'] = {
        'analysis_interval_value': '2',
        'analysis_interval_unit': 'hours'
    }
    
    from multiprocessing import Queue
    db_queue = Queue()
    lm = MagicMock(spec=LocaleManagerBackend)
    lm.get_string.return_value = "Skipped"
    
    # Mock db_manager to return a time range of 0.0 seconds (no data in DB)
    mock_db_mgr = MagicMock()
    mock_db_mgr.get_fluid_dynamics_time_range.return_value = 0.0
    
    sas_queue = Queue()
    engine = AnalyzerEngine(settings, db_queue, lm, sas_result_queue=sas_queue)
    
    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)):
        engine.run_analysis(
            accumulated_data={},
            sim_duration=10,
            scenario_name="test_scenario",
            net_file_path="mock.net.xml",
            run_id=1,
            db_manager=mock_db_mgr
        )
        
        # Check that sas_result_queue has received the error payload
        status_data = sas_queue.get(timeout=1.0)
        assert status_data["status"] == "error"
        assert "Nenhum dado de tráfego disponível" in status_data["message"]


def test_query_fluid_dynamics_history_with_limit():
    from repositories.fluid_dynamics_repo import FluidDynamicsRepository
    
    mock_engine = MagicMock()
    mock_engine.db_type = "postgres"
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_engine.get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    from datetime import datetime
    mock_cursor.fetchone.return_value = (datetime.now(),)
    mock_cursor.fetchall.return_value = []
    
    lm = MagicMock(spec=LocaleManagerBackend)
    repo = FluidDynamicsRepository(mock_engine, lm)
    
    # 1. Test PostgreSQL with limit
    repo.query_fluid_dynamics_history(limit_seconds=3600)
    assert mock_cursor.execute.call_count == 2
    sql_call = mock_cursor.execute.call_args_list[-1][0][0]
    assert "WHERE collected_at >= %s" in sql_call
    
    # 2. Test SQLite with limit
    mock_engine.db_type = "sqlite"
    mock_cursor.reset_mock()
    repo.query_fluid_dynamics_history(limit_seconds=3600)
    assert mock_cursor.execute.call_count == 2
    sql_call = mock_cursor.execute.call_args_list[-1][0][0]
    assert "WHERE collected_at >= ?" in sql_call


def test_infrastructure_analyzer_lightweight_cache():
    from analysis.infrastructure_analyzer import InfrastructureAnalyzer
    import configparser
    
    settings = configparser.ConfigParser()
    lm = MagicMock(spec=LocaleManagerBackend)
    lm.get_string.return_value = "mock_text"
    
    analyzer = InfrastructureAnalyzer(settings, lm)
    
    # Mock collected_data containing a large number of raw samples
    large_samples_list = [{"density": 0.1, "mean_speed": 10.0} for _ in range(500)]
    collected_data = {
        "j1": {
            "primary_edges": {"edge1": large_samples_list},
            "secondary_edges": {"edge2": large_samples_list},
            "conflict_events": 2,
            "type": "traffic_light"
        }
    }
    
    with patch("analysis.infrastructure_analyzer.WarrantEvaluator") as mock_eval_cls, \
         patch("analysis.infrastructure_analyzer.TextReportGenerator") as mock_rep_cls:
        
        mock_eval = MagicMock()
        mock_eval_cls.return_value = mock_eval
        mock_eval.evaluate.return_value = {
            'recommendation': "Keep",
            'current_status': "Existing",
            'justification': "Justified",
            'warrants': {},
            'data': {}
        }
        
        mock_rep = MagicMock()
        mock_rep_cls.return_value = mock_rep
        mock_rep.generate_txt_report.return_value = "report"
        
        res = analyzer.analyze_collected_data(
            collected_data=collected_data,
            last_analysis_cache={},
            scenario_name="test",
            true_traffic_light_ids=[]
        )
        
        # Verify cached_junction_metrics is lightweight (replaces lists of samples with their counts)
        cached_metrics = res["new_cache_data"]["junction_metrics"]
        assert "j1" in cached_metrics
        assert cached_metrics["j1"]["primary_edges"]["edge1"] == 500  # Stored as count (int)
        assert cached_metrics["j1"]["secondary_edges"]["edge2"] == 500  # Stored as count (int)
        assert cached_metrics["j1"]["conflict_events"] == 2
        assert cached_metrics["j1"]["type"] == "traffic_light"


def test_analyzer_data_processor_batch_processing():
    from sas.analyzer_data_processor import AnalyzerDataProcessor
    
    lm = MagicMock(spec=LocaleManagerBackend)
    processor = AnalyzerDataProcessor(lm)
    
    # Mock parser topology
    processor.topology_parser = MagicMock()
    processor.topology_parser.build.return_value = (
        {"j1": "traffic_light"},
        {"j1": {"edge1": {"num_lanes": 2, "length": 100.0}, "edge2": {"num_lanes": 1, "length": 100.0}}}
    )
    
    # Mock db_manager to return batches
    mock_db_mgr = MagicMock()
    
    # Batch yields list of dicts
    def mock_batches(limit_seconds, batch_size):
        yield [
            {"edge_id": "edge1", "density": 10.0, "mean_speed": 15.0, "queue_length": 5, "edge_length": 100.0, "num_lanes": 2, "speed_limit": 20.0},
            {"edge_id": "edge2", "density": 5.0, "mean_speed": 10.0, "queue_length": 2, "edge_length": 100.0, "num_lanes": 1, "speed_limit": 20.0}
        ]
        yield [
            {"edge_id": "edge1", "density": 12.0, "mean_speed": 14.0, "queue_length": 8, "edge_length": 100.0, "num_lanes": 2, "speed_limit": 20.0},
            {"edge_id": "edge2", "density": 6.0, "mean_speed": 9.0, "queue_length": 4, "edge_length": 100.0, "num_lanes": 1, "speed_limit": 20.0}
        ]
        
    mock_db_mgr.query_fluid_dynamics_history_batches = mock_batches
    
    res, true_tls = processor.process_historical_data(mock_db_mgr, "mock.net.xml", limit_seconds=3600)
    
    assert "j1" in res
    assert "edge1" in res["j1"]["primary_edges"]
    assert "edge2" in res["j1"]["secondary_edges"]
    
    # Verify that we generated representative samples
    samples1 = res["j1"]["primary_edges"]["edge1"]
    assert len(samples1) == 100
    
    # Check queue_length matches binned percentiles (values are binned to nearest 5)
    # queue_length=5 bins to 5, queue_length=8 bins to 5
    queues = [s["queue_length"] for s in samples1]
    assert 5 in queues


def test_analyzer_data_processor_equal_lanes():
    from sas.analyzer_data_processor import AnalyzerDataProcessor
    
    lm = MagicMock(spec=LocaleManagerBackend)
    processor = AnalyzerDataProcessor(lm)
    
    # Mock parser topology: both edges have 1 lane
    processor.topology_parser = MagicMock()
    processor.topology_parser.build.return_value = (
        {"j1": "traffic_light"},
        {"j1": {
            "edge1": {"num_lanes": 1, "length": 100.0, "lanes": ["edge1_0"]},
            "edge2": {"num_lanes": 1, "length": 100.0, "lanes": ["edge2_0"]},
            "edge3": {"num_lanes": 1, "length": 100.0, "lanes": ["edge3_0"]}
        }}
    )
    
    # Mock db_manager to return batches
    mock_db_mgr = MagicMock()
    
    # Batch yields list of dicts
    # edge1 will have highest volume, edge2 second highest, edge3 lowest.
    def mock_batches(limit_seconds, batch_size):
        yield [
            {"edge_id": "edge1", "density": 20.0, "mean_speed": 15.0, "queue_length": 5, "edge_length": 100.0, "num_lanes": 1, "speed_limit": 20.0},
            {"edge_id": "edge2", "density": 10.0, "mean_speed": 12.0, "queue_length": 2, "edge_length": 100.0, "num_lanes": 1, "speed_limit": 20.0},
            {"edge_id": "edge3", "density": 5.0, "mean_speed": 10.0, "queue_length": 1, "edge_length": 100.0, "num_lanes": 1, "speed_limit": 20.0}
        ]
        
    mock_db_mgr.query_fluid_dynamics_history_batches = mock_batches
    
    res, true_tls = processor.process_historical_data(mock_db_mgr, "mock.net.xml", limit_seconds=3600)
    
    assert "j1" in res
    
    # With 3 edges of equal lanes, the top 2 by volume (edge1 and edge2) should be primary, and edge3 secondary.
    assert "edge1" in res["j1"]["primary_edges"]
    assert "edge2" in res["j1"]["primary_edges"]
    assert "edge3" in res["j1"]["secondary_edges"]
    assert "edge1" not in res["j1"]["secondary_edges"]
    assert "edge3" not in res["j1"]["primary_edges"]


def test_analyzer_data_processor_accumulated_equal_lanes():
    from sas.analyzer_data_processor import AnalyzerDataProcessor
    
    lm = MagicMock(spec=LocaleManagerBackend)
    processor = AnalyzerDataProcessor(lm)
    
    # Mock parser topology: both edges have 1 lane
    processor.topology_parser = MagicMock()
    processor.topology_parser.build.return_value = (
        {"j1": "traffic_light"},
        {"j1": {
            "edge1": {"num_lanes": 1, "length": 100.0, "lanes": ["edge1_0"]},
            "edge2": {"num_lanes": 1, "length": 100.0, "lanes": ["edge2_0"]},
            "edge3": {"num_lanes": 1, "length": 100.0, "lanes": ["edge3_0"]}
        }}
    )
    
    accumulated_data = {
        "total_vehicles_departed_per_lane": {
            "edge1_0": 100,
            "edge2_0": 50,
            "edge3_0": 10
        },
        "total_waiting_time_per_lane": {
            "edge1_0": 1000.0,
            "edge2_0": 500.0,
            "edge3_0": 200.0
        },
        "conflict_events_per_junction": {
            "j1": 3
        }
    }
    
    # 3600 seconds = 1.0 hour
    res, true_tls = processor.process_accumulated_data(accumulated_data, 3600.0, "mock.net.xml")
    
    assert "j1" in res
    assert res["j1"]["volume"] == 150  # edge1 (100) + edge2 (50)
    assert res["j1"]["vol_secondary"] == 10  # edge3 (10)
    assert res["j1"]["avg_delay"] == 20.0  # edge3 waiting time (200) / edge3 vehicles (10)


def test_volume_warrant_mutcd_tables():
    from analysis.warrant_strategies import VolumeWarrant

    warrant = VolumeWarrant()

    # 1. 1 lane major, 1 lane minor, standard speed (13.89 m/s = 50 km/h)
    primary_edges = {
        "edge1": [{"density": 10.0, "mean_speed": 13.89, "num_lanes": 1, "speed_limit": 13.89}]
    }
    secondary_edges = {
        "edge2": [{"density": 5.0, "mean_speed": 13.89, "num_lanes": 1, "speed_limit": 13.89}]
    }

    # Volume = density * mean_speed * 3.6
    # Primary vol: 10 * 13.89 * 3.6 = 500.04 vph
    # Secondary vol: 5 * 13.89 * 3.6 = 250.02 vph
    # Expected threshold: 500 / 150 (Condition A) or 750 / 75 (Condition B)
    res = warrant.evaluate({}, primary_edges, secondary_edges, {})
    assert res["met"] is True
    assert res["threshold_primary"] == 500
    assert res["threshold_secondary"] == 150

    # 2. 2 lanes major, 2 lanes minor, standard speed
    primary_edges_2 = {
        "edge1": [{"density": 10.0, "mean_speed": 13.89, "num_lanes": 2, "speed_limit": 13.89}]
    }
    secondary_edges_2 = {
        "edge2": [{"density": 5.0, "mean_speed": 13.89, "num_lanes": 2, "speed_limit": 13.89}]
    }
    # Expected threshold: 600 / 200 (Condition A)
    res = warrant.evaluate({}, primary_edges_2, secondary_edges_2, {})
    assert res["threshold_primary"] == 600
    assert res["threshold_secondary"] == 200

    # 3. High speed limit (20 m/s > 19.44 m/s ≈ 72 km/h)
    primary_edges_high = {
        "edge1": [{"density": 10.0, "mean_speed": 20.0, "num_lanes": 1, "speed_limit": 20.0}]
    }
    secondary_edges_high = {
        "edge2": [{"density": 5.0, "mean_speed": 20.0, "num_lanes": 1, "speed_limit": 20.0}]
    }
    # Thresholds should be reduced by 70%
    # Condition A: 500 * 0.7 = 350, 150 * 0.7 = 105
    res = warrant.evaluate({}, primary_edges_high, secondary_edges_high, {})
    assert res["threshold_primary"] == 350
    assert res["threshold_secondary"] == 105




