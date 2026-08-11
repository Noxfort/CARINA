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

# File: ui/clients/control_client.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o ControlClient.

Esta versão foi atualizada para se conectar ao LiveDataProvider, criando
um 'feedback loop' que permite que os comandos da UI (como mudança de
tempos) afetem a simulação de dados mock em tempo real.
"""

import logging
from typing import TYPE_CHECKING

# We use TYPE_CHECKING to avoid circular import, a good practice
if TYPE_CHECKING:
    from ui.providers.live_data_provider import LiveDataProvider

class ControlClient:
    """
    Traduz ações da UI em comandos e os envia para o backend.
    """
    def __init__(self, live_data_provider: 'LiveDataProvider' = None):
        """
        Inicializa o cliente de controle.

        Args:
            live_data_provider: Uma referência opcional ao provedor de dados
                                para o feedback loop da UI.
        """
        self.live_data_provider = live_data_provider
        logging.info("[ControlClient] Cliente de comando inicializado (Modo Stub).")

    def set_global_mode(self, mode: str):
        """
        Envia um comando para alterar o modo de operação global do sistema.
        """
        print(f">>> [COMANDO UI]: Mudar modo global para '{mode.upper()}'")
        logging.info(f"--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Mudar modo global para '{mode.upper()}'")
        pass

    def set_semaphore_override(self, semaphore_id: str, state: str):
        """
        Envia um comando para aplicar um override em um semáforo específico.
        """
        print(f">>> [COMANDO UI]: Override no semáforo '{semaphore_id}' para o estado '{state.upper()}'")
        logging.info(f"--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Aplicar override no semáforo '{semaphore_id}' para o estado '{state.upper()}'")
        if self.live_data_provider:
            command = {
                "type": "set_semaphore_override",
                "payload": {
                    "semaphore_id": semaphore_id,
                    "state": state
                }
            }
            self.live_data_provider.send_command_to_backend(command)

    def set_street_override(self, street_id: str, state: str):
        """
        Envia um comando para bloquear ou desbloquear uma rua.
        """
        print(f">>> [COMANDO UI]: Override na rua '{street_id}' para o estado '{state.upper()}'")
        logging.info(f"--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Aplicar override na rua '{street_id}' para o estado '{state.upper()}'")
        if self.live_data_provider:
            command = {
                "type": "set_street_override",
                "payload": {
                    "street_id": street_id,
                    "state": state
                }
            }
            self.live_data_provider.send_command_to_backend(command)

    def trigger_analysis(self):
        """
        Envia um comando para disparar a análise de planejamento imediatamente.
        """
        logging.info("--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Disparar análise de planejamento")
        if self.live_data_provider:
            command = {
                "type": "trigger_analysis",
                "payload": {}
            }
            self.live_data_provider.send_command_to_backend(command)

    def trigger_mfd_analysis(self):
        """
        Envia um comando para disparar a análise de otimização MFD imediatamente.
        """
        logging.info("--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Disparar análise MFD")
        if self.live_data_provider:
            command = {
                "type": "trigger_mfd_analysis",
                "payload": {}
            }
            self.live_data_provider.send_command_to_backend(command)
        