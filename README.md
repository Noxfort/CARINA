---
tags: [readme, home, carina]
aliases: [Projeto CARINA, Root]
---

# 🚗 CARINA: Cognitive Autonomous Real-time Intersection Network Architecture

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge&logo=github" alt="Status" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/Flet-UI-00D2B4?style=for-the-badge&logo=flutter&logoColor=white" alt="Flet UI" />
  <img src="https://img.shields.io/badge/gRPC-HFT-2DA6B0?style=for-the-badge&logo=grpc&logoColor=white" alt="gRPC" />
  <img src="https://img.shields.io/badge/License-AGPL_v3-blue?style=for-the-badge" alt="License" />
</p>

<p align="center">
  <a href="https://github.com/Noxfort/CARINA">
    <img src="https://github-readme-stats.vercel.app/api/pin/?username=Noxfort&repo=CARINA&theme=dark" alt="CARINA GitHub Repository Card" />
  </a>
</p>

**CARINA** is a massively distributed Deep Reinforcement Learning ecosystem designed for real-time traffic control and smart city orchestration. Bypassing Python's Global Interpreter Lock (GIL) via 7 concurrent OS processes, it integrates a Tactical PPO agent and a Guardian Agent (Dueling DQN-TCN + Predictive Autoencoder) to provide neuro-symbolic safety. CARINA learns online directly in production via the sub-millisecond Synapse HFT protocol.

---

## 📚 Documentation Hub & Knowledge Vault

Explore the full architecture, internal mechanics, and developer guides for the CARINA ecosystem:

| Card / Subsystem | Focus Area | Direct Link |
| :--- | :--- | :---: |
| 📚 **Documentation Hub** | Central Index & Navigation for all technical docs | [Explore Hub](docs/CARINA_MOC.md) |
| 🏛️ **Core Architecture** | 7 Concurrent OS processes, GOMES & DA SILVA curriculum | [View Blueprint](ARCHITECTURE.md) |
| ⚡ **Synapse HFT API** | Sub-millisecond gRPC telemetry & Protobuf IPC specifications | [View API Reference](docs/API_REFERENCE.md) |
| 🧠 **Neural Formulations** | PPO-TCN, Dueling DQN-TCN & Predictive Autoencoder (PAE) | [View Research](docs/RESEARCH_NOTES.md) |
| 🔍 **Explainable AI (XAI)** | Captum Integrated Gradients & Qwen3 LLM engineering reports | [View XAI & SAS](docs/XAI_AND_SAS.md) |
| 🖥️ **Flet Dashboard** | Native desktop UI running in an isolated process | [View UI Guide](docs/UI_AND_DASHBOARD.md) |
| 🛠️ **Developer Guides** | Schema migrations, PyInstaller builds, IPC queues | [View Guides](docs/DEVELOPER_GUIDES.md) |
| 🧪 **Testing & Validation** | Pytest suite, coverage reports & Guardian safety mocks | [View Guidelines](docs/TESTING.md) |

> 💡 **Obsidian Vault Support:** This repository is also fully compatible with [Obsidian](https://obsidian.md/). Open this root folder as a vault and navigate from `CARINA_MOC.md`.

---

## ⚡ Core Architecture (GOMES & DA SILVA)

CARINA relies on the **Graph-based Operational Multi-agent Expert System (GOMES)** to handle complex intersections, governed by the **DA SILVA** statistical maturation curriculum.

- **Tactical Layer (PPO-TCN):** Hyper-focused on local intersection throughput using Temporal Convolutional Networks to eliminate BPTT explosion.
- **Strategic Layer (GATv2 Lite):** Coordinates "Green Waves" using Graph Attention Networks to prioritize massive avenues.
- **Guardian Layer (Neuro-Symbolic):** A background firewall that instantaneously vetoes any action violating strict physical safety constraints.
- **Explainable AI (XAI):** A massive `Qwen3 1.7B` LLM process coupled with `Captum` Integrated Gradients to generate natural-language engineering reports explaining neural reasoning.

*See the full breakdown in the [System Blueprint](ARCHITECTURE.md)*

---

## 🛠️ Key Features

- **Synapse HFT Protocol:** High-frequency, bidirectional gRPC telemetry capable of sub-millisecond physical actuation. (See [API Reference](docs/API_REFERENCE.md))
- **Decoupled Flet Frontend:** A beautiful, responsive desktop Dashboard Service (SDS) that runs completely isolated from the AI inference loop. (See [UI & Dashboard](docs/UI_AND_DASHBOARD.md))
- **Smart Analysis System (SAS):** Offline background process that analyzes historical PostgreSQL data to suggest infrastructure modifications. (See [XAI & SAS](docs/XAI_AND_SAS.md))
- **Process Watchdog:** Deterministic fail-safes that automatically revert physical intersections to hardcoded states if the neural engines hang.

---

## 🚀 Quick Start

### 1. Requirements
Ensure you have Python 3.10+ and a CUDA-compatible GPU (highly recommended for the XAI Worker).

### 2. Installation
Install the necessary dependencies from the requirements file:
```bash
pip install -r requirements.txt
```

### 3. Database Setup (Optional but Recommended)
By default, CARINA falls back to SQLite, but for full feature support (SAS and offline training data), set up your `config/settings.ini` to connect to PostgreSQL.
*(Refer to [Developer Integration Guide](docs/DEVELOPER_GUIDES.md))*

### 4. Running the Ecosystem
Launch the central orchestrator:
```bash
python carina.py
```
This single command spins up the 7 concurrent processes, initializes the IPC memory queues, boots the Flet UI, and begins listening on the gRPC port.

---

## 🧪 Testing & Validation

All Guardian rules and TCN inference pipelines are strictly tested.
```bash
pytest tests/ -v --cov=src
```
*(Read the [Testing Guidelines](docs/TESTING.md))*

---

**CARINA** is licensed under the [GNU Affero General Public License v3.0](LICENSE). © 2026 Noxfort.
