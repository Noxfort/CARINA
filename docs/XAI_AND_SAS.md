---
tags: [xai, sas, mfd, captum, abnt, forensic-audit, guardian-veto]
aliases: [Explainable AI, SAS Analytics, MFD Engine, ABNT Reports]
---

# 🔍 Explainable AI (XAI), SAS Analytics & MFD Engine

This document specifies CARINA's forensic explainability pipeline (**`XaiReportGenerator`** / Captum), the Guardian Agent Veto Audit Engine, municipal ABNT NBR 14724 report generation, and the network-wide Macroscopic Fundamental Diagram engine (**`MFD_Worker`**).

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Explainable AI & Forensic Audit Generator (`XaiReportGenerator`)

In safety-critical municipal traffic control, black-box AI decisions are legally unacceptable to public prosecutors, audit courts (Tribunal de Contas), and traffic engineers. CARINA provides **100% deterministic mathematical explainability** via Google Captum Integrated Gradients and ABNT NBR 14724 Word export.

```text
    ┌─────────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
    │  Deep Neural Network    │ ───────> │ Captum Integrated         │ ───────> │  ABNT NBR 14724 Report │ ───> Forensic xai.docx
    │  (TCN + ST-GATv2 + D3QN)│          │ Gradients (0% to 100%)    │          │  5 Formal Equations +  │      (Municipal Audit Report)
    └─────────────────────────┘          └───────────────────────────┘          │  Guardian Veto Table   │
                                                                                └────────────────────────┘
```

---

## 2. The 5 Formal Neural Equations (Section 2 of ABNT Report)

To comply with public administration auditability standards, CARINA's report includes 5 formal LaTeX equations governing every neural network layer:

### 2.1 Causal Dilated Convolution (LocalAgent TCN)
$$\mathbf{y}(t) = (x *_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

### 2.2 Spatiotemporal Graph Attention (ST-GATv2 Lite)
$$\alpha_{ij}(t) = \frac{\exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_j]\right)\right)}{\sum_{k \in \mathcal{N}_i} \exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_k]\right)\right)}$$

### 2.3 Multimodal Cross-Attention Fusion (Transformer)
$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k} \cdot \tau}\right) V$$

### 2.4 Guardian Safety Dueling Q-Value (D3QN Veto)
$$Q(s, a) = V(s) + \left( A(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s, a') \right)$$

### 2.5 Captum Integrated Gradients (Attribution & Completeness Axiom)
$$\text{GradientesIntegrados}_i(x) = (x_i - x'_i) \times \int_0^1 \frac{\partial F(x' + \alpha(x - x'))}{\partial x_i} d\alpha$$

$$\sum_{i=1}^n \text{GradientesIntegrados}_i(x) = F(x) - F(x')$$

---

## 3. Guardian Agent Veto Audit Table (Section 4 & Anexo I)

The ABNT report automatically queries PostgreSQL `step_decisions` to generate the **Guardian Agent Safety Veto Audit Table**:

| Intersection ID | Evaluated Decisions | Approved / Homologated | Safety Vetoes | Compliance Rate (%) | Root Cause of Vetoes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cruzamento ID 1193472566** | 120 | 118 | 2 | **98.3%** | Min Green Time Protection (10s) |

---

## 4. Macroscopic Fundamental Diagram Engine (`MFD_Worker`)

The **`MFD_Worker`** aggregates spatial traffic density $K_{net}$ (veh/km) and network-wide space-mean flow $Q_{net}$ (veh/hr) to build real-time Macroscopic Fundamental Diagrams (MFD).

$$K_{net} = \frac{\sum_{i=1}^N k_i \cdot L_i}{\sum_{i=1}^N L_i}, \quad Q_{net} = \frac{\sum_{i=1}^N q_i \cdot L_i}{\sum_{i=1}^N L_i}$$

When $K_{net} > K_{crit}$, perimeter metering triggers to prevent city-wide gridlock.
