---
tags: [moc, hub, docs]
aliases: [CARINA MOC, Home, Index]
---
# 📚 CARINA Ultimate Documentation Hub

Welcome to the **CARINA** technical documentation library. Because of the sheer scale and complexity of this AI ecosystem—spanning from deep reinforcement learning and neuro-symbolic safety to real-time high-frequency gRPC telemetry, Flet UI architectures, and massive multiprocessing orchestration—this library serves as the ultimate source of truth for developers, academic researchers, and enterprise integrators.

## 📖 The Complete Dimension of the System

### 1. The Core Infrastructure
- **[[ARCHITECTURE|Architecture Deep-Dive]]**: Exhaustive breakdown of the 7 concurrent OS processes, the `EpisodeRunner` pipeline, the GOMES multi-agent system, and the DA SILVA maturation curriculum.
- **[[API_REFERENCE|API Reference & HFT Protocol]]**: Specifications for the `Synapse HFT` gRPC definitions. Details the exact Protobuf messages and the internal IPC (Inter-Process Communication) queues that wire the system together.

### 2. Artificial Intelligence Subsystems
- **[[RESEARCH_NOTES|Neural Research & Formulations]]**: Deep dive into the custom AI models driving the intelligence (PPO-TCN, Predictive Autoencoder (PAE) latent space projection, and Dueling DQN-TCN stream splitting).
- **[[XAI_AND_SAS|Explainable AI & Infrastructure Analytics]]**: Understanding how the system translates math to human logic using the `Captum` library and `Qwen3` LLM, and how the Smart Analysis System generates engineering warrants.

### 3. Frontend & Dashboarding
- **[[UI_AND_DASHBOARD|UI & Smart Dashboard Service]]**: Architectural layout of the native `Flet` desktop application, System Tray handlers, and the WebSocket servers streaming telemetry at sub-second latencies.

### 4. Codebase Extension & Manipulation
- **[[DEVELOPER_GUIDES|Developer & Integration Guides]]**: Practical, step-by-step guides for modifying the core, handling `PyInstaller` frozen state builds, hooking into IPC queues, and migrating database schemas.
- **[[TESTING|Testing & Validation]]**: Instructions for running the `pytest` suite, generating coverage reports, and writing mocks for safety-critical Guardian modules.
