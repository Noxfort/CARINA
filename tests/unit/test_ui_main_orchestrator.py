# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# File: tests/unit/test_ui_main_orchestrator.py

import pytest
from unittest.mock import MagicMock
import flet as ft

from ui.views.error_view import ErrorView
from ui.builders.settings_dialog_builder import SettingsDialogBuilder
from ui.managers.navigation_manager import NavigationManager


def test_error_view_render():
    """Verify ErrorView renders error card without throwing exceptions."""
    mock_page = MagicMock()
    mock_page.overlay = []
    
    restart_called = False
    def on_restart(e):
        nonlocal restart_called
        restart_called = True

    ErrorView.render_error_card(mock_page, "Traceback (most recent call last): test", on_restart)
    assert mock_page.clean.called
    assert mock_page.add.called
    assert mock_page.update.called


def test_settings_dialog_builder():
    """Verify SettingsDialogBuilder builds dialog and returns open callback."""
    mock_page = MagicMock()
    mock_page.overlay = []

    mock_lm = MagicMock()
    mock_lm.get_string.side_effect = lambda key, default=None, **kwargs: default or key

    mock_security = MagicMock()
    mock_settings_view = ft.Container()
    mock_client = MagicMock()

    dialog, open_cb = SettingsDialogBuilder.build_settings_dialog(
        page=mock_page,
        locale_manager=mock_lm,
        security_ui=mock_security,
        settings_view=mock_settings_view,
        settings_client=mock_client
    )

    assert dialog is not None
    assert len(mock_page.overlay) == 1
    assert callable(open_cb)


def test_navigation_manager():
    """Verify NavigationManager constructs AppBar, Tabs, and applies translations."""
    mock_page = MagicMock()
    mock_lm = MagicMock()
    mock_lm.get_string.side_effect = lambda key, default=None, **kwargs: default or key

    mock_dash = MagicMock()
    mock_plan = MagicMock()
    mock_diag = MagicMock()
    mock_set_view = MagicMock()
    mock_dialog = MagicMock()

    nav = NavigationManager(
        page=mock_page,
        locale_manager=mock_lm,
        dashboard_view=mock_dash,
        planning_view=mock_plan,
        diagnostics_view=mock_diag,
        settings_view=mock_set_view,
        settings_dialog=mock_dialog,
        open_settings_callback=lambda e: None
    )

    assert nav.appbar is not None
    assert nav.tabs is not None
    assert len(nav.tabs.tabs) == 3

    nav.apply_translations()
    assert mock_page.update.called
