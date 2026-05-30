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

# File: ui/handlers/tray_handler.py
# Author: Gabriel Moraes
# Date: 2026-03-21

"""
System Tray Icon Handler for CARINA.

Manages the system tray (notification area) icon that allows:
- Minimize to tray when the window is closed
- Restore the window by clicking the tray icon
- Quit the application from the tray context menu
"""

import os
import sys
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    
    # Try AppIndicator backend first (supports right-click menus on GNOME/KDE)
    import platform
    _appindicator_ok = False
    if platform.system() == 'Linux':
        try:
            import gi
            gi.require_version('AyatanaAppIndicator3', '0.1')
            os.environ['PYSTRAY_BACKEND'] = 'appindicator'
            _appindicator_ok = True
            logger.info("[TrayHandler] AppIndicator backend available. Right-click menu enabled.")
        except (ImportError, ValueError):
            # gi or AyatanaAppIndicator3 not available — fall back to xorg/default
            logger.info("[TrayHandler] AppIndicator not available, using default X11 backend.")
    
    import pystray
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    logger.warning("[TrayHandler] pystray or Pillow not available. System tray disabled.")


class TrayHandler:
    """
    Manages the system tray icon lifecycle.
    
    The tray icon is created on a separate daemon thread so it doesn't block
    the main Flet event loop.
    """

    def __init__(self, icon_path: str, on_restore: Optional[Callable] = None, on_quit: Optional[Callable] = None):
        """
        Args:
            icon_path: Absolute path to the icon image (PNG).
            on_restore: Callback invoked when user clicks "Abrir CARINA" or double-clicks the tray icon.
            on_quit: Callback invoked when user clicks "Encerrar" in the tray menu.
        """
        self._icon_path = icon_path
        self._on_restore = on_restore
        self._on_quit = on_quit
        self._tray_icon: Optional['pystray.Icon'] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def is_available(self) -> bool:
        """Check if system tray functionality is available."""
        return TRAY_AVAILABLE and os.path.exists(self._icon_path)

    def start(self) -> bool:
        """
        Start the system tray icon on a background thread.
        Returns True if started successfully, False otherwise.
        """
        if not self.is_available:
            logger.warning("[TrayHandler] Cannot start: pystray not available or icon not found.")
            return False

        if self._running:
            logger.debug("[TrayHandler] Already running.")
            return True

        try:
            image = Image.open(self._icon_path)
            # Resize to standard tray icon size for crisp display
            image = image.resize((64, 64), Image.LANCZOS)
            
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Abrir CARINA",
                    self._handle_restore,
                    default=True  # Double-click action
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Encerrar",
                    self._handle_quit
                ),
            )

            self._tray_icon = pystray.Icon(
                name="carina",
                icon=image,
                title="CARINA - AI Traffic Control",
                menu=menu,
            )

            def safe_run():
                try:
                    self._tray_icon.run()
                except Exception as e:
                    logger.warning(f"[TrayHandler] Tray backend issue (expected on some Linux distros): {e}")

            self._thread = threading.Thread(
                target=safe_run,
                name="CARINATrayThread",
                daemon=True,
            )
            self._thread.start()
            self._running = True
            logger.info("[TrayHandler] System tray icon started.")
            return True

        except Exception as e:
            logger.error(f"[TrayHandler] Failed to start tray icon: {e}")
            return False

    def stop(self):
        """Stop and remove the system tray icon."""
        if self._tray_icon and self._running:
            try:
                self._tray_icon.stop()
            except Exception as e:
                logger.debug(f"[TrayHandler] Error stopping tray: {e}")
            self._running = False
            logger.info("[TrayHandler] System tray icon stopped.")

    def _handle_restore(self, icon=None, item=None):
        """Called when user clicks 'Abrir CARINA' or double-clicks the tray icon."""
        logger.info("[TrayHandler] Restore requested.")
        if self._on_restore:
            try:
                self._on_restore()
            except Exception as e:
                logger.error(f"[TrayHandler] Error in restore callback: {e}")

    def _handle_quit(self, icon=None, item=None):
        """Called when user clicks 'Encerrar' from the tray menu."""
        logger.info("[TrayHandler] Quit requested from tray.")
        self.stop()
        if self._on_quit:
            try:
                self._on_quit()
            except Exception as e:
                logger.error(f"[TrayHandler] Error in quit callback: {e}")
