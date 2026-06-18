# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This file is part of CARINA.
# See LICENSE file for details.

# File: src/promotion/__init__.py

"""
Promotion Package.

Handles the logic for agent maturity advancement based on MFD network efficiency
and dynamic asymptotic thresholds.
"""

from promotion.threshold_calculator import ThresholdCalculator, PromotionPhaseConfig
from promotion.promotion_evaluator import PromotionEvaluator

__all__ = ['ThresholdCalculator', 'PromotionPhaseConfig', 'PromotionEvaluator']
