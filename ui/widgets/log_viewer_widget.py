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

# File: ui/widgets/log_viewer_widget.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o LogViewerWidget, um widget auto-suficiente para exibir
um ficheiro de log em tempo real usando uma thread separada.
"""

import flet as ft
import threading
import time
import os

from ui.handlers.locale_manager import LocaleManager

class LogViewerWidget(ft.Container):
    """
    Um widget que encapsula toda a funcionalidade de visualização de logs.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(expand=True)

        self.locale_manager = locale_manager
        self.log_thread = None
        self.thread_running = False
        
        self.pause_text = "Pausar Log"
        self.resume_text = "Continuar"
        
        self.log_view_list = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        self.title_text = ft.Text(size=20, weight=ft.FontWeight.BOLD)
        self.pause_button = ft.ElevatedButton(icon=ft.Icons.PAUSE_ROUNDED, on_click=self.toggle_pause_log)
        self.clear_button = ft.ElevatedButton(icon=ft.Icons.DELETE_SWEEP_ROUNDED, on_click=self.clear_log)
        
        self.content = ft.Column(
            controls=[
                 ft.Row(
                    [ft.Icon(ft.Icons.DESCRIPTION_ROUNDED), self.title_text],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                ft.Row(
                    [self.pause_button, self.clear_button],
                    alignment=ft.MainAxisAlignment.END,
                ),
                ft.Container(
                    content=self.log_view_list,
                    border=ft.border.all(1, ft.Colors.WHITE24),
                    border_radius=10,
                    padding=10,
                    expand=True,
                ),
            ],
            expand=True, spacing=10
        )

    def did_mount(self):
        self.update_translations(self.locale_manager)
        self.start_log_watcher()

    def will_unmount(self):
        self.stop_log_watcher()
        
    def update_translations(self, lm: LocaleManager):
        self.title_text.value = lm.get_string("diagnostics_view.log_viewer_title")
        self.pause_text = lm.get_string("diagnostics_view.log_pause")
        self.resume_text = lm.get_string("diagnostics_view.log_resume")
        self.clear_button.text = lm.get_string("diagnostics_view.log_clear")
        
        if self.thread_running:
            self.pause_button.text = self.pause_text
        else:
            self.pause_button.text = self.resume_text
            
        if self.page: self.update()

    def start_log_watcher(self):
        if not self.log_thread or not self.log_thread.is_alive():
            self.thread_running = True
            self.log_thread = threading.Thread(target=self._log_watcher_thread, daemon=True)
            self.log_thread.start()
            self.pause_button.text = self.pause_text
            self.pause_button.icon = ft.Icons.PAUSE_ROUNDED
            if self.page: self.update()

    def stop_log_watcher(self):
        self.thread_running = False
        if self.page:
            self.pause_button.text = self.resume_text
            self.pause_button.icon = ft.Icons.PLAY_ARROW_ROUNDED
            if self.page.session:
                try: self.update()
                except Exception: pass

    def toggle_pause_log(self, e):
        if self.thread_running:
            self.stop_log_watcher()
        else:
            self.start_log_watcher()

    def clear_log(self, e):
        self.log_view_list.controls.clear()
        self.update()
        
    def _add_log_message_bulk(self, lines_data):
        if not self.page or not self.page.session: return
        
        MAX_LINES = 500
        controls_to_add = []
        
        for text, color in lines_data:
            controls_to_add.append(
                ft.Text(text, style=ft.TextStyle(font_family="monospace"), color=color)
            )
            
        if controls_to_add:
            self.log_view_list.controls.extend(controls_to_add)
            
            # Ring buffer logic to prevent Flet memory explosions
            if len(self.log_view_list.controls) > MAX_LINES:
                self.log_view_list.controls = self.log_view_list.controls[-MAX_LINES:]
                
            if self.thread_running:
                try:
                    self.update()
                except Exception:
                    pass
        
    # --- RESTORED CONTENT ---
    def _find_latest_log_file(self):
        try:
            from src.utils.paths import get_base_output_dir
            log_base_dir = os.path.join(get_base_output_dir(), "logs", "launcher")
            if not os.path.isdir(log_base_dir): return None
            log_file = os.path.join(log_base_dir, "launcher.log")
            return log_file if os.path.exists(log_file) else None
        except Exception:
            return None

    def _log_watcher_thread(self):
        current_log_file = None
        
        while self.thread_running:
            latest_log_file = self._find_latest_log_file()
            if current_log_file != latest_log_file:
                current_log_file = latest_log_file
                self.log_view_list.controls.clear()
                if current_log_file:
                    msg_template = self.locale_manager.get_string("diagnostics_view.log_watching_file")
                    self._add_log_message_bulk([ (msg_template.format(file_path=f"...{current_log_file[-50:]}"), ft.Colors.GREEN) ])
                else:
                    self._add_log_message_bulk([ (self.locale_manager.get_string("diagnostics_view.log_searching"), ft.Colors.ORANGE) ])
            
            if current_log_file:
                try:
                    with open(current_log_file, "r", encoding="utf-8") as f:
                        f.seek(0, 2) # Go to the end of the file
                        import re
                        ANSI_CLEANER = re.compile(r'\x1b\[[0-9;]*m')
                        
                        while self.thread_running:
                            check_latest = self._find_latest_log_file()
                            if check_latest != current_log_file:
                                self._add_log_message_bulk([ (self.locale_manager.get_string("diagnostics_view.log_new_detected"), ft.Colors.AMBER) ])
                                break
                            
                            new_lines = f.readlines()
                            if not new_lines:
                                time.sleep(0.5)
                                continue
                            
                            parsed_lines = []
                            for line in new_lines:
                                clean_line = ANSI_CLEANER.sub('', line.strip())
                                if not clean_line: continue
                                
                                # Industry Standard Colors
                                color = ft.Colors.WHITE70
                                if "[ERROR]" in clean_line or "[CRITICAL]" in clean_line or "Traceback" in clean_line:
                                    color = ft.Colors.RED_400
                                elif "[WARNING]" in clean_line:
                                    color = ft.Colors.AMBER_400
                                elif "[INFO]" in clean_line:
                                    color = ft.Colors.LIGHT_BLUE_300
                                elif "[DEBUG]" in clean_line:
                                    color = ft.Colors.BLUE_GREY_400
                                
                                parsed_lines.append((clean_line, color))
                            
                            if parsed_lines:
                                self._add_log_message_bulk(parsed_lines)
                                
                except Exception as e:
                    msg_template = self.locale_manager.get_string("diagnostics_view.log_read_error")
                    self._add_log_message_bulk([ (msg_template.format(error=e), ft.Colors.RED) ])
                    current_log_file = None
                    time.sleep(3)
            else:
                time.sleep(3)
    # --- END OF RESTORED CONTENT ---