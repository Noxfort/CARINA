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

# File: ui/widgets/xai_viewer_widget.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import flet as ft
import os
import time
import json
import threading
import logging
from ui.handlers.locale_manager import LocaleManager
from ui.widgets.explanation_viewer_widget import ExplanationViewerWidget
from ui.widgets.plot_viewer_widget import PlotViewerWidget

class XaiViewerWidget(ft.Column):
    """
    Main widget for the XAI (Explainable AI) tab.
    Manages the full cycle: Request -> Wait -> Display.
    """
    def __init__(self, locale_manager: LocaleManager, results_dir: str):
        super().__init__()
        self.locale_manager = locale_manager
        self.results_dir = results_dir
        self.selected_agent_id = None
        
        # Column Configuration
        self.expand = True
        self.spacing = 10
        
        # UI Components
        self.agent_dropdown = ft.Dropdown(
            label="Select Agent",
            width=300,
            options=[],
            on_change=self._on_agent_selected,
            prefix_icon=ft.Icons.TRAFFIC_ROUNDED
        )
        
        self.analyze_btn = ft.ElevatedButton(
            text="Request XAI Analysis",
            icon=ft.Icons.ANALYTICS_ROUNDED,
            on_click=self._on_analyze_click,
            disabled=True
        )
        
        self.status_text = ft.Text(value="", color=ft.Colors.GREY_400, size=12)
        
        # Visualization Sub-widgets
        self.plot_viewer = PlotViewerWidget(locale_manager)
        self.explanation_viewer = ExplanationViewerWidget(locale_manager)
        
        # Defines children controls
        self.controls = [
            ft.Row(
                controls=[self.agent_dropdown, self.analyze_btn],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            self.status_text,
            ft.Divider(),
            ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text=self.locale_manager.get_string("xai_viewer.tab_chart", default="Sensor Importance (Chart)"),
                        icon=ft.Icons.BAR_CHART_ROUNDED,
                        content=ft.Container(
                            content=self.plot_viewer,
                            padding=10
                        )
                    ),
                    ft.Tab(
                        text=self.locale_manager.get_string("xai_viewer.tab_text", default="Detailed Report (Text)"),
                        icon=ft.Icons.DESCRIPTION_ROUNDED,
                        content=ft.Container(
                            content=self.explanation_viewer,
                            padding=10
                        )
                    ),
                ],
                expand=True
            )
        ]

    def update_translations(self, locale_manager: LocaleManager):
        self.locale_manager = locale_manager
        self.agent_dropdown.label = locale_manager.get_string("xai_viewer.agent_select_label", default="Select Agent")
        self.analyze_btn.text = locale_manager.get_string("xai_viewer.analyze_btn", default="Run XAI Analysis")
        
        # Tabs
        self.controls[3].tabs[0].text = locale_manager.get_string("xai_viewer.tab_chart", default="Sensor Importance (Chart)")
        self.controls[3].tabs[1].text = locale_manager.get_string("xai_viewer.tab_text", default="Detailed Report (Text)")
        
        if self.page: self.update()

    def update_agent_list(self, agent_ids: list):
        current = self.agent_dropdown.value
        self.agent_dropdown.options = [ft.dropdown.Option(key=str(aid), text=f"Agent {aid}") for aid in agent_ids]
        if current not in agent_ids: self.agent_dropdown.value = None
        self.analyze_btn.disabled = self.agent_dropdown.value is None
        if self.page: self.agent_dropdown.update()
        if self.page: self.analyze_btn.update()

    def _on_agent_selected(self, e):
        self.selected_agent_id = self.agent_dropdown.value
        self.analyze_btn.disabled = self.selected_agent_id is None
        self.analyze_btn.update()

    def _on_analyze_click(self, e):
        if not self.selected_agent_id: return
        
        agent_id = self.selected_agent_id
        
        # 1. Immediate UI Feedback
        self.analyze_btn.disabled = True
        
        # Clear previous results
        self.plot_viewer.load_plot(None) 
        self.explanation_viewer.set_text(None) 
        
        self.status_text.value = self.locale_manager.get_string("xai_viewer.status_requesting", default="Requesting...", agent_id=agent_id)
        self.status_text.color = ft.Colors.ORANGE_400
        self.update()

        # 2. Create Request on Disk
        try:
            requests_dir = os.path.join(self.results_dir, "captum", "requests")
            os.makedirs(requests_dir, exist_ok=True)
            req_file = os.path.join(requests_dir, f"{agent_id}.request")
            
            # Clean up old responses first
            response_file = os.path.join(self.results_dir, "captum", "responses", f"{agent_id}.response")
            if os.path.exists(response_file):
                try:
                    os.remove(response_file)
                except OSError as e:
                    logging.warning(f"[XAI_WIDGET] Could not delete old response file: {e}")

            with open(req_file, "w", encoding="utf-8") as f:
                json.dump({"agent_id": agent_id, "timestamp": time.time()}, f)
                
            logging.info(f"[XAI_WIDGET] Request created: {req_file}")
            
            # 3. Start Monitoring Thread (Polling)
            threading.Thread(target=self._monitor_response, args=(agent_id,), daemon=True).start()
            
        except Exception as ex:
            self.status_text.value = f"Error creating request: {ex}"
            self.status_text.color = ft.Colors.RED_400
            self.analyze_btn.disabled = False
            self.update()

    def _monitor_response(self, agent_id: str):
        """Thread that watches for the response file."""
        response_file = os.path.join(self.results_dir, "captum", "responses", f"{agent_id}.response")
        
        # --- TIMEOUT ADJUSTMENT ---
        # Increased to 300 seconds (5 minutes) to account for:
        # 1.Captum Analysis (CPU)
        # 2. LLM Model Loading (HDD -> VRAM)
        # 3. LLM Inference (Token Generation)
        timeout = 300 
        
        start_time = time.time()
        logging.info(f"[XAI_WIDGET] Waiting for response at: {response_file} (Timeout: {timeout}s)")

        while (time.time() - start_time) < timeout:
            if not self.page: break 

            if os.path.exists(response_file):
                try:
                    time.sleep(0.5) # Wait for write completion
                    
                    with open(response_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if data.get("status") == "complete":
                        img_path = data.get("image_path")
                        txt_path = data.get("text_path")
                        
                        # Validate existence
                        if img_path and os.path.exists(img_path) and txt_path and os.path.exists(txt_path):
                            logging.info(f"[XAI_WIDGET] Success! Loading results.")
                            self._safe_update_ui(img_path, txt_path, success=True)
                            
                            try: os.remove(response_file)
                            except: pass
                            return
                        else:
                            logging.warning("[XAI_WIDGET] JSON found, but media files are missing. Waiting...")
                    else:
                        err_msg = data.get("message", "Unknown error")
                        self._safe_update_ui(None, err_msg, success=False)
                        try: os.remove(response_file)
                        except: pass
                        return

                except json.JSONDecodeError:
                    pass 
                except Exception as e:
                    logging.error(f"[XAI_WIDGET] Error reading response: {e}")
            
            time.sleep(1.0)

        # Timeout Logic
        elapsed = time.time() - start_time
        logging.error(f"[XAI_WIDGET] Timeout waiting for response after {elapsed:.1f}s.")
        self._safe_update_ui(None, self.locale_manager.get_string("xai_viewer.status_timeout", default="Timeout ({seconds}s).", seconds=int(elapsed)), success=False)

    def _safe_update_ui(self, img_path, text_content, success):
        """Updates the UI safely (Thread-Safe Wrapper)."""
        if not self.page: return
        
        def update_action():
            self.analyze_btn.disabled = False
            
            if success:
                self.plot_viewer.load_plot(img_path)
                
                try:
                    with open(text_content, 'r', encoding='utf-8') as f:
                        full_text = f.read()
                    self.explanation_viewer.set_text(full_text)
                except:
                    self.explanation_viewer.set_text(f"Error reading text: {text_content}")

                self.status_text.value = self.locale_manager.get_string("xai_viewer.status_success", default="Analysis completed successfully!")
                self.status_text.color = ft.Colors.GREEN_400
            else:
                self.status_text.value = self.locale_manager.get_string("xai_viewer.status_error", default="Failed: {error}", error=text_content)
                self.status_text.color = ft.Colors.RED_400
            
            self.update()
            if self.page: self.page.update()

        update_action()