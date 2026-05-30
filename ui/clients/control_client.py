# File: ui/clients/control_client.py (WITH CONNECTION TO DATAPROVIDER)
# Author: Gabriel Moraes
# Date: September 24, 2025

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
    from handlers.live_data_provider import LiveDataProvider

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
        pass
        
    def set_semaphore_timings(self, semaphore_id: str, green_time: str, yellow_time: str):
        """
        Envia um comando para definir novos tempos de fase para um semáforo.
        """
        print(f">>> [COMANDO UI]: Novos tempos para '{semaphore_id}': Verde={green_time}s, Amarelo={yellow_time}s")
        logging.info(f"--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Novos tempos para '{semaphore_id}': Verde={green_time}s, Amarelo={yellow_time}s")
        
        # --- FEEDBACK LOOP FOR UI SIMULATOR ---
        if self.live_data_provider:
            try:
                # Convert times to float before sending
                gt_float = float(green_time)
                yt_float = float(yellow_time)
                self.live_data_provider.update_timing_override(semaphore_id, gt_float, yt_float)
            except (ValueError, TypeError):
                logging.warning(f"[ControlClient] Valores de tempo inválidos recebidos: G={green_time}, Y={yellow_time}. Não foi possível atualizar o simulador.")
        pass