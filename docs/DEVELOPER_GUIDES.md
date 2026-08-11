---
tags: [developer, guide, setup, pyinstaller, config]
aliases: [Developer Guides, Configuration Reference, PyInstaller Build]
---

# 🛠️ Developer & Integration Guides

This document provides step-by-step developer guides for configuring, extending, and building the CARINA ecosystem.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Complete `config/settings.ini` Parameter Reference

The central configuration file is located at `config/settings.ini`.

```ini
[SERVER]
# gRPC High-Frequency Telemetry Server Port
grpc_port = 50051
grpc_max_workers = 10
enable_tls = false

[DATABASE]
# Database backend: 'postgresql' or 'sqlite'
db_type = postgresql
db_host = localhost
db_port = 5432
db_name = carina_db
db_user = carina_user
db_password = secret_password
pool_size = 20

[AI]
# Reinforcement Learning Engine Parameters
device = cuda
learning_rate = 0.0003
gamma = 0.99
gae_lambda = 0.95
ppo_clip = 0.2
batch_size = 64
temporal_context_window = 8
spillback_risk_threshold = 0.80

[XAI]
# Explainable AI & Local LLM Configuration
enable_xai = true
model_name = Qwen/Qwen3-1.7B-Instruct
vram_allocation_gb = 4.0

[MFD]
# Macroscopic Fundamental Diagram Analysis
mfd_time_window_seconds = 3600
critical_density_threshold = 45.0

[PROMETHEUS]
# Metrics Exporter Port
metrics_port = 8001
enable_metrics = true
```

---

## 2. Creating a Custom Reinforcement Learning Agent

To register a new agent (e.g., `CustomSACAgent`):

1. Create your agent class in `src/agents/custom_sac_agent.py` inheriting from `BaseAgent`:

```python
from agents.base_agent import BaseAgent
import torch

class CustomSACAgent(BaseAgent):
    def __init__(self, state_dim: int, action_dim: int, config: dict):
        super().__init__(state_dim, action_dim, config)
        # Initialize actor/critic networks here

    def select_action(self, state_tensor: torch.Tensor, explore: bool = True) -> int:
        # Return discrete phase action index
        pass

    def update(self, replay_buffer) -> dict:
        # Perform backpropagation update step
        return {"actor_loss": 0.0, "critic_loss": 0.0}
```

2. Register your agent in `src/engine/decision_coordinator.py`:

```python
from agents.custom_sac_agent import CustomSACAgent

def get_agent_instance(agent_type: str, state_dim: int, action_dim: int, config: dict):
    if agent_type == "SAC":
        return CustomSACAgent(state_dim, action_dim, config)
    # ...
```

3. Update `config/settings.ini`:
```ini
[AI]
agent_type = SAC
```

---

## 3. Building Standalone Executables with PyInstaller

CARINA supports frozen binary distribution via PyInstaller for Linux and Windows.

### 3.1 Main Application Executable (`carina.spec`)
To build the primary `carina` executable bundle:

```bash
# Clean previous build artifacts
rm -rf dist/ build/

# Run PyInstaller build spec
pyinstaller carina.spec --noconfirm
```

The resulting standalone executable bundle will be generated in `dist/carina/`.

### 3.2 Patch Utility Executable (`apply_patch.spec`)
For deploying zero-downtime micro-updates:

```bash
pyinstaller apply_patch.spec --noconfirm
```

---

## 4. Environment & Sys.Path Handling in Frozen Mode

When running in PyInstaller frozen mode (`sys.frozen = True`), CARINA uses `src/launcher/env_setup.py` to resolve resource paths dynamically:

```python
import sys
import os

def setup_environment():
    if getattr(sys, 'frozen', False):
        bundle_root = sys._MEIPASS
        project_root = os.path.dirname(sys.executable)
    else:
        project_root = os.path.abspath(os.path.dirname(__file__))
        bundle_root = project_root

    sys.path.insert(0, project_root)
    return project_root, bundle_root, getattr(sys, 'frozen', False)
```
