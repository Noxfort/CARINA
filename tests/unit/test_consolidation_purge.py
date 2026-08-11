# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems

import sqlite3
import pytest
from unittest.mock import MagicMock
from repositories.fluid_dynamics_repo import FluidDynamicsRepository

class ProxyConnection:
    def __init__(self, conn):
        self._conn = conn
    def cursor(self):
        return self._conn.cursor()
    def commit(self):
        return self._conn.commit()
    def rollback(self):
        return self._conn.rollback()
    def close(self):
        pass

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
                scenario_name TEXT DEFAULT 'default',
                intersection_id TEXT,
                edge_id TEXT NOT NULL,
                density REAL NOT NULL,
                mean_speed REAL NOT NULL,
                min_speed REAL,
                queue_length INTEGER NOT NULL,
                max_queue INTEGER,
                occupancy REAL NOT NULL,
                edge_length REAL,
                num_lanes INTEGER,
                speed_limit REAL,
                maturity_stage TEXT NOT NULL DEFAULT 'CHILD',
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synapse_edge_phase_hourly_summary (
                edge_id TEXT NOT NULL,
                maturity_stage TEXT NOT NULL,
                summary_hour TIMESTAMP NOT NULL,
                scenario_name TEXT NOT NULL DEFAULT 'default',
                sample_count INTEGER NOT NULL,
                avg_speed REAL NOT NULL,
                min_speed REAL NOT NULL,
                avg_density REAL NOT NULL,
                avg_queue REAL NOT NULL,
                max_queue REAL NOT NULL,
                total_production REAL NOT NULL,
                avg_occupancy REAL NOT NULL,
                PRIMARY KEY (edge_id, maturity_stage, summary_hour)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synapse_intersection_phase_hourly_summary (
                intersection_id TEXT NOT NULL,
                maturity_stage TEXT NOT NULL,
                summary_hour TIMESTAMP NOT NULL,
                scenario_name TEXT NOT NULL DEFAULT 'default',
                sample_count INTEGER NOT NULL,
                avg_speed REAL NOT NULL,
                min_speed REAL NOT NULL,
                avg_queue REAL NOT NULL,
                max_queue REAL NOT NULL,
                total_production REAL NOT NULL,
                total_delay REAL NOT NULL,
                PRIMARY KEY (intersection_id, maturity_stage, summary_hour)
            );
        """)
        # Insert samples: one old sample (>48h ago) and one recent sample
        cursor.execute("""
            INSERT INTO synapse_fluid_dynamics 
            (scenario_name, intersection_id, edge_id, density, mean_speed, queue_length, occupancy, edge_length, maturity_stage, collected_at)
            VALUES 
            ('default', 'int_1', 'edge_old', 50.0, 30.0, 10, 0.4, 100.0, 'CHILD', datetime('now', '-50 hours')),
            ('default', 'int_1', 'edge_new', 20.0, 50.0, 2, 0.1, 100.0, 'CHILD', datetime('now', '-1 hours'));
        """)
        self._conn.commit()

    def get_connection(self):
        return ProxyConnection(self._conn)

def test_consolidate_and_purge_old_data():
    engine = MockDbEngine()
    lm = MagicMock()
    repo = FluidDynamicsRepository(engine, lm)

    # Before consolidation: 2 raw rows, 0 summary rows
    conn = engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM synapse_fluid_dynamics;")
    assert cursor.fetchone()[0] == 2

    # Execute consolidation (keep_hours=48)
    repo.consolidate_and_purge_old_data(keep_hours=48)

    # After consolidation: 1 raw row remaining (edge_new), 1 summary row created (edge_old)
    cursor.execute("SELECT count(*) FROM synapse_fluid_dynamics;")
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT edge_id FROM synapse_fluid_dynamics;")
    assert cursor.fetchone()[0] == 'edge_new'

    cursor.execute("SELECT edge_id, sample_count, avg_speed FROM synapse_edge_phase_hourly_summary;")
    summary_edge = cursor.fetchone()
    assert summary_edge[0] == 'edge_old'
    assert summary_edge[1] == 1
    assert summary_edge[2] == 30.0

    cursor.execute("SELECT intersection_id, sample_count FROM synapse_intersection_phase_hourly_summary;")
    summary_int = cursor.fetchone()
    assert summary_int[0] == 'int_1'
    assert summary_int[1] == 1
