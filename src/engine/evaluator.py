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

# File: src/engine/evaluator.py (FIXED: Correct reference to policy_net)
# Author: Gabriel Moraes
# Date: November 22, 2025

"""
Defines the ValidationEvaluator class, responsible for evaluating an agent's
performance in an environment, without the agent learning during the evaluation.
"""
import torch
import logging
from collections import deque
import numpy as np

class ValidationEvaluator:
    """
    Executes validation episodes to measure the agents' generalization performance.
    """
    def __init__(self, settings):
        """
        Inicializa o Avaliador.
        :param settings: As configurações globais do projeto.
        """
        self.settings = settings
        self.sequence_length = self.settings.getint('AI_TRAINING', 'sequence_length', fallback=4)
        self.state_history = {}
        logging.info("[EVAL] Módulo ValidationEvaluator criado.")

    def _initialize_state_history(self, initial_states):
        """Fills the history with zeroed states to form the first sequence."""
        self.state_history.clear()
        for tl_id, state in initial_states.items():
            if state:
                history = deque(maxlen=self.sequence_length)
                # Creates a zeroed state with the same size as the observed state
                zero_state = np.zeros_like(state) if isinstance(state, (list, np.ndarray)) else [0.0]*len(state)
                for _ in range(self.sequence_length):
                    history.append(zero_state)
                self.state_history[tl_id] = history

    def evaluate(self, agents: dict, env, num_episodes: int) -> float:
        """
        Runs a number of validation episodes and returns the average reward.
        :param agents: The dictionary of agents to be evaluated.
        :param env: The agnostic Environment instance to be used for validation.
        :param num_episodes: The number of episodes to run.
        :return: The total average reward per episode.
        """
        logging.info(f"[EVAL] Iniciando ciclo de validação para {num_episodes} episódio(s).")

        # Puts policy_net in evaluation mode
        for agent in agents.values():
            if hasattr(agent, 'policy_net'):
                agent.policy_net.eval()

        cycle_rewards = []
        episode_max_steps = self.settings.getint('AI_TRAINING', 'episode_max_steps', fallback=5000)

        for i_episode in range(num_episodes):
            env.reset()
            current_states = env.get_global_state()
            if not current_states:
                logging.warning(f"[EVAL] Ambiente retornou estado inicial vazio no episódio {i_episode+1}.")
                continue
                
            self._initialize_state_history(current_states)
            
            episode_reward = 0
            step = 0
            done = False

            while not done and step < episode_max_steps:
                actions_to_apply = {}
                for tl_id, agent in agents.items():
                    state = current_states.get(tl_id, [])
                    if not state: continue
                    
                    if tl_id in self.state_history:
                        self.state_history[tl_id].append(state)
                        state_sequence = list(self.state_history[tl_id])
                        
                        state_tensor = torch.tensor([state_sequence], dtype=torch.float32).to(agent.device)
                        action, _, _, _ = agent.choose_action(state_tensor)
                        actions_to_apply[tl_id] = action.item()

                next_states, rewards, done = env.step(actions=actions_to_apply)
                
                if rewards:
                    episode_reward += sum(rewards.values())
                    
                if next_states:
                    current_states = next_states
                    
                step += 1
            
            cycle_rewards.append(episode_reward)
            logging.info(f"[EVAL] Episódio de validação {i_episode+1}/{num_episodes} finalizado após {step} passos. Recompensa: {episode_reward:.2f}")

        # Puts policy_net back into training mode
        for agent in agents.values():
            if hasattr(agent, 'policy_net'):
                agent.policy_net.train()

        average_reward = np.mean(cycle_rewards) if cycle_rewards else 0
        logging.info(f"[EVAL] Ciclo de validação concluído. Recompensa média: {average_reward:.2f}")

        return average_reward