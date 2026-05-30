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

# File: src/core/threshold_calibrator.py (MODIFIED FOR TRANSLATION)
# Author: Gabriel Moraes
# Date: October 2, 2025

"""
Defines the ThresholdCalibrator class.

This specialist component is the system's "auto-tuner". Its mission is to autonomously
and data-drivenly determine what constitutes a "confident" AI, by analyzing the
stability of the agent population's entropy over time.
"""

import logging
import numpy as np
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class ThresholdCalibrator:
    """
    Monitors agents' entropy to auto-calibrate the confidence thresholds
    required for the maturity phases.
    """

    def __init__(self, settings: dict, locale_manager: 'LocaleManagerBackend'):
        """
        Inicializa o Calibrador.

        Args:
            settings (dict): A seção [CALIBRATION] do arquivo de configuração.
            locale_manager: A instância do tradutor do backend.
        """
        self.locale_manager = locale_manager
        lm = self.locale_manager

        self.window_size = settings.getint('calibration_window_size', fallback=20)
        self.stability_threshold = settings.getfloat('stability_std_dev_threshold', fallback=0.01)
        self.teen_margin = settings.getfloat('teen_confidence_margin', fallback=1.25)
        self.adult_margin = settings.getfloat('adult_confidence_margin', fallback=1.10)
        
        self.entropies = deque(maxlen=self.window_size)
        
        self._is_calibrated = False
        self.teen_threshold = None
        self.adult_threshold = None
        
        logging.info(lm.get_string("threshold_calibrator.init.created"))
        logging.info(lm.get_string("threshold_calibrator.init.window_info", window=self.window_size))

    @property
    def is_calibrated(self) -> bool:
        """Returns True if the calibration is complete."""
        return self._is_calibrated

    def get_thresholds(self) -> tuple:
        """
        Retorna os limites de entropia calculados.
        """
        return self.teen_threshold, self.adult_threshold

    def step(self, mean_entropy: float):
        """
        Processes a new episode's entropy and checks if stability has been achieved.
        """
        if self._is_calibrated:
            return

        lm = self.locale_manager
        self.entropies.append(mean_entropy)
        
        if len(self.entropies) < self.window_size:
            logging.debug(lm.get_string(
                "threshold_calibrator.step.collecting_data",
                current=len(self.entropies),
                total=self.window_size
            ))
            return

        current_std_dev = np.std(list(self.entropies))
        logging.debug(lm.get_string(
            "threshold_calibrator.step.std_dev_check",
            std_dev=f"{current_std_dev:.4f}",
            threshold=f"{self.stability_threshold:.4f}"
        ))

        if current_std_dev < self.stability_threshold:
            self._calibrate()

    def _calibrate(self):
        """
        Calcula e trava os limites de entropia com base no platô detectado.
        """
        lm = self.locale_manager
        logging.info(lm.get_string("threshold_calibrator.calibrate.plateau_detected"))
        
        stable_entropy_value = np.mean(list(self.entropies))
        logging.info(lm.get_string("threshold_calibrator.calibrate.stable_value", value=f"{stable_entropy_value:.4f}"))

        self.teen_threshold = stable_entropy_value * self.teen_margin
        self.adult_threshold = stable_entropy_value * self.adult_margin
        
        self._is_calibrated = True
        
        logging.info(lm.get_string("threshold_calibrator.calibrate.complete"))
        logging.info(lm.get_string("threshold_calibrator.calibrate.teen_threshold", threshold=f"{self.teen_threshold:.4f}"))
        logging.info(lm.get_string("threshold_calibrator.calibrate.adult_threshold", threshold=f"{self.adult_threshold:.4f}"))