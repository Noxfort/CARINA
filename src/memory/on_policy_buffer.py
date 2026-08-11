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

# File: src/memory/on_policy_buffer.py (NEW FILE)
# Author: Gabriel Moraes
# Date: August 19, 2025

"""
Defines the OnPolicyBuffer class.

This class, extracted from 'local_agent.py', implements a simple memory buffer,
designed for "on-policy" reinforcement learning algorithms like PPO. It collects
a batch of transitions and converts them into PyTorch tensors for the learning cycle.
"""
import torch
import numpy as np

class OnPolicyBuffer:
    """A buffer that stores transitions (state, action, etc.) for a single data collection cycle."""
    
    def __init__(self):
        """Initializes the lists that will store the trajectory data."""
        self.actions = []
        self.states = []
        self.log_probs = []
        self.rewards = []
        self.dones = []
        self.state_values = []

    def push(self, state_sequence, action, log_prob, reward, done, state_value):
        """
        Adiciona uma única transição ao buffer.

        Args:
            state_sequence: A sequência de estados que levou à decisão.
            action: A ação tomada pelo agente.
            log_prob: O log da probabilidade da ação tomada.
            reward (float): A recompensa recebida após a ação.
            done (bool): Se o episódio terminou após a ação.
            state_value: O valor do estado estimado pelo Crítico.
        """
        self.states.append(state_sequence)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.dones.append(done)
        self.state_values.append(state_value)

    def get_batch(self) -> tuple:
        """
        Converte os dados armazenados em tensores PyTorch e os retorna.
        Assume que as sequências de estado já têm tamanho uniforme.

        Returns:
            tuple: Uma tupla contendo os tensores de estados, ações, log_probs,
                   recompensas (lista), dones (lista) e valores de estado.
        """
        # Converting to numpy array first is efficient
        states_np = np.array(self.states, dtype=np.float32)
        actions_np = np.array(self.actions, dtype=np.float32)
        log_probs_np = np.array(self.log_probs, dtype=np.float32)
        state_values_np = np.array(self.state_values, dtype=np.float32)
        
        # Converts to PyTorch tensors
        states_t = torch.from_numpy(states_np)
        actions_t = torch.from_numpy(actions_np)
        log_probs_t = torch.from_numpy(log_probs_np)
        state_values_t = torch.from_numpy(state_values_np)
        
        # The squeeze() method removes dimensions of size 1, if any
        return states_t, actions_t.squeeze(), log_probs_t.squeeze(), self.rewards, self.dones, state_values_t.squeeze()

    def clear(self):
        """Limpa o buffer. Deve ser chamado após cada ciclo de aprendizado."""
        self.actions = []
        self.states = []
        self.log_probs = []
        self.rewards = []
        self.dones = []
        self.state_values = []

    def __len__(self) -> int:
        """Returns the number of transitions stored in the buffer."""
        return len(self.states)