# File: ui/widgets/advanced_dqn_card.py (MODIFIED FOR TRANSLATION SUPPORT)
# Author: Gabriel Moraes
# Date: September 29, 2025

"""
Define o AdvancedDQNCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager

class AdvancedDQNCard(ft.Card):
    """
    Um Card que encapsula as configurações avançadas do Agente DQN.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_dqn_epsilon_decay = ft.TextField(
            value=initial_values.get('dqn_epsilon_decay', '30000'),
            input_filter=numeric_filter
        )
        self.tf_dqn_batch_size = ft.TextField(
            value=initial_values.get('dqn_batch_size', '128'),
            input_filter=numeric_filter
        )
        
        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.tf_dqn_epsilon_decay,
                self.tf_dqn_batch_size
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'dqn_epsilon_decay': self.tf_dqn_epsilon_decay.value,
            'dqn_batch_size': self.tf_dqn_batch_size.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.tf_dqn_epsilon_decay.value = values.get('dqn_epsilon_decay', '30000')
        self.tf_dqn_batch_size.value = values.get('dqn_batch_size', '128')
        if self.page: self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.advanced_dqn_card.title")
        self.tf_dqn_epsilon_decay.label = lm.get_string("settings_view.advanced_dqn_card.epsilon_decay")
        self.tf_dqn_batch_size.label = lm.get_string("settings_view.advanced_dqn_card.batch_size")
        if self.page: self.update()