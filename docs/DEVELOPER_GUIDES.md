# 🛠️ Developer & System Integration Guide

CARINA is designed as an extensible enterprise framework. This guide details how to extend the system, handle multiprocessing, and prepare binaries.

## 1. Creating and Registering Custom Neural Agents

Because CARINA relies on the `DecisionCoordinator` to invoke agents, you can inject entirely new RL algorithms seamlessly.

### Step 1.1: Implement the Abstract Interface
Create a new file in `src/agents/custom_agent.py`.
```python
from src.agents.base_agent import BaseAgent
import torch

class CustomSACAgent(BaseAgent):
    def __init__(self, config):
        super().__init__(config)
        self.actor = ...
        self.critic = ...

    def act(self, state_tensor: torch.Tensor) -> int:
        return action
        
    def update(self, batch):
        pass
```

### Step 1.2: Update Configuration
Modify `config/settings.ini` to point to your new class:
```ini
[AGENT]
model_type = SAC_CUSTOM
```
The `PopulationManager` will automatically spawn your new agent architecture during initialization.

---

## 2. Modifying the Safety Rules (Guardian Agent)

The `GuardianAgent` enforces deterministic safety rules before allowing neural inference.

1. Navigate to `src/agents/guardian_agent.py`.
2. Locate the `select_action` method.
3. Add a new rule (e.g., Pedestrian Priority) using the `context` dictionary:
```python
pedestrian_waiting = context.get('pedestrian_waiting', False)
if pedestrian_waiting and 'G' in current_phase_state:
    return self.ACTION_CHANGE_PHASE, "Pedestrian Priority Override"
```

---

## 3. Database Migration: Moving to PostgreSQL

By default, the `DatabaseWorker` mounts a lightweight `SQLite3` engine. For production deployments with multiple physical intersections, PostgreSQL is mandatory.

1. Ensure bindings are installed: `pip install psycopg2-binary`
2. Open `config/settings.ini`.
3. Locate the `[DATABASE]` block and adjust parameters:
```ini
[DATABASE]
driver = postgresql
host = 192.168.1.100
port = 5432
user = carina_admin
password = your_secure_password
dbname = carina_telemetry
```
4. Restart the application. The `DatabaseWorker` will automatically mount the SQLAlchemy connection pool to your Postgres cluster.

---

## 4. Frozen Packaging (`PyInstaller`)

CARINA detects if it is running as a compiled binary using the `IS_FROZEN` flag inside `carina.py`.

```python
IS_FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
```

If you compile CARINA using `pyinstaller`, it will automatically remap the `sys.path` to the `_MEIPASS` temporary extraction directory to ensure the massive `Qwen3` LLM and `Flet` UI assets load correctly without crashing the 7 concurrent worker processes.
