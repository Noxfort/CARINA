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

# File: src/core/dynamic_entropy_calculator.py
# Author: Gabriel Moraes
# Date: May 30, 2026

import math

class DynamicEntropyCalculator:
    """
    Calculates dynamic entropy thresholds based on the time configured in the UI.
    Ensures that AI certainty requirements respect urban engineering safety ceilings.
    """

    def __init__(self, e_max: float = 1.8, e_ideal: float = 0.1) -> None:
        """
        Initializes the dynamic entropy calculator.
        
        Args:
            e_max: Safety ceiling (maximum chaos allowed for urban traffic safety).
            e_ideal: Absolute certainty limit (perfect convergence).
        """
        self.e_max = e_max
        self.e_ideal = e_ideal
        
    def calculate_threshold(self, configured_episodes: int, is_adult_transition: bool = False) -> float:
        """
        Calculates the maximum allowed entropy threshold for an agent's promotion.
        The more time (episodes) configured, the stricter (closer to e_ideal) the threshold becomes.
        
        Args:
            configured_episodes: The time limit set by the user in the menu.
            is_adult_transition: If True, applies an extremely rigorous decay curve (Teen -> Adult).
            
        Returns:
            The calculated entropy threshold (float).
        """
        if configured_episodes <= 0:
            return self.e_max
            
        # Decay constant k.
        k = 0.05
        
        if is_adult_transition:
            # Rigorous transition to Adult: we multiply the decay constant 
            # to force the threshold down aggressively, demanding near-absolute certainty.
            k = 0.15 
            
        # Exponential decay formula: E(t) = E_ideal + (E_max - E_ideal) * e^(-k * t)
        threshold = self.e_ideal + (self.e_max - self.e_ideal) * math.exp(-k * configured_episodes)
        
        # Clamp between ideal and max for absolute safety
        return max(self.e_ideal, min(self.e_max, threshold))
