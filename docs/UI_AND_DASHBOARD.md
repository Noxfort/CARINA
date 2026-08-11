---
tags: [ui, flet, dashboard, frontend, sds]
aliases: [UI Architecture, Dashboard Service, Flet Frontend]
---

# 🖥️ UI & Smart Dashboard Service (SDS) Architecture

This document details CARINA's native desktop UI, the **Smart Dashboard Service (SDS)**, the **System Tray Manager**, and the single-instance locking system.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Decoupled Desktop Architecture (`ui/`)

To prevent GUI rendering or client browser socket lag from dropping real-time traffic control frames, CARINA completely decouples its frontend into the **`DashboardService` (SDS)** process (`run_sds_worker`).

```text
CentralController (gRPC) ──> [sds Queue] ──> DashboardService (SDS) ──> [ui Queue] ──> Flet UI (Main Thread)
                                                   │
                                                   └──> WebSocket Telemetry Server (port 8080)
```

---

## 2. Flet Desktop UI Components & Views

The frontend is built using **[Flet](https://flet.dev/)** (Python + Flutter engine) located in `ui/`.

```text
ui/
├── views/                  # Primary Dashboard Screens
│   ├── main_view.py        # Central Real-time Telemetry & Signal Monitor
│   ├── analytics_view.py   # SAS Infrastructure Warrants & Historical Trends
│   ├── mfd_view.py         # Live Macroscopic Fundamental Diagram Curve Plotter
│   └── settings_view.py    # Runtime System Configuration & gRPC Settings
│
├── components/             # Reusable UI Controls
│   ├── header.py           # Top Status Bar (gRPC status, active processes, FPS counter)
│   ├── sidebar.py          # Navigation Drawer & Quick Action Buttons
│   ├── signal_card.py      # Individual Intersection Live Phase Display
│   └── incident_filter.py  # Real-time Incident & Safety Veto Log Table
│
├── theme/                  # Design System & Styling
│   ├── colors.py           # Curated Dark Theme Color Palette
│   └── typography.py       # Custom Font Scales & Spacing Tokens
│
└── assets/                 # Icons, System Tray Graphics & Logotypes
```

---

## 3. System Tray & Single Instance Lock (`SingleInstanceLock`)

CARINA runs seamlessly as a background system daemon with a native desktop tray icon.

### 3.1 System Tray Management (`UITrayManager`)
- **Tray Actions:** Minimize to Tray, Open Dashboard, View Live Logs, Restart Services, Graceful Shutdown.
- **Notification Popups:** Displays system alerts when the Watchdog detects process failure or when the Guardian Agent fires an emergency veto.

### 3.2 Single Instance Lock (`SingleInstanceLock`)
- **Port:** `42123`
- If a user double-clicks `carina.py` or the built binary while CARINA is already running:
  1. The new process attempts to acquire TCP port `42123`.
  2. Upon failure, it sends a RESTORE command signal over the local TCP socket to the primary instance.
  3. The primary instance receives the signal, restores the Flet dashboard window to the foreground, and the duplicate process exits cleanly.
