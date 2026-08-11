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

# File: ui/views/error_view.py
# Author: Gabriel Moraes
# Date: August 10, 2026

import logging
from typing import Callable, Any
import flet as ft


class ErrorView:
    """
    Renders a fallback error UI card when a critical exception occurs during UI initialization.
    """

    @staticmethod
    def render_error_card(page: ft.Page, error_msg: str, on_restart_callback: Callable[[Any], None]) -> None:
        """
        Clears the page content and renders a styled Dark Theme error card with exception details
        and a UI restart button.

        Args:
            page (ft.Page): Active Flet page instance.
            error_msg (str): Formatted exception traceback string.
            on_restart_callback (Callable): Callback function invoked when restart button is clicked.
        """
        colors_mod = getattr(ft, "Colors", getattr(ft, "colors", None))
        icons_mod = getattr(ft, "Icons", getattr(ft, "icons", None))
        dark_mode = getattr(ft.ThemeMode, "DARK", "dark") if hasattr(ft, "ThemeMode") else "dark"

        red_color = getattr(colors_mod, "RED_400", "red") if colors_mod else "red"
        red_200 = getattr(colors_mod, "RED_200", "red") if colors_mod else "red"
        grey_300 = getattr(colors_mod, "GREY_300", "grey") if colors_mod else "grey"
        black54 = getattr(colors_mod, "BLACK54", "black") if colors_mod else "black"
        error_icon = getattr(icons_mod, "ERROR_OUTLINE_ROUNDED", None) or getattr(icons_mod, "ERROR", None)
        refresh_icon = getattr(icons_mod, "REFRESH", None)

        try:
            page.clean()
            page.title = "CARINA - Erro de Inicialização"
            page.theme_mode = dark_mode

            error_card = ft.Container(
                content=ft.Column([
                    ft.Icon(error_icon, color=red_color, size=64),
                    ft.Text("Erro ao Carregar Interface da CARINA", size=22, weight=ft.FontWeight.BOLD, color=red_color),
                    ft.Text("Ocorreu uma exceção crítica durante a montagem dos componentes da interface:", size=14, color=grey_300),
                    ft.Container(
                        content=ft.Text(error_msg, size=11, selectable=True, font_family="monospace", color=red_200),
                        bgcolor=black54,
                        padding=15,
                        border_radius=8,
                        height=300,
                    ),
                    ft.ElevatedButton(
                        "Reiniciar Interface",
                        icon=refresh_icon,
                        on_click=on_restart_callback
                    )
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                alignment=ft.alignment.center,
                expand=True,
                padding=30
            )
            page.add(error_card)
            page.update()
        except Exception as ex:
            logging.error(f"[ErrorView] Error rendering fallback error card: {ex}")
