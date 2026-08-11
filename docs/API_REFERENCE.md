---
tags: [api, grpc, ipc, reference]
aliases: [API Reference, Synapse HFT, IPC Queues]
---

# ⚡ API Reference & Synapse HFT Protocol Specifications

This document serves as the authoritative interface specification for CARINA. It covers the **Synapse HFT gRPC Protocol**, the **Prometheus Exporter Metrics**, and the **Inter-Process Communication (IPC) Schemas**.

⬅️ Back to [Main Documentation Hub](CARINA_DOC.md) or [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Synapse HFT gRPC Service Definition (`synapse_hft.proto`)

CARINA interfaces with physical traffic controllers, simulation environments (SUMO/CityFlow), and external sensors via the **Synapse HFT Protocol** over gRPC.

- **Default Port:** `50051` (Configurable in `config/settings.ini`)
- **Transport:** HTTP/2 over TCP with optional TLS encryption.
- **Protocol Package:** `synapse.hft`

```protobuf
syntax = "proto3";
package synapse.hft;

service HFTLink {
  rpc Ping (Empty) returns (SystemState);
  rpc LoadScenario (ScenarioDefinition) returns (ScenarioStatus);
  rpc SystemControl (ControlCommand) returns (CommandResponse);
  rpc StreamTraffic (stream TrafficFrame) returns (SystemState);
}
```

### 1.1 gRPC RPC Methods Breakdown

#### `Ping`
- **Request:** `Empty`
- **Response:** `SystemState` (returns server status, active boolean flag, and UTC epoch timestamp `server_time`).
- **Latency Target:** $< 1\text{ ms}$

#### `LoadScenario`
- **Request:** `ScenarioDefinition` (transfers binary map geometry `.net.xml.gz`, topology nodes/edges, and peak schedule JSON extracted by the ADAGIO classifier).
- **Response:** `ScenarioStatus` (`accepted` boolean and status message).

#### `SystemControl`
- **Request:** `ControlCommand` (Enum action: `START`, `PAUSE`, `STOP`, `RESET`).
- **Response:** `CommandResponse` (`success` boolean and `new_state` string).

#### `StreamTraffic`
- **Request:** `stream TrafficFrame` (High-frequency streaming of edge occupancy, vehicle speeds, queue lengths, and densities).
- **Response:** `SystemState`

---

## 2. Telemetry & Control Message Schemas

### 2.1 `TrafficFrame`
```protobuf
message TrafficFrame {
  double timestamp = 1;
  uint64 sequence_id = 2;
  map<string, EdgeState> edges = 3;
}

message EdgeState {
  float occupancy = 1;      // Ratio [0.0 - 1.0] of road occupancy
  float mean_speed = 2;     // Space-mean speed in m/s
  int32 queue_length = 3;   // Number of stopped vehicles in queue
  float density = 4;        // Vehicles per kilometer
}
```

### 2.2 `ScenarioDefinition`
```protobuf
message ScenarioDefinition {
  string map_hash = 1;
  TopologyGraph graph = 2;
  MapGeometry geometry = 3;
  bytes map_file_content = 4;
  string map_file_name = 5;
  string peak_schedule_json = 6;
}
```

---

## 3. Inter-Process Communication (IPC) Queue Specifications

CARINA manages 10 bounded IPC channels created by `ProcessManager`.

| Queue Name | Max Size | Producer Process | Consumer Process | Payload Schema / Message Type |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn`** | Pipe | `CentralController` | `AI_Process` | `("state", frame_id, traffic_frame_dict)` |
| **`ai_conn`** | Pipe | `AI_Process` | `CentralController` | `("actuation", frame_id, signal_group_actions)` |
| **`wd`** | 500 | All Microservices | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`sds`** | 500 | `CentralController` | `DashboardService` | `{"timestamp": float, "telemetry": dict, "active_phase": int}` |
| **`sas`** | 500 | `CentralController` | `AnalysisService` | Historical traffic metrics for PostgreSQL aggregation |
| **`ui`** | 500 | `DashboardService` | `UITrayManager` | UI state updates, system tray notifications & log events |
| **`db`** | 500 | `AI_Process` | `DatabaseWorker` | `(state_tensor, action_int, reward_float, next_state_tensor)` |
| **`g_state`** | 500 | `AI_Process` | `GuardianWorker` | `(lane_queues, pae_latent_vector_z, strategic_gat_vector)` |
| **`g_signal`** | 500 | `GuardianWorker` | `AI_Process` | `{"veto": bool, "forced_phase": int, "risk_score": float}` |
| **`sas_results`** | 10 | `AnalysisService` | `CentralController` | Engineering warrant reports & signal timing recommendations |
| **`mfd_trigger`** | 10 | `CentralController` | `MFD_Worker` | `{"action": "COMPUTE_MFD", "time_window_seconds": 3600}` |
| **`mfd_results`** | 10 | `MFD_Worker` | `CentralController` | `{"critical_density": float, "max_capacity_flow": float, "curve": list}` |

---

## 4. Prometheus Exporter Metrics

The `MetricsManager` exposes real-time operational telemetry on **HTTP port 8001** (path `/metrics`).

```text
# Prometheus Metric Summary:
carina_step_latency_seconds_bucket{le="0.005"}   # gRPC telemetry to actuation latency histogram
carina_ppo_reward_total                          # Cumulative reward for PPO Tactical Agent
carina_guardian_veto_total{type="symbolic"}      # Counter of symbolic safety vetoes
carina_guardian_veto_total{type="neural"}        # Counter of PAE neural spillback vetoes
carina_mfd_network_density_veh_km               # Macroscopic network density
carina_mfd_network_flow_veh_hr                   # Macroscopic network throughput
carina_active_processes_count                    # Count of alive backend microservices
```
