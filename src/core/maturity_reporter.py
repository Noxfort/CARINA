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

# File: src/core/maturity_reporter.py (MODIFIED FOR STRUCTURAL TRANSLATION)
# Author: Gabriel Moraes
# Date: October 3, 2025

import logging
import sys
import os
from typing import TYPE_CHECKING

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.enums import Maturity
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class MaturityReporter:
    """O "Porta-voz" da Escola de Pilotagem, especialista em gerar relatórios de log."""

    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        self.locale_manager = locale_manager

    def report_promotion(self, agent_id: str, new_phase: Maturity, details: dict):
        """Formata e loga uma mensagem de promoção bem-sucedida."""
        lm = self.locale_manager
        
        is_graduation = new_phase == Maturity.ADULT
        icon = "🎓" if is_graduation else "✅"
        
        title_key = "maturity_reporter.promotion.title_graduated" if is_graduation else "maturity_reporter.promotion.title_promoted"
        title = lm.get_string(title_key)
        
        # --- CHANGE 1: Use a key that contains the entire header structure ---
        header = lm.get_string("maturity_reporter.promotion.header", icon=icon, title=title, agent_id=agent_id)
        
        phase_map = { Maturity.TEEN: "teen", Maturity.ADULT: "adult" }
        phase_name = lm.get_string(f"maturity_manager.phase_{phase_map.get(new_phase, 'child')}")
        
        log_message = f"\n{header}\n"
        log_message += f"   L- {lm.get_string('maturity_manager.new_phase_message', phase_name=phase_name)}.\n"
        log_message += f"   L- {lm.get_string('maturity_manager.criteria_met_header')}"
        
        for criterion, value in details.items():
            # Criteria formatting can be maintained in the code for its simplicity
            log_message += f"\n      - ✅ {criterion}: {value}"
        logging.info(log_message)

    def report_rejection(self, agent_id: str, current_phase: Maturity, target_phase: Maturity, details: dict):
        """Formats and logs a detailed "report card" for a failed promotion attempt."""
        lm = self.locale_manager
        
        title = lm.get_string('maturity_reporter.rejection.title')
        
        phase_map = { Maturity.CHILD: "child", Maturity.TEEN: "teen", Maturity.ADULT: "adult" }
        current_phase_name = lm.get_string(f"maturity_manager.phase_{phase_map.get(current_phase, 'child')}")
        target_phase_name = lm.get_string(f"maturity_manager.phase_{phase_map.get(target_phase, 'teen')}")

        # --- CHANGE 2: Use a key that contains the entire header structure ---
        header = lm.get_string(
            "maturity_reporter.rejection.header", 
            title=title, 
            agent_id=agent_id, 
            current_phase_name=current_phase_name
        )

        log_message = f"\n{header} "
        log_message += lm.get_string('maturity_manager.promotion_not_met_message', target_phase_name=target_phase_name)
        log_message += f"\n   L- {lm.get_string('maturity_manager.criteria_status_header')}"
        
        for criterion, data in details.items():
            icon = "✅" if data["ok"] else "❌"
            # Criteria formatting can be maintained in the code
            log_message += f"\n      - {icon} {criterion}: {data['msg']}"
        logging.info(log_message)