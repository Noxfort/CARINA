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

# File: ui/views/settings_configurator.py
# Author: Gabriel Moraes
# Date: 2026-06-10

import flet as ft
from ui.views.settings_view import SettingsView
from ui.handlers.settings_handler import SettingsHandler
from ui.handlers.hardware_settings_handler import HardwareSettingsHandler
from ui.handlers.account_settings_handler import AccountSettingsHandler
from ui.handlers.monitor_settings_handler import MonitorSettingsHandler
from src.controller.connection_manager import HardwareConnectionManager

from ui.cards.general_settings_card import GeneralSettingsCard
from ui.cards.traffic_rules_card import TrafficRulesCard
from ui.cards.dashboard_settings_card import DashboardSettingsCard
from ui.cards.advanced_ppo_card import AdvancedPPOCard
from ui.cards.advanced_dqn_card import AdvancedDQNCard
from ui.cards.advanced_system_card import AdvancedSystemCard
from ui.cards.piloting_school_card import PilotingSchoolCard
from ui.cards.reward_weights_card import RewardWeightsCard
from ui.cards.monitor_settings_card import MonitorSettingsCard
from ui.cards.database_settings_card import DatabaseSettingsCard
from ui.cards.account_settings_card import AccountSettingsCard
from ui.cards.hardware_connection_card import HardwareConnectionCard
from ui.cards.report_formatting_card import ReportFormattingCard

def build_settings_view(locale_manager, settings_client):
    """
    OCP: Constructs and wires the tabs and cards for SettingsView. 
    To add a new setting tab or card, modify only this builder.
    """
    handler = SettingsHandler()
    initial_settings = handler.get_current_settings()

    # Handlers
    hardware_handler = HardwareSettingsHandler(HardwareConnectionManager.get_instance(), settings_client)
    account_handler = AccountSettingsHandler(settings_client)
    monitor_handler = MonitorSettingsHandler(settings_client)
    
    # Cards
    formatting_card = ReportFormattingCard(initial_settings)
    general_card = GeneralSettingsCard(initial_settings)
    traffic_rules_card = TrafficRulesCard(initial_settings)
    dashboard_card = DashboardSettingsCard(initial_settings)
    advanced_ppo_card = AdvancedPPOCard(initial_settings)
    advanced_dqn_card = AdvancedDQNCard(initial_settings)
    advanced_system_card = AdvancedSystemCard(initial_settings)
    piloting_school_card = PilotingSchoolCard(initial_settings)
    reward_weights_card = RewardWeightsCard(initial_settings)
    
    monitor_card = MonitorSettingsCard(
        initial_values=initial_settings,
        on_toggle_connection=monitor_handler.on_monitor_toggle
    )
    
    hardware_card = HardwareConnectionCard(
        on_import_click=hardware_handler.on_import_click,
        on_export_click=hardware_handler.on_export_click,
        on_toggle_connection=hardware_handler.on_toggle_connection
    )

    account_card = AccountSettingsCard(
        locale_manager=locale_manager,
        on_add_user=account_handler.on_add_user,
        on_remove_user=account_handler.on_remove_user,
        on_request_list=account_handler.on_request_users_list
    )

    db_card = DatabaseSettingsCard(
        initial_values=initial_settings,
        on_toggle_connection=None # Wired up via lambda below
    )

    warning_text = ft.Text(size=12, expand=True, italic=True)

    tab_definitions = [
        {
            "icon": ft.Icons.TUNE_ROUNDED,
            "title_key": "settings_view.tab_general",
            "default_title": "General",
            "cards": [general_card, db_card, traffic_rules_card, dashboard_card]
        },
        {
            "icon": ft.Icons.HUB_ROUNDED,
            "title_key": "settings_view.tab_advanced",
            "default_title": "Advanced",
            "cards": [
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.AMBER), 
                    border=ft.border.all(1, ft.Colors.AMBER),
                    border_radius=10, padding=15,
                    content=ft.Row([
                        ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.AMBER),
                        warning_text
                    ])
                ),
                advanced_ppo_card, advanced_dqn_card,
                piloting_school_card, reward_weights_card,
                advanced_system_card
            ]
        },
        {
            "icon": ft.Icons.CABLE_ROUNDED,
            "title_key": "settings_view.tab_hardware",
            "default_title": "Hardware",
            "is_dynamic_fallback": True,
            "cards": [hardware_card]
        },
        {
            "icon": ft.Icons.MONITOR_HEART_ROUNDED,
            "title_key": "settings_view.tab_monitor",
            "default_title": "Monitor",
            "is_dynamic_fallback": True,
            "cards": [monitor_card]
        },
        {
            "icon": ft.Icons.MANAGE_ACCOUNTS_ROUNDED,
            "title_key": "settings_view.tab_accounts",
            "default_title": "Contas",
            "cards": [account_card]
        },
        {
            "icon": ft.Icons.PRINT_ROUNDED,
            "title_key": "settings_view.tab_formatting",
            "default_title": "Formatação",
            "cards": [formatting_card]
        }
    ]

    view = SettingsView(
        locale_manager=locale_manager,
        settings_client=settings_client,
        tab_definitions=tab_definitions,
        warning_text_ref=warning_text
    )

    # Wire up the db toggle to the view's save mechanism
    db_card.on_toggle_connection = lambda is_connected: view.save_silently()

    view.hardware_handler = hardware_handler
    view.hardware_card = hardware_card
    view.account_card = account_card

    return view
