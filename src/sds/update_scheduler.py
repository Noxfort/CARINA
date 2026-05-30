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

# File: src/sds/update_scheduler.py
# Author: Gabriel Moraes
# Date: April 25, 2026

import logging
from typing import Dict, Any, Optional


class UpdateScheduler:
    """
    Manages the scheduling of periodic updates for heatmap visualization.
    
    This class determines when enough time has passed to trigger a dashboard update
    based on configurable intervals similar to Waze and Google Maps update frequency.
    """

    def __init__(self, update_interval: float = 5.0):
        """
        Initializes the UpdateScheduler.
        
        Args:
            update_interval (float): Seconds between visual updates (similar to Waze/Maps: 5-30 seconds).
        """
        self.update_interval = update_interval
        self.last_update_time = 0.0
        self.first_sample_time = None
        
        logging.info(f"[UpdateScheduler] Initialized with {update_interval}s update interval")

    def should_update(self, current_time: float) -> bool:
        """
        Checks if enough time has passed to trigger a dashboard update.
        
        Args:
            current_time (float): The current timestamp
            
        Returns:
            bool: True if update is due
        """
        # If no samples have been collected yet, no update is due
        if self.first_sample_time is None:
            return False
            
        # If last_update_time is 0 (initial value), check against first_sample_time
        if self.last_update_time == 0.0:
            return (current_time - self.first_sample_time) >= self.update_interval
            
        # Otherwise, check against last_update_time
        return (current_time - self.last_update_time) >= self.update_interval

    def update_last_update_time(self, current_time: float) -> None:
        """
        Updates the last update time to the current time.
        
        Args:
            current_time (float): The current timestamp
        """
        self.last_update_time = current_time
        # Reset first_sample_time to ensure we start counting from the last update
        self.first_sample_time = None

    def set_first_sample_time(self, timestamp: float) -> None:
        """
        Sets the first sample time if not already set.
        
        Args:
            timestamp (float): The timestamp of the first sample
        """
        if self.first_sample_time is None:
            self.first_sample_time = timestamp

    def reset(self) -> None:
        """
        Resets the scheduler state.
        """
        self.last_update_time = 0.0
        self.first_sample_time = None