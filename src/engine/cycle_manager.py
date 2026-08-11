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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/engine/cycle_manager.py
# Author: Gabriel Moraes
# Date: February 17, 2026

import os
import logging
import numpy as np
import torch
from multiprocessing.connection import Connection
from typing import Dict, Any

from utils.paths import get_base_output_dir
from core.enums import Maturity

class CycleManager:
    """
    Gerencia o ciclo de vida e maturação dos agentes de IA.
    Responsável por checkpoints periódicos, agregação de métricas e
    sincronização de estado de evolução (child -> teen -> adult) com a UI.
    """

    def __init__(self, maturity_manager, pipe_conn: Connection):
        """
        Args:
            maturity_manager: Instance of the maturity rules manager.
            pipe_conn: Connection (Pipe) to send updates to the UI.
        """
        self.maturity_manager = maturity_manager
        self.pipe_conn = pipe_conn

    def evaluate_cycle(self, step_counter: int, agents: Dict, accumulated_metrics: Dict, mfd_efficiency: float = 0.0):
        """
        Executa a rotina de fim de ciclo:
        1. Calcula médias de desempenho.
        2. Verifica promoções de nível (IMPORTANTE: Antes de salvar).
        3. Salva checkpoints (Agora com o estado atualizado).
        4. Notifica a UI.

        Args:
            step_counter (int): Passo atual da simulação.
            agents (Dict): Dicionário de agentes ativos.
            accumulated_metrics (Dict): Métricas brutas coletadas durante o episódio.
        """
        logging.info(f"--- FIM DO CICLO (Passo {step_counter}) | AVALIAÇÃO DE MATURIDADE ---")
        
        # 1. Metrics Aggregation
        agent_metrics_summary = self._aggregate_metrics(accumulated_metrics)
        
        # Clear metrics for the next cycle
        accumulated_metrics.clear()
        
        # 2. Promotion Check (Updates status in MaturityManager)
        # We run this BEFORE saving the checkpoint to ensure the promotion
        # be persisted to disk immediately.
        promotion_occurred = self.maturity_manager.check_and_promote_agents(agent_metrics_summary, mfd_efficiency)
        
        # 3. Physical Checkpoints (Now it will save with the ALREADY updated phase)
        self._save_checkpoints(agents)
        
        # Clear agent memory buffers to prevent RAM leak in HFT mode
        for agent in agents.values():
            if hasattr(agent, 'memory'):
                agent.memory.clear()
                
        # Force empty PyTorch CUDA cache if GPU is available to prevent fragmentation/leak
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # 4. Sync with UI
        if promotion_occurred:
            self._sync_maturity_state(step_counter)

    def _save_checkpoints(self, agents: Dict):
        """Saves the current state of neural networks and their maturity phase to disk."""
        try:
            results_base = get_base_output_dir()
            checkpoints_dir = os.path.join(results_base, "results", "hft_live_session", "checkpoints")
            os.makedirs(checkpoints_dir, exist_ok=True)
            
            for tl_id, agent in agents.items():
                # Retrieves the agent's current phase (ex: Maturity.CHILD)
                # As 'check_and_promote_agents' has already run, this value will be updated.
                current_maturity = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
                maturity_str = current_maturity.name # "CHILD", "TEEN", "ADULT"
                
                ckpt_path = os.path.join(checkpoints_dir, f"agent_{tl_id}.pth")
                
                # Explicitly passes the phase to the agent to save it within the .pth file
                agent.save_checkpoint(ckpt_path, maturity_stage=maturity_str)
                
            logging.info(f"[CHECKPOINT] Estados dos agentes atualizados no disco.")
        except Exception as e:
            logging.error(f"[CHECKPOINT] Falha ao salvar checkpoints periódicos: {e}")

    def _aggregate_metrics(self, accumulated_metrics: Dict) -> Dict:
        """Calcula a média das recompensas e entropias acumuladas."""
        summary = {}
        for tl_id, metrics in accumulated_metrics.items():
            count = metrics.get('count', 0)
            if count > 0:
                mean_reward = metrics['reward_sum'] / count
                mean_entropy = metrics['entropy_sum'] / count
            else:
                # Fallback support for lists
                rewards_list = metrics.get('rewards', [])
                entropies_list = metrics.get('entropies', [])
                mean_reward = np.mean(rewards_list) if rewards_list else 0.0
                mean_entropy = np.mean(entropies_list) if entropies_list else 0.0
            
            summary[tl_id] = {
                'reward': mean_reward,
                'entropy': mean_entropy
            }
        return summary

    def _sync_maturity_state(self, step_counter: int):
        """Sends the new maturity map to the graphical interface."""
        maturity_map = {
            aid: phase.name 
            for aid, phase in self.maturity_manager.agent_maturity.items()
        }
        
        payload = {
            'run_id': step_counter, 
            'agent_maturity': maturity_map
        }
        
        try:
            # Send 'update_maturity_state' command via custom pipe
            self.pipe_conn.send(('custom', 'update_maturity_state', (payload,), {}))
            logging.info(f"[MATURITY] Estado de maturidade sincronizado com UI.")
        except Exception as e:
            logging.error(f"[MATURITY] Erro ao sincronizar maturidade: {e}")