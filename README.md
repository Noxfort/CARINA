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

**CARINA** is a massively distributed Deep Reinforcement Learning ecosystem designed for real-time traffic control and smart city orchestration. Bypassing Python's Global Interpreter Lock (GIL) via 8 concurrent OS processes, it integrates a Tactical PPO agent, an ST-GATv2 Lite Graph Coordinator, a Global Consultant Agent (PAE 128-channel), and a Guardian Agent (D3QN) to provide 100% ABNT-compliant forensic auditability and neuro-symbolic safety.

---

## 📚 Documentation Hub & Knowledge Vault

Explore the full architecture, internal mechanics, and developer guides for the CARINA ecosystem:

| Card / Subsystem | Focus Area | Direct Link |
| :--- | :--- | :---: |
| 📚 **Documentation Hub** | Central Index & Navigation for all technical docs | [Explore Hub](docs/CARINA_MOC.md) |
| 🏛️ **Core Architecture** | 8 Concurrent OS microservices, ST-GATv2 Lite & Consultant PAE | [View Blueprint](ARCHITECTURE.md) |
| ⚡ **Synapse HFT API** | Sub-millisecond gRPC telemetry & Protobuf IPC specifications | [View API Reference](docs/API_REFERENCE.md) |
| 🧠 **Neural Formulations** | PPO-TCN, ST-GATv2 Lite, Cross-Attention & Consultant PAE | [View Research](docs/RESEARCH_NOTES.md) |
| 🛡️ **Safety Firewall & Watchdog** | Guardian D3QN Vetoes, Symbolic rules & Watchdog | [View Safety Guide](docs/SAFETY_AND_WATCHDOG.md) |
| 🗄️ **Database & Schemas** | PostgreSQL Delta Storage (97.9% reduction), 1-byte Enums | [View DB Specs](docs/DATABASE_AND_SCHEMAS.md) |
| 📈 **MFD & Traffic Analytics** | Network density-flow curves, capacity drop & gating | [View MFD Guide](docs/MFD_AND_ANALYTICS.md) |
| 🔍 **Explainable AI (XAI)** | Captum Integrated Gradients, 5 Formal Equations & Word export | [View XAI & SAS](docs/XAI_AND_SAS.md) |
| 🖥️ **Flet Dashboard** | Native desktop UI running in an isolated process | [View UI Guide](docs/UI_AND_DASHBOARD.md) |
| 🛠️ **Developer Guides** | Schema migrations, PyInstaller builds, IPC queues | [View Guides](docs/DEVELOPER_GUIDES.md) |
| 🧪 **Testing & Validation** | Pytest suite, coverage reports & Guardian safety mocks | [View Guidelines](docs/TESTING.md) |
| 🚀 **Deployment & Packaging** | Docker containerization, Systemd services & Debian packages | [View Deployment](docs/DEPLOYMENT_AND_PACKAGING.md) |

---

## ⚡ Core Architecture (GOMES & DA SILVA)

- **Tactical Layer (PPO-TCN Edge AI):** Hyper-focused on local intersection throughput with sub-millisecond ($< 0.5\text{ ms}$) execution.
- **Strategic Layer (ST-GATv2 Lite):** Dynamic spatiotemporal graph attention coordinating Green Waves across urban avenues.
- **Global Consultant Layer (PAE 128-channel):** Event-triggered background mentor projecting future traffic states ($t + \Delta t$).
- **Guardian Layer (Neuro-Symbolic D3QN):** Inviolable safety firewall validating or vetoing actions against traffic codes and spillback risks.
- **Explainable AI (XAI Engine):** Google Captum Integrated Gradients exporting ABNT NBR 14724 reports with 5 formal neural equations and Guardian veto audit tables.
- **PostgreSQL Delta Storage:** Non-blocking async queue with 1-byte Smallint enums and run-length encoding achieving **97.9% storage reduction** (~380 MB/day for 200 intersections).

---

## 🚀 Quick Start

### 1. Requirements
Ensure you have Python 3.10+ and a CUDA-compatible GPU (accelerated via PyTorch AMP & NVIDIA TensorCores).

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Running the Ecosystem
```bash
python carina.py
```

---

**CARINA** is licensed under the [GNU Affero General Public License v3.0](LICENSE). © 2026 Noxfort.
