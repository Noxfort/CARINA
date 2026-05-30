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

# File: src/engine/state_history_manager.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import logging
from collections import deque
from typing import Dict

class StateHistoryManager:
    """
    Manages the rolling Deque buffers that form the observation horizon for Agents.
    """

    def __init__(self, sequence_length: int, n_observations: int):
        if sequence_length <= 0:
            logging.warning("[StateHistoryManager] 'sequence_length' must be > 0. Using 1.")
            self.sequence_length = 1
        else:
            self.sequence_length = sequence_length
            
        self.n_observations = n_observations
        self.history: Dict[str, deque] = {}

    def initialize_history(self, initial_states: dict, agent_ids: list):
        if not initial_states or not agent_ids:
            logging.warning("[StateHistoryManager] Initial states or agents missing.")
            return

        if self.n_observations <= 0:
            logging.error(f"[StateHistoryManager] Observation size invalid ({self.n_observations}). History not initialized.")
            return

        self.history.clear()

        for tl_id in agent_ids:
            history_deque = deque(maxlen=self.sequence_length)
            zero_state = [0.0] * self.n_observations
            
            for _ in range(self.sequence_length):
                history_deque.append(zero_state)
                
            self.history[tl_id] = history_deque

        logging.debug(f"[StateHistoryManager] Initialized history for {len(self.history)} agents.")
