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

# File: ui/widgets/plot_viewer_widget.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import flet as ft
import os
from ui.handlers.locale_manager import LocaleManager

class PlotViewerWidget(ft.Container):
    """
    Widget dedicated to displaying the XAI chart (image).
    Handles hiding/showing the image and refreshing the source properly.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__()
        self.locale_manager = locale_manager
        
        # --- FIX: Renamed from self.image to self.plot_image to avoid collision ---
        # ft.Container already has a property named 'image' for background images.
        # Overwriting it with a Control causes a Circular Reference error during serialization.
        self.plot_image = ft.Image(
            src="",
            fit=ft.ImageFit.CONTAIN,
            visible=False,  # Starts invisible
            gapless_playback=True,
            expand=True
        )
        
        # Placeholder (Text/Icon showed when no image is loaded)
        self.placeholder_icon = ft.Icon(ft.Icons.INSERT_CHART_OUTLINED, size=64, color=ft.Colors.GREY_700)
        self.placeholder_text = ft.Text(
            value=self.locale_manager.get_string("plot_viewer.no_data", default="No analysis generated yet."),
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

        # Layout
        self.content = ft.Stack(
            controls=[
                self.placeholder_col,
                self.plot_image  # Updated reference
            ],
            alignment=ft.alignment.center
        )
        
        # styles
        self.expand = True
        self.bgcolor = ft.Colors.BLACK12
        self.border = ft.border.all(1, ft.Colors.GREY_800)
        self.border_radius = 8
        self.padding = 20
        self.alignment = ft.alignment.center

    def load_plot(self, image_path: str):
        """
        Updates the displayed image.
        If image_path is None or invalid, shows the placeholder.
        """
        if image_path and os.path.exists(image_path):
            # Update image source
            self.plot_image.src = os.path.abspath(image_path)
            self.plot_image.visible = True
            
            # Hide placeholder
            self.placeholder_col.visible = False
        else:
            # clear image
            self.plot_image.src = ""
            self.plot_image.visible = False
            
            # Show placeholder
            self.placeholder_col.visible = True
        
        # Force UI update for this specific widget
        self.update()

    def update_translations(self, locale_manager: LocaleManager):
        """Refreshes text translations."""
        self.locale_manager = locale_manager
        self.placeholder_text.value = locale_manager.get_string("plot_viewer.no_data", default="No analysis generated yet.")
        self.update()