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

# File: src/engine/mfd/tracker.py
# Author: Gabriel Moraes
# Date: June 15, 2026

"""
MFD Tracker — State & History Management.

Responsible for maintaining the temporal state of the MFD engine:
peak detection, exponential moving averages (EMA), history buffer,
and warmup period management.
"""

import logging
from collections import deque
from typing import List, Dict, Any, Optional

from mfd.snapshot import MFDSnapshot

logger = logging.getLogger(__name__)


class MFDTracker:
    """
    Manages the temporal state of MFD observations.
    
    Tracks:
        - Historical snapshots (bounded deque)
        - Peak production and critical accumulation
        - Exponential Moving Averages for smoothed UI display
        - Warmup period to avoid premature metric reporting
    """

    # Maximum history size (prevents unbounded memory growth)
    MAX_HISTORY = 3600  # ~1 hour at 1 step/second

    # Minimum steps before the peak estimate is considered reliable
    WARMUP_STEPS = 30

    def __init__(self, ema_alpha: float = 0.05):
        """
        Args:
            ema_alpha: Smoothing factor for the Exponential Moving Average (0.0 to 1.0).
                       Lower values = smoother (more lag), higher = more responsive.
        """
        self._ema_alpha = ema_alpha

        # Peak state
        self._peak_production: float = 0.0
        self._peak_accumulation: float = 0.0  # Accumulation at peak production (critical density)

        # Step counter
        self._step_count: int = 0

        # History buffer
        self._history: deque[MFDSnapshot] = deque(maxlen=self.MAX_HISTORY)

        # EMA state
        self._ema_production: float = 0.0
        self._ema_accumulation: float = 0.0

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def is_warmed_up(self) -> bool:
        return self._step_count > self.WARMUP_STEPS

    @property
    def peak_production(self) -> float:
        return self._peak_production

    @property
    def peak_accumulation(self) -> float:
        return self._peak_accumulation

    def record(self, snapshot: MFDSnapshot) -> None:
        """
        Records a new MFD snapshot and updates all internal state.

        Args:
            snapshot: The computed MFDSnapshot for the current step.
        """
        self._step_count += 1

        # Update EMA
        self._ema_production = (
            self._ema_alpha * snapshot.production +
            (1 - self._ema_alpha) * self._ema_production
        )
        self._ema_accumulation = (
            self._ema_alpha * snapshot.accumulation +
            (1 - self._ema_alpha) * self._ema_accumulation
        )

        # Update peak production (the top of the MFD bell curve)
        if snapshot.production > self._peak_production:
            self._peak_production = snapshot.production
            self._peak_accumulation = snapshot.accumulation
            if self.is_warmed_up:
                logger.info(
                    f"[MFD] New peak production detected: {snapshot.production:.2f} veh·m/s "
                    f"at accumulation {snapshot.accumulation:.2f} veh"
                )

        # Store in history
        self._history.append(snapshot)

    def get_latest(self) -> Optional[MFDSnapshot]:
        """Returns the most recent MFD snapshot, or None if no data."""
        return self._history[-1] if self._history else None

    def get_smoothed_metrics(self) -> Dict[str, Any]:
        """Returns the EMA-smoothed production and accumulation for the UI."""
        return {
            'production_ema': round(self._ema_production, 4),
            'accumulation_ema': round(self._ema_accumulation, 4),
            'peak_production': round(self._peak_production, 4),
            'peak_accumulation': round(self._peak_accumulation, 4),
            'steps_computed': self._step_count,
            'is_warmed_up': self.is_warmed_up
        }

    def get_curve_data(self, last_n: int = 0) -> List[Dict[str, float]]:
        """
        Returns MFD curve data points (accumulation vs production) for plotting.

        Args:
            last_n: Number of recent points to return. 0 = all available.

        Returns:
            List of dicts with 'accumulation', 'production', and 'timestamp' keys.
        """
        source = list(self._history)
        if last_n > 0:
            source = source[-last_n:]

        return [
            {
                'accumulation': s.accumulation,
                'production': s.production,
                'timestamp': s.timestamp
            }
            for s in source
        ]

    @property
    def history_size(self) -> int:
        return len(self._history)

    def reset(self) -> None:
        """Resets all temporal state. Does NOT affect topology."""
        self._peak_production = 0.0
        self._peak_accumulation = 0.0
        self._step_count = 0
        self._ema_production = 0.0
        self._ema_accumulation = 0.0
        self._history.clear()
        logger.info("[MFD] Tracker state reset.")
