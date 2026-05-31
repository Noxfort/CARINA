---
tags: [readme, home, carina]
aliases: [Projeto CARINA, Root]
---
# 🚗 CARINA: Cognitive Autonomous Real-time Intersection Network Architecture

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c)
![Flet](https://img.shields.io/badge/Flet-UI-00d2b4)
![License](https://img.shields.io/badge/License-Proprietary-red)

**CARINA** is a massively distributed Deep Reinforcement Learning ecosystem designed for real-time traffic control and smart city orchestration. Bypassing Python's Global Interpreter Lock (GIL) via 7 concurrent OS processes, it integrates a Tactical PPO agent and a Guardian Agent (Dueling DQN-TCN + Predictive Autoencoder) to provide neuro-symbolic safety. CARINA learns online directly in production via the sub-millisecond Synapse HFT protocol.

---

## 📖 Obsidian Knowledge Vault

This repository is designed to be browsed natively in **Obsidian**. To explore the full architecture and internal workings of the system via our Knowledge Graph:
1. Open [Obsidian](https://obsidian.md/).
2. Select **"Open folder as vault"**.
3. Choose the root directory of this repository (`CARINA_CORE`).
4. 👉 **Start here:** [[CARINA_MOC|Central Documentation Hub]]

---

## ⚡ Core Architecture (GOMES & DA SILVA)

CARINA relies on the **Graph-based Operational Multi-agent Expert System (GOMES)** to handle complex intersections, governed by the **DA SILVA** statistical maturation curriculum.

- **Tactical Layer (PPO-TCN):** Hyper-focused on local intersection throughput using Temporal Convolutional Networks to eliminate BPTT explosion.
- **Strategic Layer (GATv2 Lite):** Coordinates "Green Waves" using Graph Attention Networks to prioritize massive avenues.
- **Guardian Layer (Neuro-Symbolic):** A background firewall that instantaneously vetoes any action violating strict physical safety constraints.
- **Explainable AI (XAI):** A massive `Qwen3 1.7B` LLM process coupled with `Captum` Integrated Gradients to generate natural-language engineering reports explaining neural reasoning.

*See the full breakdown in the [[ARCHITECTURE|System Blueprint]]*

---

## 🛠️ Key Features

- **Synapse HFT Protocol:** High-frequency, bidirectional gRPC telemetry capable of sub-millisecond physical actuation. (See [[API_REFERENCE]])
- **Decoupled Flet Frontend:** A beautiful, responsive desktop Dashboard Service (SDS) that runs completely isolated from the AI inference loop. (See [[UI_AND_DASHBOARD]])
- **Smart Analysis System (SAS):** Offline background process that analyzes historical PostgreSQL data to suggest infrastructure modifications. (See [[XAI_AND_SAS]])
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
*(Refer to [[DEVELOPER_GUIDES|Developer Integration Guide]])*

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
*(Read the [[TESTING|Testing Guidelines]])*

---

**CARINA** © 2026 Noxfort. All rights reserved.
