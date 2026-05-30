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

# File: src/core/action_authorizer.py (HFT Compatibility Patch)
# Author: Gabriel Moraes
# Date: December 15, 2025

import sys
import os
from typing import TYPE_CHECKING, Any, Optional

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.enums import Maturity
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class ActionAuthorizer:
    """O "Porteiro" da Escola de Pilotagem, especialista em autorizar ações."""

    def __init__(self, settings: Any, locale_manager: 'LocaleManagerBackend', traffic_profiles: Optional[dict] = None):
        """
        Initializes the authorizer.
        Now accepts 'settings' for compatibility with Trainer HFT.
        """
        self.locale_manager = locale_manager
        
        if traffic_profiles:
            self.traffic_profiles = traffic_profiles
        else:
            # HFT Fallback: If no profile is provided, assumes 'low' traffic
            # for the entire period, allowing TEEN agents to act.
            # Structure: {day_index: {hour_str: level_trafego}}
            self.traffic_profiles = {
                day: {str(hour): "low" for hour in range(24)}
                for day in range(7)
            }

    def is_action_authorized(self, agent_id: str, maturity: Maturity, sim_time: float) -> tuple[bool, str]:
        """
        Checks if an agent is authorized to act based on its maturity and time.
        """
        lm = self.locale_manager
        
        if maturity == Maturity.CHILD: 
            return False, lm.get_string("action_authorizer.reason.child", fallback="Nível Criança: Apenas observação.")
        
        if maturity == Maturity.ADULT: 
            return True, lm.get_string("action_authorizer.reason.adult", fallback="Nível Adulto: Autorizado.")
        
        if maturity == Maturity.TEEN:
            # Calculates day and time based on simulation time (assumes T=0 is Mon 00:00)
            day_index = int(sim_time // 86400) % 7
            hour_of_day = str(int((sim_time % 86400) // 3600))
            
            profile_for_day = self.traffic_profiles.get(day_index, {})
            traffic_level = profile_for_day.get(hour_of_day, "low")
            
            if traffic_level == "peak": 
                return False, lm.get_string("action_authorizer.reason.teen_peak", fallback="Nível Adolescente: Proibido em horário de pico.")
            
            return True, lm.get_string("action_authorizer.reason.teen_offpeak", fallback="Nível Adolescente: Autorizado fora de pico.")
            
        return False, lm.get_string("action_authorizer.reason.unknown", fallback="Maturidade desconhecida.")