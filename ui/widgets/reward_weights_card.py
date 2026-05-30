# File: ui/widgets/reward_weights_card.py (MODIFIED FOR TRANSLATION SUPPORT)
# Author: Gabriel Moraes
# Date: September 29, 2025

"""
Define o RewardWeightsCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager

class RewardWeightsCard(ft.Card):
    """
    Um Card que encapsula as configurações de pesos de recompensa.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.description_text = ft.Text(italic=True, size=12, color=ft.Colors.WHITE70)
        
        self.tf_weight_waiting_time = ft.TextField(
            value=initial_values.get('weight_waiting_time', '-2.0'),
            input_filter=numeric_filter
        )
        self.tf_weight_flow = ft.TextField(
            value=initial_values.get('weight_flow', '2.0'),
            input_filter=numeric_filter
        )
        self.tf_weight_emergency_brake = ft.TextField(
            value=initial_values.get('weight_emergency_brake', '-50.0'),
            input_filter=numeric_filter
        )
        self.tf_weight_teleport = ft.TextField(
            value=initial_values.get('weight_teleport', '-300.0'),
            input_filter=numeric_filter
        )
        
        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.description_text,
                self.tf_weight_waiting_time,
                self.tf_weight_flow,
                self.tf_weight_emergency_brake,
                self.tf_weight_teleport
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'weight_waiting_time': self.tf_weight_waiting_time.value,
            'weight_flow': self.tf_weight_flow.value,
            'weight_emergency_brake': self.tf_weight_emergency_brake.value,
            'weight_teleport': self.tf_weight_teleport.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.tf_weight_waiting_time.value = values.get('weight_waiting_time', '-2.0')
        self.tf_weight_flow.value = values.get('weight_flow', '2.0')
        self.tf_weight_emergency_brake.value = values.get('weight_emergency_brake', '-50.0')
        self.tf_weight_teleport.value = values.get('weight_teleport', '-300.0')
        if self.page: self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.reward_weights_card.title")
        self.description_text.value = lm.get_string("settings_view.reward_weights_card.description")
        
        self.tf_weight_waiting_time.label = lm.get_string("settings_view.reward_weights_card.waiting_time_label")
        self.tf_weight_waiting_time.tooltip = lm.get_string("settings_view.reward_weights_card.waiting_time_tooltip")
        
        self.tf_weight_flow.label = lm.get_string("settings_view.reward_weights_card.flow_label")
        self.tf_weight_flow.tooltip = lm.get_string("settings_view.reward_weights_card.flow_tooltip")
        
        self.tf_weight_emergency_brake.label = lm.get_string("settings_view.reward_weights_card.emergency_brake_label")
        self.tf_weight_emergency_brake.tooltip = lm.get_string("settings_view.reward_weights_card.emergency_brake_tooltip")
        
        self.tf_weight_teleport.label = lm.get_string("settings_view.reward_weights_card.teleport_label")
        self.tf_weight_teleport.tooltip = lm.get_string("settings_view.reward_weights_card.teleport_tooltip")
        
        if self.page: self.update()