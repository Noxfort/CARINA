---
tags: [ui, flet, frontend]
aliases: [UI, Dashboard, Frontend]
---
# 🖥️ UI & Smart Dashboard Service (SDS)

CARINA features a completely decoupled frontend architecture. The heavy lifting of rendering UI components and streaming live telemetry is completely isolated from the AI Engine to guarantee zero frame-drops or inference stuttering.

⬅️ Back to [[CARINA_MOC|Main Documentation Hub]]

## 1. The Flet Desktop Architecture (`ui/`)

The graphical interface is built using **Flet**, a framework that compiles Python to a Flutter native desktop application. 

### Core Components
- **`carina.py` (The Launcher)**: The main thread of execution is permanently yielded to the `ft.app(target=main)` render loop. If the Flet window closes, the `TrayHandler` takes over.
- **`TrayHandler`**: Uses `pystray` to keep the massive AI ecosystem running quietly in the background (System Tray). Users can right-click the tray icon to restore the Flet window or trigger a Graceful Shutdown.
- **Asynchronous Views**: The `ui/views/` directory contains individual screens (Dashboard, Topology Map, XAI Reports) that update asynchronously via `page.update()` without blocking user interaction.

---

## 2. Smart Dashboard Service (`sds/`)

The SDS acts as the crucial bridge between the `EpisodeRunner` (AI Process) and the Flet UI. It runs inside its own OS process: `DashboardService`.

### 2.1 Telemetry Aggregation
- The `telemetry_aggregator.py` reads raw data points from the internal queues and aggregates them into visually digestible metrics (e.g., calculating moving averages of intersection delays or generating color gradients for heatmaps).

### 2.2 WebSocket Server
- Instead of using direct memory hooks (which would violate process isolation), the `websocket_server.py` broadcasts JSON payloads over local network ports.
- The Flet UI frontend acts as a standard WebSocket Client, consuming these JSON payloads and re-rendering the visual widgets at 60 FPS.
