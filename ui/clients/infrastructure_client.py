# File: ui/clients/infrastructure_client.py (MODIFIED FOR ASYNCHRONOUS OPERATION)
# Author: Gabriel Moraes
# Date: September 29, 2025

"""
Define o InfrastructureClient.

Nesta versão, ele foi refatorado para operar de forma assíncrona usando uma
thread, evitando que a busca por arquivos congele a interface do usuário.
"""

import os
import json
import logging
import threading
from typing import Callable

class InfrastructureClient:
    """
    Busca o status da análise de infraestrutura em uma thread separada.
    """
    # --- CHANGE 1: The constructor now receives a callback function ---
    def __init__(self, on_complete_callback: Callable[[dict], None]):
        """
        Inicializa o cliente.

        Args:
            on_complete_callback: A função que será chamada pela thread de trabalho
                                  quando a busca pelo arquivo terminar.
        """
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.on_complete = on_complete_callback

    def _find_latest_status_file(self) -> str | None:
        """Encontra o caminho absoluto para o arquivo analysis_status.json mais recente."""
        # (The internal logic of this method remains the same)
        try:
            from src.utils.paths import get_base_output_dir
            results_dir = os.path.join(get_base_output_dir(), "results")
            if not os.path.exists(results_dir): return None
            
            ignored_dirs = {"database"}
            all_scenarios = [
                d for d in os.listdir(results_dir) 
                if os.path.isdir(os.path.join(results_dir, d)) and d not in ignored_dirs
            ]
            if not all_scenarios: return None

            latest_scenario_name = max(all_scenarios, key=lambda d: os.path.getmtime(os.path.join(results_dir, d)))
            status_file = os.path.join(
                results_dir, latest_scenario_name, "infrastructure_analysis", "analysis_status.json"
            )
            return status_file if os.path.exists(status_file) else None
        except Exception as e:
            logging.error(f"[INFRA_CLIENT] Erro ao procurar arquivo de status: {e}")
            return None

    # --- CHANGE 2: The search logic is now in a target method for the thread ---
    def _fetch_thread_target(self):
        """
        Este é o método que a thread de trabalho executa em segundo plano.
        Ele faz a busca lenta pelo arquivo e depois chama o callback com o resultado.
        """
        status_file_path = self._find_latest_status_file()
        result = {}

        if not status_file_path:
            result = {
                "status": "error",
                "message": "Nenhum relatório de análise encontrado. Execute uma simulação primeiro."
            }
        else:
            try:
                with open(status_file_path, "r", encoding="utf-8") as f:
                    result = json.load(f)
            except Exception as e:
                result = {"status": "error", "message": f"Erro ao ler o arquivo de status: {e}"}
        
        # Calls the callback provided by PlanningView with the result dictionary
        if self.on_complete:
            self.on_complete(result)

    # --- CHANGE 3: New public method to start the search ---
    def start_fetching_latest_analysis(self):
        """
        Inicia a busca pelo arquivo de análise em uma nova thread.
        Este método retorna imediatamente, sem bloquear a UI.
        """
        thread = threading.Thread(target=self._fetch_thread_target, daemon=True)
        thread.start()