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

# File: tests/unit/test_settings_view.py
# Author: Gabriel Moraes
# Date: 2026-06-24

import pytest
from unittest.mock import MagicMock
import flet as ft

def test_settings_view_file_picker_registration():
    """
    Verifies that the logo file picker is successfully registered to the page overlay
    on mounting SettingsView, and that subsequent individual card did_mount calls
    do not register duplicates.
    """
    from ui.views.settings_view import SettingsView
    from ui.cards.report_formatting_card import ReportFormattingCard
    
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.return_value = "Mock Text"
    mock_settings_client = MagicMock()
    
    initial_settings = {
        "xai_font_name": "Arial",
        "xai_font_size": 11,
        "xai_alignment": "justify",
        "xai_line_spacing": 1.15,
        "xai_margin_top": 1.0,
        "xai_margin_bottom": 1.0,
        "xai_margin_left": 1.0,
        "xai_margin_right": 1.0,
        "xai_report_title": "TEST REPORT",
        "xai_logo_path": "/some/path/logo.png",
        "xai_secretary_name": "Secretary",
        "xai_secretary_title": "Title",
        "xai_agency_name": "Agency",
        "xai_department_name": "Department",
        "xai_block_order": "header,content"
    }
    
    formatting_card = ReportFormattingCard(initial_settings)
    warning_text = ft.Text("warning")
    
    tab_definitions = [
        {
            "icon": ft.Icons.PRINT_ROUNDED,
            "title_key": "settings_view.tab_formatting",
            "default_title": "Formatação",
            "cards": [formatting_card]
        }
    ]
    
    view = SettingsView(
        locale_manager=mock_locale_manager,
        settings_client=mock_settings_client,
        tab_definitions=tab_definitions,
        warning_text_ref=warning_text
    )
    
    mock_page = MagicMock()
    mock_page.overlay = []
    
    view.page = mock_page
    formatting_card.page = mock_page
    
    # Trigger mount
    view.did_mount()
    
    # Assert picker was registered
    assert formatting_card.logo_file_picker in mock_page.overlay
    
    # Verify individual card did_mount checks to prevent duplicates
    count_before = len(mock_page.overlay)
    formatting_card.did_mount()
    assert len(mock_page.overlay) == count_before

def test_units_section_get_set_values():
    from ui.section.units_section import UnitsSection
    initial_values = {"xai_speed_unit": "km/h"}
    section = UnitsSection(initial_values)
    
    assert section.get_values()["xai_speed_unit"] == "km/h"
    
    section.set_values({"xai_speed_unit": "imperial"})
    assert section.get_values()["xai_speed_unit"] == "imperial"
    
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"
    section.update_translations(mock_locale_manager)
    assert section.lbl_units_title.value == "Mock_settings_view.formatting_card.units_title"
