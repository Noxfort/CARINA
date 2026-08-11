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

# File: tests/unit/test_planning_view.py
# Author: Gabriel Moraes
# Date: 2026-07-10

import pytest
from unittest.mock import MagicMock, patch
import flet as ft
from ui.views.planning_view import PlanningView

@patch('ui.views.planning_view.InfrastructureClient')
@patch('ui.views.planning_view.InteractiveMap')
def test_planning_view_process_analysis_response_no_change(mock_map, mock_infra_client):
    """
    Verifies that when an analysis response is received with no significant change,
    the save_report_button is enabled and status text is updated appropriately.
    """
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"
    
    view = PlanningView(locale_manager=mock_locale_manager)
    view.page = MagicMock()
    view.update = MagicMock()
    
    response = {
        "status": "success",
        "report_content": "Mock report content",
        "analysis_results": {"node1": "recommendation"},
        "significant_change": False
    }
    
    view._process_analysis_response(response)
    
    # Assert report content is stored
    assert view.last_report_content == "Mock report content"
    
    # Assert save report button is enabled
    assert view.save_report_button.disabled is False
    assert view.status_text.value == "Mock_planning_view.status_loaded_no_change"


@patch('ui.views.planning_view.InfrastructureClient')
@patch('ui.views.planning_view.InteractiveMap')
def test_planning_view_save_report_click_triggers_save(mock_map, mock_infra_client):
    """
    Verifies that clicking save report triggers the file picker.
    """
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"
    
    view = PlanningView(locale_manager=mock_locale_manager)
    view.page = MagicMock()
    view.update = MagicMock()
    view.file_picker = MagicMock()
    
    # Mocking last report content
    view.last_report_content = "Mock report content"
    
    view._save_report_click(None)
    
    # Assert file picker save_file was triggered
    view.file_picker.save_file.assert_called_once()
