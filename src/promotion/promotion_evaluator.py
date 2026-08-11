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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/promotion/promotion_evaluator.py
# Author: Gabriel Moraes
# Date: June 15, 2026

"""
Promotion Evaluator.

Connects the MFD Network Efficiency with the Dynamic Threshold Calculator
to determine if an agent deserves to be promoted to the next maturity phase.
"""

import logging
from typing import Dict, Optional, Tuple, Any
from core.enums import Maturity
from promotion.threshold_calculator import ThresholdCalculator, PromotionPhaseConfig

logger = logging.getLogger(__name__)

class PromotionEvaluator:
    """
    Evaluates whether agents meet the conditions for maturity promotion
    based on MFD efficiency and dynamic thresholds.
    """

    def __init__(self, settings: Any = None, locale_manager: Any = None):
        """
        Args:
            settings: Optional configuration overrides for phase parameters.
            locale_manager: Optional LocaleManagerBackend instance.
        """
        self.locale_manager = locale_manager
        # Create unique instances of configs for this evaluator instance
        self.configs = {
            'CHILD': PromotionPhaseConfig(r_min=0.30, r_max=0.60, t_min=10, decay_lambda=2.0),
            'TEEN': PromotionPhaseConfig(r_min=0.60, r_max=0.85, t_min=30, decay_lambda=1.5)
        }
        
        # Override with settings if provided
        if settings:
            self._load_configs(settings)

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _load_configs(self, settings: Any):
        # Allow overriding defaults from settings.ini
        def get_int_setting(section, key, fallback):
            if hasattr(settings, 'getint'):
                try:
                    return settings.getint(section, key, fallback=fallback)
                except Exception:
                    return fallback
            elif hasattr(settings, 'get'):
                try:
                    val = settings.get(key)
                    return int(val) if val is not None else fallback
                except Exception:
                    return fallback
            return fallback

        child_t_min = get_int_setting('MATURITY', 'child_phase_episodes', 10)
        teen_t_min = get_int_setting('MATURITY', 'teen_phase_min_episodes', 30)
        
        self.configs['CHILD'].t_min = child_t_min
        self.configs['TEEN'].t_min = teen_t_min
        logger.info(self._get_string("promotion_evaluator.loaded_thresholds", default="[PromotionEvaluator] Loaded thresholds from settings: CHILD t_min={child_t_min}, TEEN t_min={teen_t_min}", child_t_min=child_t_min, teen_t_min=teen_t_min))

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
            return False, self._get_string("promotion_evaluator.already_max", default="Agent is already at maximum maturity or unknown phase."), 1.0, float('inf')

        config = self.configs[phase_name]
        
        # Check minimum time
        if episodes_in_phase < config.t_min:
            return False, self._get_string("promotion_evaluator.not_enough_episodes", default="Not enough episodes in phase. Required: {required}, Current: {current}", required=config.t_min, current=episodes_in_phase), 0.0, config.t_min
            
        # Calculate dynamic threshold
        current_threshold = ThresholdCalculator.calculate_threshold(
            phase_name=phase_name,
            episodes_in_phase=episodes_in_phase,
            configs=self.configs
        )
        
        # Check performance against threshold
        if recent_mfd_efficiency >= current_threshold:
            return True, self._get_string("promotion_evaluator.promoted_reason", default="Efficiency {eff:.2%} exceeded dynamic threshold {thresh:.2%}", eff=recent_mfd_efficiency, thresh=current_threshold), current_threshold, config.t_min
            
        return False, self._get_string("promotion_evaluator.rejected_reason", default="Efficiency {eff:.2%} is below dynamic threshold {thresh:.2%}", eff=recent_mfd_efficiency, thresh=current_threshold), current_threshold, config.t_min
