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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: ui/managers/window_manager.py
# Author: Gabriel Moraes
# Date: July 19, 2026

import sys
import os
import time
import logging
import flet as ft

class WindowManager:
    """
    Responsible for managing the Flet window lifecycle,
    including keyboard shortcuts (F11), window close interception (minimize to tray),
    and synchronization with the system tray daemon.
    """
    def __init__(self, page: ft.Page, restore_event, shutdown_event):
        self.page = page
        self.restore_event = restore_event
        self.shutdown_event = shutdown_event

    def configure_window(self, app_title: str, favicon_path: str = None):
        self.page.title = app_title
        self.page.window_width = 1280
        self.page.window_height = 800
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 10

        if favicon_path and os.path.exists(favicon_path):
            self.page.window_favicon_path = favicon_path

        # F11 keyboard shortcut
        self.page.on_keyboard_event = self._handle_keyboard

        # Intercept window close button
        if hasattr(self.page, 'window') and self.page.window is not None:
            self.page.window.prevent_close = True
            self.page.window.on_event = self._window_event
        else:
            try:
                self.page.window_prevent_close = True
                self.page.on_window_event = self._window_event
            except AttributeError:
                pass

        # Start background thread to monitor system tray signals
        self.page.run_thread(self._monitor_tray_loop)

    def _handle_keyboard(self, e: ft.KeyboardEvent):
        if e.key == "F11":
            if hasattr(self.page, 'window') and self.page.window is not None:
                self.page.window.full_screen = not self.page.window.full_screen
            else:
                self.page.window_full_screen = not getattr(self.page, "window_full_screen", False)
            self.page.update()

    def _window_event(self, e):
        if hasattr(e, 'data') and e.data == "close":
            if self.shutdown_event and self.shutdown_event.is_set():
                return
            logging.info("[WindowManager] Botão 'X' clicado pelo usuário. Minimizando janela para a bandeja em vez de fechar...")
            if hasattr(self.page, 'window') and self.page.window is not None:
                self.page.window.minimized = True
                self.page.window.visible = False
            else:
                try:
                    self.page.window_minimized = True
                    self.page.window_visible = False
                except Exception:
                    pass
            self.page.update()

    def _monitor_tray_loop(self):
        while True:
            if self.restore_event and self.restore_event.is_set():
                self.restore_event.clear()
                self._restore_window()
                
            if self.shutdown_event and self.shutdown_event.is_set():
                self._destroy_window()
                break
            time.sleep(0.1)

    def _restore_window(self):
        if hasattr(self.page, 'window') and self.page.window is not None:
            is_visible = getattr(self.page.window, 'visible', False)
            is_minimized = getattr(self.page.window, 'minimized', False)
            
            if is_visible and not is_minimized:
                self.page.window.minimized = True
            else:
                self.page.window.visible = True
                self.page.window.minimized = False
                self.page.window.focused = True
                try:
                    self.page.window.to_front()
                except Exception:
                    pass
        else:
            is_visible = getattr(self.page, 'window_visible', False)
            is_minimized = getattr(self.page, 'window_minimized', False)
            
            if is_visible and not is_minimized:
                self.page.window_minimized = True
            else:
                self.page.window_visible = True
                try:
                    self.page.window_minimized = False
                    self.page.window_focused = True
                    self.page.window_to_front()
                except Exception:
                    pass
        self.page.update()

    def _destroy_window(self):
        if hasattr(self.page, 'window') and self.page.window is not None:
            self.page.window.prevent_close = False
            self.page.window.destroy()
        else:
            try:
                self.page.window_prevent_close = False
            except:
                pass
            self.page.window_destroy()

    def hard_kill_app(self):
        logging.info("[UI] Requested hard kill of the application...")
        if self.shutdown_event:
            self.shutdown_event.set()
        self._destroy_window()
        try:
            import psutil
            current_proc = psutil.Process(os.getpid())
            for child in current_proc.children(recursive=True):
                try:
                    if child.is_running():
                        child.kill()
                except Exception:
                    pass
        except Exception:
            pass
        os._exit(0)
