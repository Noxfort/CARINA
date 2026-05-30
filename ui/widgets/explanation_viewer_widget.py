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

# File: ui/widgets/explanation_viewer_widget.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import flet as ft
from ui.handlers.locale_manager import LocaleManager

class ExplanationViewerWidget(ft.Container):
    """
    Widget dedicated to displaying the XAI text report.
    Handles hiding/showing the content and resetting the view.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__()
        self.locale_manager = locale_manager
        
        # Scrollable Text/Markdown Component
        self.report_view = ft.Markdown(
            value="",
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            visible=False, # Starts invisible
        )
        
        # Container for the report with scrolling
        self.report_container = ft.Column(
            controls=[self.report_view],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            visible=False
        )
        
        # Placeholder (shown when no report is loaded)
        self.placeholder_icon = ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=64, color=ft.Colors.GREY_700)
        self.placeholder_text = ft.Text(
            value=self.locale_manager.get_string("explanation_viewer.no_data", default="No detailed report available."),
            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER
        )
        
        self.placeholder_col = ft.Column(
            controls=[
                self.placeholder_icon,
                self.placeholder_text
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            visible=True
        )

        # Main Layout
        self.content = ft.Stack(
            controls=[
                self.placeholder_col,
                self.report_container
            ],
            alignment=ft.alignment.center
        )
        
        # styles
        self.expand = True
        self.bgcolor = ft.Colors.BLACK12
        self.border = ft.border.all(1, ft.Colors.GREY_800)
        self.border_radius = 8
        self.padding = 20
        self.alignment = ft.alignment.top_left

    def set_text(self, text: str):
        """
        Updates the displayed text.
        If text is None or empty, shows the placeholder.
        """
        if text and len(text.strip()) > 0:
            # Update text content
            self.report_view.value = text
            self.report_view.visible = True
            self.report_container.visible = True
            
            # Hide placeholder
            self.placeholder_col.visible = False
        else:
            # Clear text
            self.report_view.value = ""
            self.report_view.visible = False
            self.report_container.visible = False
            
            # Show placeholder
            self.placeholder_col.visible = True
        
        # Force UI update
        self.update()

    def update_translations(self, locale_manager: LocaleManager):
        """Refreshes text translations."""
        self.locale_manager = locale_manager
        self.placeholder_text.value = locale_manager.get_string("explanation_viewer.no_data", default="No detailed report available.")
        self.update()