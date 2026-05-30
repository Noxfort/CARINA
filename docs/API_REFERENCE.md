# 🔌 Synapse HFT Protocol & IPC Memory Queues

CARINA interfaces with the physical world via the **Synapse HFT Protocol** (gRPC). Internally, it manages its highly concurrent microservices via OS-level **Inter-Process Communication (IPC)** Queues.

## 1. Internal IPC Queues (`multiprocessing.Queue`)

Because CARINA is spread across 7 isolated OS processes (to bypass the Python GIL), they cannot share standard variables. Data is passed exclusively through these 7 primary queues initialized in `carina.py`:

| Queue Name | Source Process | Target Process | Payload Description |
|---|---|---|---|
| `wd` (Watchdog) | All Processes | `Watchdog` | Heartbeat JSONs (`{"process": "AI", "status": "ok"}`). |
| `sds` (Dashboard) | `AI_Process` | `DashboardService` | Moving averages, rewards, and real-time phase states for WebSockets. |
| `sas` (Analysis) | `DatabaseWorker` | `AnalysisService` | Batched historical states for offline engineering warrant analysis. |
| `ui` (Flet UI) | `DashboardService` | `carina.py (Main)` | Processed WebSocket events pushing state changes to the Flet rendering loop. |
| `db` (Database) | `AI_Process` | `DatabaseWorker` | Massive JSON strings containing `(state, action, reward, next_state)`. |
| `g_state` (Guardian) | `AI_Process` | `GuardianWorker` | The 8-second temporal tensor requiring safety validation. |
| `g_signal` (Guardian) | `GuardianWorker`| `AI_Process` | The strict Veto list returned after neural/symbolic inference. |

## 2. The `HFTLink` gRPC Service

Defined in `proto/synapse_hft.proto`, the `HFTLink` service provides four critical Remote Procedure Calls (RPCs):

### 2.1 `Ping (Empty) returns (SystemState)`
A heartbeat mechanism to ensure the physical controller is online and receptive.
- **Returns**: `SystemState` containing an `active` boolean, a `state` string, and the `server_time`.

### 2.2 `LoadScenario (ScenarioDefinition) returns (ScenarioStatus)`
Triggered during system initialization. CARINA sends the complete graph topology to the physical proxy or simulation.
- **Input (`ScenarioDefinition`)**: 
  - `map_hash` and `map_file_content` (bytes) for binary transfer.
  - `TopologyGraph` array detailing all physical `nodes` (intersections) and `edges` (lanes, speed limits).
  - `peak_schedule_json` representing pre-calculated offline traffic peak hours.
- **Returns**: `ScenarioStatus` boolean acceptance.

### 2.3 `SystemControl (ControlCommand) returns (CommandResponse)`
Issues state machine commands to the physical proxy (e.g., START, PAUSE, STOP, RESET).

### 2.4 `StreamTraffic (stream TrafficFrame) returns (SystemState)`
The core telemetry ingestion pipeline. This is a **unidirectional streaming RPC** where the physical proxy blasts high-frequency traffic frames to CARINA.
- **Input (`TrafficFrame`)**:
  - `timestamp` (double)
  - `sequence_id` (uint64)
  - A map of `EdgeState` objects keyed by `edge_id`.
- **`EdgeState` Metrics**:
  - `occupancy` (float): Lane utilization percentage (0.0 to 100.0).
  - `mean_speed` (float): Average velocity of vehicles (km/h).
  - `queue_length` (integer): Absolute number of stopped vehicles.
  - `density` (float): Vehicles per kilometer.
