# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This file is part of CARINA.
# See LICENSE file for details.

# File: src/promotion/promotion_evaluator.py
# Author: Gabriel Moraes
# Date: June 15, 2026

"""
Promotion Evaluator.

Connects the MFD Network Efficiency with the Dynamic Threshold Calculator
to determine if an agent deserves to be promoted to the next maturity phase.
"""

import logging
from typing import Dict, Optional, Tuple
from core.enums import Maturity
from promotion.threshold_calculator import ThresholdCalculator, PromotionPhaseConfig

logger = logging.getLogger(__name__)

class PromotionEvaluator:
    """
    Evaluates whether agents meet the conditions for maturity promotion
    based on MFD efficiency and dynamic thresholds.
    """

    def __init__(self, settings_dict: Dict = None):
        """
        Args:
            settings_dict: Optional configuration overrides for phase parameters.
        """
        self.configs = ThresholdCalculator.DEFAULT_CONFIGS
        
        # Override with settings if provided
        if settings_dict:
            self._load_configs(settings_dict)

    def _load_configs(self, settings: Dict):
        # Allow overriding defaults from settings.ini
        pass # To be implemented if settings integration is required

    def evaluate_agent(self, agent_id: str, current_phase: Maturity, episodes_in_phase: int, recent_mfd_efficiency: float) -> Tuple[bool, str, float, float]:
        """
        Evaluates if a single agent should be promoted.

        Args:
            agent_id: The ID of the agent (traffic light).
            current_phase: The agent's current Maturity enum.
            episodes_in_phase: How long the agent has been in this phase.
            recent_mfd_efficiency: The EMA or recent average of the MFD efficiency (0.0 to 1.0).

        Returns:
            Tuple containing:
                - is_promoted (bool): True if the agent met the criteria.
                - reason (str): Human readable reason.
                - threshold_used (float): The dynamic threshold that was calculated.
                - required_episodes (float): Minimum episodes required.
        """
        phase_name = current_phase.name
        
        # ADULT phase or unknown phase cannot be promoted
        if phase_name not in self.configs:
            return False, "Agent is already at maximum maturity or unknown phase.", 1.0, float('inf')

        config = self.configs[phase_name]
        
        # Check minimum time
        if episodes_in_phase < config.t_min:
            return False, f"Not enough episodes in phase. Required: {config.t_min}, Current: {episodes_in_phase}", 0.0, config.t_min
            
        # Calculate dynamic threshold
        current_threshold = ThresholdCalculator.calculate_threshold(
            phase_name=phase_name,
            episodes_in_phase=episodes_in_phase,
            configs=self.configs
        )
        
        # Check performance against threshold
        if recent_mfd_efficiency >= current_threshold:
            return True, f"Efficiency {recent_mfd_efficiency:.2%} exceeded dynamic threshold {current_threshold:.2%}", current_threshold, config.t_min
            
        return False, f"Efficiency {recent_mfd_efficiency:.2%} is below dynamic threshold {current_threshold:.2%}", current_threshold, config.t_min
