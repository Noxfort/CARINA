# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems

import sqlite3
import pytest
from unittest.mock import MagicMock
from repositories.fluid_dynamics_repo import FluidDynamicsRepository
from sas.analyzer_data_processor import AnalyzerDataProcessor

class MockDbEngine:
    def __init__(self):
        self.db_type = "sqlite"
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_sqlite()

    def _init_sqlite(self):
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synapse_fluid_dynamics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edge_id TEXT NOT NULL,
                density REAL,
                mean_speed REAL,
                queue_length REAL,
                occupancy REAL,
                edge_length REAL,
                num_lanes INTEGER,
                speed_limit REAL,
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Insert test traffic samples for edge_A and edge_B
        cursor.execute("""
            INSERT INTO synapse_fluid_dynamics (edge_id, density, mean_speed, queue_length, occupancy, edge_length, num_lanes, speed_limit, collected_at)
            VALUES 
            ('edge_A', 10.0, 10.0, 5, 0.2, 100.0, 2, 13.89, '2026-08-01 06:00:00'),
            ('edge_A', 15.0, 8.0, 8, 0.3, 100.0, 2, 13.89, '2026-08-01 06:30:00'),
            ('edge_B', 5.0, 12.0, 2, 0.1, 150.0, 1, 13.89, '2026-08-01 07:00:00');
        """)
        self._conn.commit()

    def get_connection(self):
        return self._conn


def test_fluid_dynamics_repo_pushdown_aggregation():
    engine = MockDbEngine()
    lm = MagicMock()
    repo = FluidDynamicsRepository(engine, lm)
    
    results = repo.query_aggregated_fluid_dynamics(limit_seconds=3600)
    assert len(results) == 3 or len(results) == 2
    
    edge_map = {row['edge_id']: row for row in results}
    assert 'edge_A' in edge_map
    assert 'edge_B' in edge_map


def test_fluid_dynamics_min_max_timestamps():
    engine = MockDbEngine()
    lm = MagicMock()
    repo = FluidDynamicsRepository(engine, lm)
    
    min_dt, max_dt = repo.get_fluid_dynamics_min_max_timestamps()
    assert min_dt is not None
    assert max_dt is not None
    assert min_dt.strftime("%Y-%m-%d %H:%M:%S") == "2026-08-01 06:00:00"
    assert max_dt.strftime("%Y-%m-%d %H:%M:%S") == "2026-08-01 07:00:00"


def test_analyzer_data_processor_with_pushdown():
    engine = MockDbEngine()
    lm = MagicMock()
    
    class MockDbManager:
        def __init__(self):
            self.fluid_dynamics_repo = FluidDynamicsRepository(engine, lm)
        def query_aggregated_fluid_dynamics(self, limit_seconds=None):
            return self.fluid_dynamics_repo.query_aggregated_fluid_dynamics(limit_seconds)
        def query_fluid_dynamics_history_batches(self, limit_seconds=None, batch_size=50000):
            return self.fluid_dynamics_repo.query_fluid_dynamics_history_batches(limit_seconds, batch_size)

    mock_topology = MagicMock()
    mock_topology.build.return_value = (
        {'junction1': 'traffic_light'},
        {'junction1': {'edge_A': {'num_lanes': 2}, 'edge_B': {'num_lanes': 1}}}
    )
    
    processor = AnalyzerDataProcessor(locale_manager=lm, topology_parser=mock_topology)
    
    processed_data, true_tls = processor.process_historical_data(MockDbManager(), "mock_net.xml", limit_seconds=3600)
    
    assert true_tls == ['junction1']
    assert 'junction1' in processed_data
    assert len(processed_data['junction1']['primary_edges']) > 0
