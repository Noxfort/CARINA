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

# File: src/controller/health_monitor.py (ALREADY COMPLIANT)
# Author: Gabriel Moraes
# Date: October 1, 2025

import time
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class AIHealthMonitor:
    """Monitors the 'pulse' of the AI process to detect failures."""

    def __init__(self, heartbeat_timeout: float, locale_manager: 'LocaleManagerBackend'):
        """
        Inicializa o monitor de saúde.
        """
        self.timeout = heartbeat_timeout
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        self.last_message_time = None
        self.is_healthy = True
        
        logging.info(lm.get_string("health_monitor.init.monitor_created", timeout=self.timeout))
        self.record_activity()

    def record_activity(self):
        """
        Registra que a IA enviou uma mensagem, "resetando" o cronômetro do heartbeat.
        """
        self.last_message_time = time.time()
        if not self.is_healthy:
            logging.info(self.locale_manager.get_string("health_monitor.activity.communication_reestablished"))
            self.is_healthy = True

    def check_health(self) -> bool:
        """
        Checks if the AI has exceeded the response timeout.
        Returns the current health status.
        """
        lm = self.locale_manager
        if not self.is_healthy:
            return False

        elapsed_time = time.time() - self.last_message_time
        if elapsed_time > self.timeout:
            logging.critical(lm.get_string("health_monitor.health_check.failure", timeout=f"{self.timeout:.2f}"))
            logging.warning(lm.get_string("health_monitor.health_check.switching_to_watchdog"))
            self.is_healthy = False
        
        return self.is_healthy