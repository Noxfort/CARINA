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

# File: ui/clients/settings_client.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Define o SettingsClient, responsável por comunicar as alterações de
configuração da UI para o backend.
"""

import logging
from typing import Dict, Any, TYPE_CHECKING

# Prevents circular import, allowing type annotation
if TYPE_CHECKING:
    from ui.providers.live_data_provider import LiveDataProvider

class SettingsClient:
    """
    Envia comandos de atualização de configurações para o backend através
    do provedor de dados em tempo real (WebSocket).
    """
    def __init__(self, live_data_provider: 'LiveDataProvider'):
        """
        Inicializa o cliente de configurações.

        Args:
            live_data_provider: A instância do LiveDataProvider que gerencia a
                                conexão WebSocket com o backend.
        """
        self.live_data_provider = live_data_provider
        logging.info("[SettingsClient] Cliente de configurações inicializado.")

    def save_settings(self, settings_payload: Dict[str, Any]):
        """
        Cria um comando padronizado e o envia para o backend para salvar
        as novas configurações.

        Args:
            settings_payload (Dict[str, Any]): Um dicionário contendo as
                                               configurações a serem salvas.
        """
        if not self.live_data_provider:
            logging.error("[SettingsClient] LiveDataProvider não foi fornecido. Impossível enviar configurações.")
            return

        command = {
            "type": "save_settings",
            "payload": settings_payload
        }
        
        self.live_data_provider.send_command_to_backend(command)
        logging.info(f"[SettingsClient] Comando 'save_settings' enviado para o backend com {len(settings_payload)} chaves.")

    def send_command(self, cmd_type: str, payload: Dict[str, Any]):
        """
        Envia um comando genérico para o backend.
        
        Args:
            cmd_type (str): O tipo de comando (ex: 'set_hardware_connection').
            payload (Dict[str, Any]): Os dados associados ao comando.
        """
        if not self.live_data_provider:
            logging.error(f"[SettingsClient] LiveDataProvider não foi fornecido. Impossível enviar comando '{cmd_type}'.")
            return

        command = {
            "type": cmd_type,
            "payload": payload
        }
        
        self.live_data_provider.send_command_to_backend(command)
        logging.info(f"[SettingsClient] Comando '{cmd_type}' enviado para o backend.")