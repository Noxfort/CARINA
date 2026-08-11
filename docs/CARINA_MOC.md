---
tags: [moc, hub, docs]
aliases: [CARINA MOC, Home, Index]
---

# 📚 CARINA Technical Master Documentation Hub

Welcome to the **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) technical documentation library. Designed as a massively concurrent, high-frequency Deep Reinforcement Learning ecosystem for real-time traffic light control, CARINA bridges high-level neuro-symbolic AI, real-time gRPC hardware actuation, and multi-process OS isolation.

This master documentation index provides deep technical coverage for core developers, academic researchers, and system integrators.

---

## 🗺️ Codebase Map & Directory Hierarchy

```text
CARINA_CORE/
├── carina.py                   # Master Orchestrator (SingleInstanceLock, ProcessManager, UI/Tray)
├── ARCHITECTURE.md             # 8-Process Multiprocessing Blueprint & IPC Topology
├── pyproject.toml              # Build toolchain & project metadata
├── requirements.txt            # Python dependencies (PyTorch, Flet, gRPC, Captum, etc.)
│
├── config/                     # Configuration Systems
│   └── settings.ini            # System-wide parameters (gRPC, DB, AI, XAI, MFD, Logging)
│
├── proto/                      # gRPC Protocol Specifications
│   └── synapse_hft.proto       # High-Frequency Telemetry & Actuation Protobuf Definitions
│
├── docs/                       # Comprehensive Documentation
│   ├── CARINA_MOC.md           # Master Documentation Hub (This File)
│   ├── API_REFERENCE.md        # Synapse HFT gRPC Protocol & IPC Queue Schema
│   ├── RESEARCH_NOTES.md       # PPO-TCN, PAE, GATv2 & DA SILVA Mathematical Formulations
│   ├── XAI_AND_SAS.md          # Explainable AI (Qwen3 LLM), SAS Analytics & MFD Engine
│   ├── UI_AND_DASHBOARD.md     # Flet Desktop Application, System Tray & SDS Architecture
│   ├── DEVELOPER_GUIDES.md     # Setup, Custom Agent Creation, PyInstaller & Settings
│   └── TESTING.md              # Pytest Suite, Safety Mocks & Coverage Validation
│
├── src/                        # Primary Source Code
│   ├── agents/                 # PPO-TCN, Dueling DQN, Guardian & Strategic Agents
│   ├── analysis/               # Traffic metrics, flow aggregation & queue metrics
│   ├── central_controller.py   # High-Frequency gRPC Telemetry Server
│   ├── database/               # Async Database Worker (SQLite / PostgreSQL)
│   ├── engine/                 # EpisodeRunner, DecisionCoordinator & LearningCoordinator
│   ├── launcher/               # ProcessManager, SingleInstanceLock & UI Tray Manager
│   ├── mfd/                    # Macroscopic Fundamental Diagram Analysis Worker
│   ├── models/                 # Neural architectures (PAE, TCN, GATv2, Head networks)
│   ├── safety/                 # Symbolic Veto Firewall & SafetyAuditor
│   ├── sas/                    # Smart Analysis System (Offline Infrastructure Warrants)
│   ├── sds/                    # Smart Dashboard Service (Flet UI bridge)
│   ├── slm/                    # Local LLM Interface (Qwen3 1.7B integration)
│   ├── watchdog/               # Real-time process heartbeat monitor & fail-safe fallback
│   └── xai/                    # Captum Integrated Gradients & XAI Report Generator
│
├── ui/                         # Flet UI Views, Components, Theme & Assets
└── tests/                      # Pytest Test Suite (Unit, Integration & Mocks)
```

---

## 📖 System Dimension & Core Modules

### 1. Core Infrastructure & Process Engineering
- **[Architecture Deep-Dive](../ARCHITECTURE.md)**: Exhaustive technical blueprint detailing all 8 concurrent OS microservices, process isolation via `multiprocessing`, IPC Pipe/Queue channels, and the `EpisodeRunner` execution loop.
- **[API Reference & HFT Protocol](API_REFERENCE.md)**: Complete specifications for the `Synapse HFT` gRPC interface, Protobuf message schemas, Prometheus metric endpoints (port 8001), and IPC queue schemas.

### 2. Artificial Intelligence & Neuro-Symbolic Safety
- **[Neural Research & Formulations](RESEARCH_NOTES.md)**: Deep mathematical formulations for PPO-TCN, Predictive Autoencoder (PAE) latent projection $Z$, Dueling DQN-TCN value/advantage streams, GATv2 Lite Graph Attention, and the DA SILVA maturation curriculum.
- **[Explainable AI, SAS & MFD Analytics](XAI_AND_SAS.md)**: Operational details of the `XAI_Worker` (Captum Integrated Gradients + Qwen3 1.7B LLM), the `AnalysisService` (PostgreSQL offline analytics), and the `MFD_Worker` (Macroscopic Fundamental Diagram capacity estimation).

### 3. Desktop Application & Monitoring
- **[UI & Smart Dashboard Service](UI_AND_DASHBOARD.md)**: Architectural breakdown of the native `Flet` desktop UI, system tray integration, single instance socket locking (port 42123), live telemetry charts, and incident filtering.

### 4. Developer Operations & Quality Assurance
- **[Developer & Integration Guides](DEVELOPER_GUIDES.md)**: Complete guide for setting up environments, modifying `config/settings.ini`, extending custom agents, writing database migrations, and building frozen executables (`carina.spec`).
- **[Testing & Validation](TESTING.md)**: Guidelines for executing `pytest`, generating coverage reports (`--cov=src`), mocking gRPC telemetry, and testing Guardian safety vetoes.

---

> 💡 **Obsidian Knowledge Graph:** This documentation suite maintains full native support for [Obsidian](https://obsidian.md/). Open `CARINA_CORE` as an Obsidian Vault to navigate the interactive technical graph.
