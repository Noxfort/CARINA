# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This file is part of CARINA.
# See LICENSE file for details.

# File: src/promotion/threshold_calculator.py
# Author: Gabriel Moraes
# Date: June 15, 2026

"""
Dynamic Threshold Calculator for Agent Promotion.

Implements the Asymptotic Adaptive Threshold formula to calculate
the required performance (MFD Efficiency) for an agent to be promoted.
The threshold grows asymptotically based on the time the agent has spent
in its current maturity phase.

Formula:
    threshold(t) = R_min + (R_max - R_min) * (1 - e^(-lambda * t / t_min))
"""

import math
from typing import Dict, Any

class PromotionPhaseConfig:
    """Configuration parameters for a specific maturity phase promotion."""
    def __init__(self, r_min: float, r_max: float, t_min: int, decay_lambda: float):
        self.r_min = r_min
        self.r_max = r_max
        self.t_min = t_min
        self.decay_lambda = decay_lambda

class ThresholdCalculator:
    """
    Calculates dynamic promotion thresholds using the Asymptotic Adaptive Threshold method.
    """
    
    # Default parameters if not provided by settings
    DEFAULT_CONFIGS = {
        'CHILD': PromotionPhaseConfig(r_min=0.30, r_max=0.60, t_min=10, decay_lambda=2.0),
        'TEEN': PromotionPhaseConfig(r_min=0.60, r_max=0.85, t_min=30, decay_lambda=1.5)
    }

    @staticmethod
    def calculate_threshold(phase_name: str, episodes_in_phase: int, configs: Dict[str, PromotionPhaseConfig] = None) -> float:
        """
        Calculates the required MFD Efficiency threshold for promotion.

        Args:
            phase_name: The current maturity phase of the agent (e.g., 'CHILD', 'TEEN').
            episodes_in_phase: Number of episodes the agent has been in this phase.
            configs: Optional custom configurations. Uses defaults if None.

        Returns:
            The calculated efficiency threshold (float between 0.0 and 1.0).
        """
        config_map = configs if configs else ThresholdCalculator.DEFAULT_CONFIGS
        
        # If the phase is not defined (e.g., ADULT), return max float so it never promotes
        if phase_name not in config_map:
            return float('inf')
            
        config = config_map[phase_name]
        
        # If the agent hasn't reached the minimum time, it's not eligible yet.
        # We return the threshold anyway for transparency, but the evaluator handles t_min.
        
        # Asymptotic Adaptive Threshold Formula
        # T(t) = R_min + (R_max - R_min) * (1 - e^(-lambda * t / t_min))
        
        exponent = -config.decay_lambda * (episodes_in_phase / max(1, config.t_min))
        growth_factor = 1.0 - math.exp(exponent)
        
        threshold = config.r_min + (config.r_max - config.r_min) * growth_factor
        
        return min(threshold, config.r_max)
