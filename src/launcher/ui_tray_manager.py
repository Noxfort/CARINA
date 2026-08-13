# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/launcher/ui_tray_manager.py
# Author: Gabriel Moraes
# Date: August 6, 2026

import os
import sys
import time
import logging
import signal
import threading

# Conditional imports for UI and System Tray
try:
    import ui.main_ui as ui_module
    import flet as ft
    UI_AVAILABLE = True
except ImportError as e:
    UI_AVAILABLE = False
    if __name__ == "__main__":
        print(f"[Launcher Warning] UI not available: {e}")

try:
    from ui.handlers.tray_handler import TrayHandler
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    if __name__ == "__main__":
        print("[Launcher Warning] System tray not available (pystray missing)")


class UITrayManager:
    """
    Manages the lifecycle of Flet UI, System Tray icon,
    and OS signal handling (SIGINT/SIGTERM).
    """
    def __init__(self, process_manager, bundle_root: str):
        self.process_manager = process_manager
        self.bundle_root = bundle_root
        self.shutdown_requested = threading.Event()
        self.restore_requested = threading.Event()
        self.tray_handler = None

        try:
            from ui.providers.live_data_provider import LiveDataProvider
            LiveDataProvider.GLOBAL_SHUTDOWN_EVENT = self.shutdown_requested
        except Exception:
            pass

    def setup_signal_handlers(self):
        """Registers OS signal handlers for graceful shutdown (Ctrl+C / SIGTERM)."""
        def handle_shutdown_signal(signum, frame):
            logging.info(f"[Launcher] Interrupt signal ({signum}) received via terminal. Shutting down CARINA...")
            self.shutdown_requested.set()
            # Force close Flet UI window immediately if active
            try:
                for mod_name in ['ui.main_ui', 'main_ui']:
                    if mod_name in sys.modules:
                        ui_mod = sys.modules[mod_name]
                        page = getattr(ui_mod, 'active_page', None)
                        if page:
                            if hasattr(page, 'window') and page.window is not None:
                                page.window.prevent_close = False
                                page.window.destroy()
                            else:
                                page.window_prevent_close = False
                                page.window_destroy()
            except Exception as e:
                logging.debug(f"[Launcher] Exception while destroying Flet window via signal: {e}")
            raise KeyboardInterrupt

        try:
            signal.signal(signal.SIGINT, handle_shutdown_signal)
            if hasattr(signal, 'SIGTERM'):
                signal.signal(signal.SIGTERM, handle_shutdown_signal)
        except Exception as e:
            logging.warning(f"[Launcher] Could not register signal handler: {e}")

    def on_tray_restore(self):
        """Callback triggered when user selects restore from system tray menu."""
        logging.info("[Tray] Scheduled restoring UI window...")
        self.restore_requested.set()

    def on_tray_quit(self):
        """Callback triggered when user selects quit from system tray menu."""
        logging.info("[Tray] Encerrando CARINA via bandeja (system tray)...")
        self.shutdown_requested.set()

        # 1. Direct window destruction to unblock Flet event loop on main thread
        try:
            for mod_name in ['ui.main_ui', 'main_ui']:
                if mod_name in sys.modules:
                    ui_mod = sys.modules[mod_name]
                    page = getattr(ui_mod, 'active_page', None)
                    if page:
                        try:
                            if hasattr(page, 'window') and page.window is not None:
                                page.window.prevent_close = False
                                page.window.destroy()
                            else:
                                page.window_prevent_close = False
                                page.window_destroy()
                        except Exception:
                            pass
        except Exception as e:
            logging.debug(f"[Tray] Exception destroying window: {e}")

        # 2. Complete shutdown of all backend processes and IPC queues
        try:
            if self.process_manager:
                self.process_manager.shutdown_all()
        except Exception as e:
            logging.error(f"[Tray] Error executing process_manager.shutdown_all: {e}")

        # 3. Kill lingering child processes
        try:
            import psutil
            current_proc = psutil.Process(os.getpid())
            children = current_proc.children(recursive=True)
            for child in children:
                try:
                    if child.is_running():
                        cmdline = " ".join(child.cmdline()) if hasattr(child, 'cmdline') else ""
                        if "resource_tracker" not in cmdline:
                            child.kill()
                except Exception:
                    pass
        except Exception:
            pass

        # 4. Instant exit of main launcher process
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)

    def launch_flet_ui(self):
        """Launches or re-launches the Flet UI window."""
        assets_dir = os.path.join(self.bundle_root, "ui", "assets")
        ui_module.restore_event = self.restore_requested
        ui_module.shutdown_event = self.shutdown_requested
        ui_module.sas_result_queue = self.process_manager.queues.get('sas_results')
        ui_module.mfd_result_queue = self.process_manager.queues.get('mfd_results')
        ui_module.mfd_trigger_queue = self.process_manager.queues.get('mfd_trigger')
        try:
            ft.app(target=ui_module.main, assets_dir=assets_dir)
        except RuntimeError as e:
            if "cannot schedule new futures after shutdown" not in str(e):
                logging.error(f"[Flet Runtime] {e}")
        except Exception as e:
            logging.error(f"[UI Launcher] Failed to start or shutdown interface: {e}")

    def run(self):
        """Executes the main UI and Tray loop on the main thread."""
        self.setup_signal_handlers()
        icon_path = os.path.join(self.bundle_root, "ui", "assets", "images", "logo.png")
        tray_started = False

        if UI_AVAILABLE:
            if TRAY_AVAILABLE and os.path.exists(icon_path):
                self.tray_handler = TrayHandler(
                    icon_path=icon_path,
                    on_restore=self.on_tray_restore,
                    on_quit=self.on_tray_quit,
                )
                tray_started = self.tray_handler.start()
                if tray_started:
                    logging.info("[Launcher] System tray active. Closing window -> minimizes to tray.")
                else:
                    logging.warning("[Launcher] System tray not available, closing window terminates application.")

            # UI launch loop on main thread
            while not self.shutdown_requested.is_set():
                logging.info("Starting UI (Main Thread)...")
                self.launch_flet_ui()

                if not self.shutdown_requested.is_set():
                    if tray_started:
                        logging.info("[Launcher] Window closed. Waiting for wake/quit or restore...")
                        while not self.shutdown_requested.is_set():
                            if self.restore_requested.is_set():
                                self.restore_requested.clear()
                                break
                            time.sleep(0.1)
                    else:
                        logging.info("[Launcher] Window closed and System Tray is not active. Terminating application...")
                        self.shutdown_requested.set()
                        break
                else:
                    break

            if self.tray_handler:
                self.tray_handler.stop()
        else:
            if self.process_manager.p_cc:
                self.process_manager.p_cc.join()
