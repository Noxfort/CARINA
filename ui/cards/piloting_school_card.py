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

# File: ui/widgets/piloting_school_card.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o PilotingSchoolCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager

class PilotingSchoolCard(ft.Card):
    """
    Um Card que encapsula as configurações da Escola de Pilotagem.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_child_phase_episodes = ft.TextField(
            value=initial_values.get('child_phase_episodes', '1'),
            input_filter=numeric_filter
        )
        self.tf_child_promotion_max_entropy = ft.TextField(
            value=initial_values.get('child_promotion_max_entropy', '2.0'),
            input_filter=numeric_filter
        )
        self.tf_teen_phase_min_episodes = ft.TextField(
            value=initial_values.get('teen_phase_min_episodes', '1'),
            input_filter=numeric_filter
        )
        self.tf_performance_check_window = ft.TextField(
            value=initial_values.get('performance_check_window', '1'),
            input_filter=numeric_filter
        )
        self.tf_calibration_window_size = ft.TextField(
            value=initial_values.get('calibration_window_size', '10'),
            input_filter=numeric_filter
        )

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.tf_child_phase_episodes,
                self.tf_child_promotion_max_entropy,
                self.tf_teen_phase_min_episodes,
                self.tf_performance_check_window,
                self.tf_calibration_window_size
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'child_phase_episodes': self.tf_child_phase_episodes.value,
            'child_promotion_max_entropy': self.tf_child_promotion_max_entropy.value,
            'teen_phase_min_episodes': self.tf_teen_phase_min_episodes.value,
            'performance_check_window': self.tf_performance_check_window.value,
            'calibration_window_size': self.tf_calibration_window_size.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.tf_child_phase_episodes.value = values.get('child_phase_episodes', '1')
        self.tf_child_promotion_max_entropy.value = values.get('child_promotion_max_entropy', '2.0')
        self.tf_teen_phase_min_episodes.value = values.get('teen_phase_min_episodes', '1')
        self.tf_performance_check_window.value = values.get('performance_check_window', '1')
        self.tf_calibration_window_size.value = values.get('calibration_window_size', '10')
        if self.page: self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.piloting_school_card.title")
        self.tf_child_phase_episodes.label = lm.get_string("settings_view.piloting_school_card.child_phase_duration")
        self.tf_child_promotion_max_entropy.label = lm.get_string("settings_view.piloting_school_card.child_promotion_entropy")
        self.tf_teen_phase_min_episodes.label = lm.get_string("settings_view.piloting_school_card.teen_phase_duration")
        self.tf_performance_check_window.label = lm.get_string("settings_view.piloting_school_card.performance_window")
        self.tf_calibration_window_size.label = lm.get_string("settings_view.piloting_school_card.calibration_window")
        if self.page: self.update()