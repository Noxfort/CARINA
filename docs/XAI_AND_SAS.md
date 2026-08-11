---
tags: [xai, sas, mfd, llm, analytics]
aliases: [Explainable AI, SAS Analytics, MFD Worker]
---

# 🔍 Explainable AI (XAI), SAS Analytics & MFD Engine

This document specifies CARINA's explainability pipeline (**`XAI_Worker`**), offline infrastructure analytics (**`AnalysisService` / SAS**), and the network-wide Macroscopic Fundamental Diagram engine (**`MFD_Worker`**).

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Explainable AI Worker (`XAI_Worker`)

In safety-critical urban infrastructure, black-box AI decisions are unacceptable to municipal traffic engineers. The `XAI_Worker` translates complex neural network activations into human-readable engineering rationale.

```text
    ┌─────────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
    │  PPO-TCN Neural Action  │ ───────> │ Captum Feature Attribution │ ───────> │  Qwen3 1.7B LLM Worker │ ───> Natural Language Report
    │  (e.g., Extend Phase 2) │          │ (Integrated Gradients)    │          │  (vLLM / PyTorch GPU)  │      ("Extended Phase 2 due to 45%
    └─────────────────────────┘          └───────────────────────────┘          └────────────────────────┘       queue buildup on North Ave")
```

### 1.1 Integrated Gradients via Captum

Feature attributions are computed using Integrated Gradients:

$$\text{Attribution}_i(x) = (x_i - x'_i) \times \int_{0}^{1} \frac{\partial F(x' + \alpha (x - x'))}{\partial x_i} d\alpha$$

Where:
- $x$: Actual input traffic state tensor.
- $x'$: Neutral baseline tensor (zero traffic occupancy).
- $F(x)$: Neural policy output probability for the chosen phase action.

### 1.2 Qwen3 1.7B LLM Text Generation Prompt Template

The top 3 attributed traffic features (e.g., `lane_north_queue = +0.64`, `lane_east_speed = -0.42`) are injected into the local Qwen3 1.7B language model prompt:

```text
[SYSTEM PROMPT]
You are CARINA Senior Traffic AI Engineer. Explain the neural traffic decision using the feature attributions below. Be concise, technical, and precise.

[INPUT ATTRIBUTIONS]
- Chosen Action: Phase 2 (North-South Main Arterial Green)
- Top Attribution 1: lane_north_queue_length (+0.64 - High Queue Accumulation)
- Top Attribution 2: lane_south_occupancy (+0.28 - Increasing Density)
- Top Attribution 3: lane_east_spillback_risk (-0.12 - Low Side Street Risk)

[EXPLANATION REPORT]
```

---

## 2. Smart Analysis System (`AnalysisService` / SAS)

The **Smart Analysis System (SAS)** runs as an offline background process (`run_analysis_worker`). It queries historical PostgreSQL data tables (`traffic_metrics`, `episode_rewards`, `guardian_vetoes`) to evaluate signal timing efficiency and generate municipal engineering warrants.

### 2.1 Warrant Generation Pipeline
- **Warrant 1 (8-Hour Vehicular Volume):** Evaluates whether traffic volume justifies converting a stop-sign intersection to full CARINA AI control.
- **Warrant 2 (4-Hour Peak Volume):** Identifies recurring bottleneck hours.
- **Warrant 3 (Pedestrian Safety & Veto Analysis):** Flags intersections where the Guardian Agent triggered more than 50 vetoes per day.

---

## 3. Macroscopic Fundamental Diagram Engine (`MFD_Worker`)

The **`MFD_Worker`** aggregates spatial traffic density $K_{net}$ (veh/km) and network-wide space-mean flow $Q_{net}$ (veh/hr) to build real-time Macroscopic Fundamental Diagrams (MFD).

```text
Network Flow (Q)
   ^
Qmax│             / \   <-- Capacity Drop Boundary (Gridlock Imminent)
    │            /   \
    │           /     \
    │          /       \
    └─────────┴─────────┴─────────> Network Density (K)
             K_crit    K_jam
```

### 3.1 MFD Mathematical Formulation

For a spatial network of $N$ road edges with lengths $L_i$:

$$K_{net} = \frac{\sum_{i=1}^N k_i \cdot L_i}{\sum_{i=1}^N L_i}, \quad Q_{net} = \frac{\sum_{i=1}^N q_i \cdot L_i}{\sum_{i=1}^N L_i}$$

When $K_{net} > K_{crit}$, the `MFD_Worker` sends an emergency alert via the `mfd_results` queue to trigger perimeter metering (restricting entry into the city core).
