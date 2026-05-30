# File: ui/clients/settings_client.py (NEW FILE)
# Author: Gabriel Moraes
# Date: October 1, 2025

"""
Define o SettingsClient, responsável por comunicar as alterações de
configuração da UI para o backend.
"""

import logging
from typing import Dict, Any, TYPE_CHECKING

# Prevents circular import, allowing type annotation
if TYPE_CHECKING:
    from ui.handlers.live_data_provider import LiveDataProvider

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