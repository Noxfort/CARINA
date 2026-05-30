# 📚 CARINA Ultimate Documentation Hub

Welcome to the **CARINA** technical documentation library. Because of the sheer scale and complexity of this AI ecosystem—spanning from deep reinforcement learning and neuro-symbolic safety to real-time high-frequency gRPC telemetry, Flet UI architectures, and massive multiprocessing orchestration—this library serves as the ultimate source of truth for developers, academic researchers, and enterprise integrators.

## 📖 The Complete Dimension of the System

### 1. The Core Infrastructure
- **[Architecture Deep-Dive](../ARCHITECTURE.md)**: Exhaustive breakdown of the 7 concurrent OS processes, the `EpisodeRunner` pipeline, the GOMES multi-agent system, and the DA SILVA maturation curriculum.
- **[API Reference & HFT Protocol](API_REFERENCE.md)**: Specifications for the `Synapse HFT` gRPC definitions. Details the exact Protobuf messages and the internal IPC (Inter-Process Communication) queues that wire the system together.

### 2. Artificial Intelligence Subsystems
- **[Neural Research & Formulations](RESEARCH_NOTES.md)**: Deep dive into the custom AI models driving the intelligence (PPO-TCN, Predictive Autoencoder (PAE) latent space projection, and Dueling DQN-TCN stream splitting).
- **[Explainable AI & Infrastructure Analytics](XAI_AND_SAS.md)**: Understanding how the system translates math to human logic using the `Captum` library and `Qwen3` LLM, and how the Smart Analysis System generates engineering warrants.

### 3. Frontend & Dashboarding
- **[UI & Smart Dashboard Service](UI_AND_DASHBOARD.md)**: Architectural layout of the native `Flet` desktop application, System Tray handlers, and the WebSocket servers streaming telemetry at sub-second latencies.

### 4. Codebase Extension & Manipulation
- **[Developer & Integration Guides](DEVELOPER_GUIDES.md)**: Practical, step-by-step guides for modifying the core, handling `PyInstaller` frozen state builds, hooking into IPC queues, and migrating database schemas.
- **[Testing & Validation](TESTING.md)**: Instructions for running the `pytest` suite, generating coverage reports, and writing mocks for safety-critical Guardian modules.
