---
tags: [safety, guardian, watchdog, veto, failsafe]
aliases: [Safety Architecture, Guardian Veto, Watchdog System]
---

# 🛡️ Safety Architecture, Guardian Firewall & Watchdog

This document details CARINA's dual-stage Neuro-Symbolic Safety Firewall (`GuardianAgent` & `SafetyAuditor`) and the real-time deterministic `Watchdog` process.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Dual-Stage Safety Firewall Overview

CARINA separates physical safety from neural performance using a two-tier safety architecture:

```text
Proposed Phase Action ──> [1. Symbolic Safety Rules] ──> [2. Neural Spillback Veto] ──> Hardware Actuation
                              │                               │
                              ├── Veto (Min Green / Yellow)   └── Veto (Spillback Risk > 0.8)
                              └── Force Keep Phase            └── Force Clearing Phase
```

---

## 2. Symbolic Veto Rules Inventory

The `SafetyAuditor` enforces strict physical constraints that can never be overridden by neural training:

| Rule ID | Name | Constraint Description | Action on Violation |
| :--- | :--- | :--- | :--- |
| **SR-01** | **Minimum Green Time** | Active phase must remain active for at least $T_{min} = 7.0\text{s}$. | Force `ACTION_KEEP_PHASE`. |
| **SR-02** | **Yellow Clearance** | Phase change must trigger a mandatory $3.0\text{s}$ yellow signal. | Intercept action and inject Yellow phase. |
| **SR-03** | **All-Red Interval** | A $2.0\text{s}$ all-red clearance interval must execute between conflicting direction changes. | Inject All-Red phase. |
| **SR-04** | **Pedestrian Protection** | Pedestrian crossing buttons guarantee a minimum $12.0\text{s}$ walk phase. | Lock pedestrian signal green. |
| **SR-05** | **Conflict Matrix** | Prevents concurrent green signals on perpendicular or crossing lanes. | Hard veto; revert to safe state. |

---

## 3. Real-Time Process Watchdog (`watchdog.py`)

The `Watchdog` microservice (`run_watchdog`) monitors system health via heartbeats sent over the `wd` queue.

- **Heartbeat Interval:** 100ms
- **Timeout Threshold:** 500ms
- **Fail-Safe Mechanism:** If `AI_Process` or `CentralController` fails to emit a heartbeat within 500ms, the Watchdog signals hardware to fall back to hardcoded, fixed-time signal plans.
