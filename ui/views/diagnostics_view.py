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

# File: ui/views/diagnostics_view.py (FIXED: Path Results using utils.paths)
# Author: Gabriel Moraes
# Date: December 17, 2025

import flet as ft
import os
import time
import threading
import glob
import logging
import sys

# Ensures that utils.paths can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, "..", ".."))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.paths import get_base_output_dir # <--- THE MAGIC FIX
from ui.handlers.locale_manager import LocaleManager
from ui.widgets.mfd_viewer_widget import MfdViewerWidget
from ui.widgets.xai_viewer_widget import XaiViewerWidget
from ui.widgets.audit_log_widget import AuditLogWidget

class DiagnosticsView(ft.Column):
    """
    View responsible for system diagnostics.
    
    ATUALIZAÇÃO: Usa get_base_output_dir() para garantir que a UI
    olhe para a mesma pasta 'results' que o Backend.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__()
        self.locale_manager = locale_manager
        self.expand = True 
        
        # --- PATH CORRECTION ---
        # The backend uses get_base_output_dir(), so the UI should use it too.
        self.project_root = get_base_output_dir()
        
        self.results_dir = os.path.join(self.project_root, "results", "hft_live_session")
        
        logging.info(f"[UI_DIAG] DiagnosticsView inicializada.")
        logging.info(f"[UI_DIAG] Pasta de Resultados (Backend): {self.results_dir}")
        
        # Widgets
        self.mfd_viewer = MfdViewerWidget(
            locale_manager,
            results_dir=self.results_dir
        )
        
        # XAI Widget now receives the CORRECT directory
        self.xai_viewer = XaiViewerWidget(
            locale_manager, 
            results_dir=self.results_dir
        )
        self.audit_viewer = AuditLogWidget(locale_manager)
        
        # Control
        self.watching = False
        self.watch_thread = None

        # Layout
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text=locale_manager.get_string("diagnostics_view.nav_mfd", default="MFD Optimization Analysis"),
                    icon=ft.Icons.AUTO_GRAPH_ROUNDED,
                    content=ft.Container(
                        content=self.mfd_viewer,
                        padding=10
                    )
                ),
                ft.Tab(
                    text=locale_manager.get_string("diagnostics_view.nav_xai", default="Neural Analysis (XAI)"),
                    icon=ft.Icons.PSYCHOLOGY_ROUNDED,
                    content=ft.Container(
                        content=self.xai_viewer,
                        padding=10
                    )
                ),
                ft.Tab(
                    text="Auditoria (Audit Logs)",
                    icon=ft.Icons.POLICY_ROUNDED,
                    content=ft.Container(
                        content=self.audit_viewer,
                        padding=10
                    )
                ),
            ],
            expand=True
        )

        self.controls = [self.tabs]

    def did_mount(self):
        logging.info("[UI_DIAG] View montada. Iniciando Agent Watcher...")
        self.start_log_watcher()

    def will_unmount(self):
        logging.info("[UI_DIAG] View desmontando. Parando Agent Watcher...")
        self.stop_log_watcher()

    def update_translations(self, locale_manager: LocaleManager):
        self.locale_manager = locale_manager
        self.tabs.tabs[0].text = locale_manager.get_string("diagnostics_view.nav_mfd", default="MFD Optimization Analysis")
        self.tabs.tabs[1].text = locale_manager.get_string("diagnostics_view.nav_xai", default="Neural Analysis (XAI)")
        self.mfd_viewer.update_translations(locale_manager)
        self.xai_viewer.update_translations(locale_manager)
        if self.page: self.update()

    def start_log_watcher(self):
        if not self.watching:
            self.watching = True
            self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self.watch_thread.start()

    def stop_log_watcher(self):
        self.watching = False

    def _watch_loop(self):
        """Monitora APENAS o arquivo de Log e a lista de Agentes."""
        last_log_size = 0
        
        while self.watching:
            try:
                if not self.page:
                    time.sleep(1.0)
                    continue

                # --- 1. Agent Discovery (Agent List) ---
                checkpoints_dir = os.path.join(self.results_dir, "checkpoints")
                if os.path.exists(checkpoints_dir):
                    agent_files = glob.glob(os.path.join(checkpoints_dir, "agent_*.pth"))
                    agent_ids = sorted([os.path.basename(f).replace("agent_", "").replace(".pth", "") for f in agent_files])
                    if agent_ids:
                        self.xai_viewer.update_agent_list(agent_ids)

            except Exception as e:
                err_str = str(e)
                if "Event loop is closed" in err_str or "cannot schedule new futures" in err_str:
                    break
                logging.error(f"[UI_DIAG] Erro no loop de logs: {e}")
                time.sleep(2.0)
            
            time.sleep(1.0)