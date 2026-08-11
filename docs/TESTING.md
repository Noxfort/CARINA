---
tags: [testing, pytest, coverage, mocks, safety]
aliases: [Testing Guidelines, Unit Testing, Safety Mocks]
---

# 🧪 Testing & Validation Guidelines

CARINA governs safety-critical traffic light hardware. Absolute reliability, deterministic unit testing, and continuous safety veto validation are mandatory before deploying code changes.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Running the Test Suite (`pytest`)

All tests are located in `tests/`.

### 1.1 Execute All Unit & Integration Tests
```bash
pytest tests/ -v
```

### 1.2 Generate Test Coverage Reports
To measure statement and branch coverage across `src/`:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
The HTML coverage report will be generated in `htmlcov/index.html`.

---

## 2. Test Architecture & Directory Structure

```text
tests/
├── unit/
│   ├── test_ppo_tcn.py         # Unit tests for PPO-TCN tensor shapes & loss functions
│   ├── test_pae_model.py       # Tests for Predictive Autoencoder latent projection Z
│   ├── test_guardian_veto.py   # Unit tests for symbolic and neural safety vetoes
│   └── test_ipc_queues.py      # Multiprocessing Queue serialization tests
├── integration/
│   ├── test_grpc_stream.py     # End-to-end gRPC telemetry & actuation loop
│   └── test_database_worker.py # Database bulk insert queue handling
└── mocks/
    ├── mock_traffic_gen.py     # Synthetic TrafficFrame generator for test benchmarks
    └── mock_hardware_ctrl.py   # Mock traffic light hardware controller
```

---

## 3. Writing Mock Tests for Guardian Safety Vetoes

Every new action or phase transition must be validated against the `SafetyAuditor`.

Example unit test (`tests/unit/test_guardian_veto.py`):

```python
import pytest
import torch
from safety.safety_auditor import SafetyAuditor

def test_symbolic_min_green_veto():
    auditor = SafetyAuditor(min_green_time_seconds=7.0)
    
    # Simulate current state where Phase 1 has been active for only 3 seconds
    current_state = {"active_phase": 1, "phase_duration_seconds": 3.0}
    proposed_action = 2  # Attempting to switch to Phase 2 prematurely
    
    # Audit action
    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)
    
    assert is_vetoed is True
    assert authorized_action == 1  # Forced to keep current Phase 1
    assert "Minimum Green Time" in reason
```
