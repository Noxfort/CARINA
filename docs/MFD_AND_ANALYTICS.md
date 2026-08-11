---
tags: [mfd, analytics, dynamics, density, gating]
aliases: [MFD Engine, Network Analytics, Traffic Physics]
---

# 📈 Macroscopic Fundamental Diagram & Network Analytics

This document details the Macroscopic Fundamental Diagram worker (**`MFD_Worker`**), network density dynamics, and incident filtering cache.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. MFD Theory & Capacity Estimation

The **Macroscopic Fundamental Diagram (MFD)** relates the total accumulation of vehicles (density $K$) in a urban network to the total space-mean flow ($Q$).

```text
       Q (veh/h)
          ▲                Zone 1: Uncongested (PPO-TCN Active)
     Qmax │           /\   Zone 2: Capacity Drop (Perimeter Gating Triggered)
          │          /  \  Zone 3: Gridlock / Collapse (Emergency Override)
          │         /    \
          └────────┴──────┴────────► K (veh/km)
                  Kcrit   Kjam
```

- **Uncongested Region ($K < K_{crit}$):** Local PPO-TCN agents optimize individual intersection throughput.
- **Capacity Drop Region ($K > K_{crit}$):** `MFD_Worker` signals `CentralController` to restrict vehicle entries at perimeter intersections (*Perimeter Gating*).

---

## 2. Incident Filter Debug Cache (`.carina_incident_filter_cache.json`)

The incident filter detects sudden vehicle deceleration or lane blockage anomalies. Incident states are cached locally in `.carina_incident_filter_cache.json` for rapid recovery across system restarts.
