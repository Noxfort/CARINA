---
tags: [database, postgresql, sqlite, schema, persistence]
aliases: [Database Architecture, Relational Schemas, Persistence]
---

# 🗄️ Database Architecture & Relational Schemas

This document details CARINA's persistence tier, connection pooling, asynchronous batch writing (`DatabaseWorker`), and table schemas for PostgreSQL and SQLite.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Asynchronous Database Architecture (`DatabaseWorker`)

To prevent synchronous SQL `INSERT` commands from blocking the real-time AI decision loop, CARINA routes all database write operations through an isolated OS worker process: `DatabaseWorker` (`run_database_worker`).

```text
AI_Process ──> [db Queue maxsize=500] ──> DatabaseWorker ──> Batch Buffer (50 records) ──> PostgreSQL / SQLite
```

- **Batch Size:** 50 records or max flush timeout of 1.0 second.
- **Failover:** Defaults to SQLite (`carina_local.db`) if connection to PostgreSQL fails.

---

## 2. Relational Database Schemas

### 2.1 Table: `traffic_metrics`
Stores high-frequency sensor readings per intersection lane.

```sql
CREATE TABLE IF NOT EXISTS traffic_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp DOUBLE PRECISION NOT NULL,
    edge_id VARCHAR(64) NOT NULL,
    occupancy REAL NOT NULL,
    mean_speed REAL NOT NULL,
    queue_length INT NOT NULL,
    density REAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_edge_time ON traffic_metrics (edge_id, timestamp);
```

### 2.2 Table: `episode_rewards`
Tracks Reinforcement Learning trajectories and policy updates.

```sql
CREATE TABLE IF NOT EXISTS episode_rewards (
    id BIGSERIAL PRIMARY KEY,
    episode_id INT NOT NULL,
    step_number INT NOT NULL,
    state_tensor JSONB NOT NULL,
    action_taken INT NOT NULL,
    reward_value REAL NOT NULL,
    policy_entropy REAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Table: `guardian_vetoes`
Audit log of all Symbolic and Neural safety overrides executed by the Guardian Agent.

```sql
CREATE TABLE IF NOT EXISTS guardian_vetoes (
    id BIGSERIAL PRIMARY KEY,
    timestamp DOUBLE PRECISION NOT NULL,
    intersection_id VARCHAR(64) NOT NULL,
    veto_type VARCHAR(32) NOT NULL, -- 'SYMBOLIC' or 'NEURAL'
    proposed_phase INT NOT NULL,
    forced_phase INT NOT NULL,
    risk_score REAL NOT NULL,
    reason TEXT NOT NULL
);
```
