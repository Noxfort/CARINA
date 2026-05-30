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

# File: src/engine/phase_transition_manager.py
# Author: Gabriel Moraes
# Date: April 26, 2026

import logging
from typing import Dict, Any

class PhaseTransitionManager:
    """
    Componente especializado no gerenciamento de transições físicas de fase
    (Yellow, All-red) baseadas no tempo de simulação decorrido.
    """
    
    def __init__(self, state_extractor, action_supervisor, yellow_time: float = 4.0, all_red_time: float = 2.0):
        self.state_extractor = state_extractor
        self.action_supervisor = action_supervisor
        self.yellow_time = yellow_time
        self.all_red_time = all_red_time
    
    def auto_advance_transitions(self, sim_time: float, current_phases: Dict[str, Any]):
        """
        Avança as transições físicas automaticamente baseadas no tempo de simulação decorrido.
        
        Args:
            sim_time (float): Tempo de simulação atual
            current_phases (Dict): Dicionário com as fases atuais de cada TL
        """
        for tl_id in list(current_phases.keys()):
            current_phase_idx = current_phases.get(tl_id, 0)
            green_phases = self.state_extractor.tl_green_phases.get(tl_id, [])
            
            # If current phase is NOT a green phase, it's a physical transition (Yellow, Red, etc)
            if green_phases and current_phase_idx not in green_phases:
                duration = sim_time - self.action_supervisor._last_phase_change_time.get(tl_id, 0)
                phase_codes = self.state_extractor.tl_phase_codes.get(tl_id, {})
                state_string = phase_codes.get(current_phase_idx, "").upper()
                total_phases = len(phase_codes)
                
                if total_phases == 0:
                    continue
                    
                advanced = False
                if 'Y' in state_string and duration >= self.yellow_time:
                    current_phases[tl_id] = (current_phase_idx + 1) % total_phases
                    advanced = True
                    logging.debug(f"[PhaseTransitionManager] TL {tl_id} YELLOW->NEXT phase after {duration:.2f}s (threshold: {self.yellow_time}s)")
                elif 'R' in state_string and duration >= self.all_red_time:
                    current_phases[tl_id] = (current_phase_idx + 1) % total_phases
                    advanced = True
                    logging.debug(f"[PhaseTransitionManager] TL {tl_id} ALL-RED->NEXT phase after {duration:.2f}s (threshold: {self.all_red_time}s)")
                elif 'Y' in state_string:
                    logging.debug(f"[PhaseTransitionManager] TL {tl_id} in YELLOW phase for {duration:.2f}s (threshold: {self.yellow_time}s)")
                elif 'R' in state_string:
                    logging.debug(f"[PhaseTransitionManager] TL {tl_id} in ALL-RED phase for {duration:.2f}s (threshold: {self.all_red_time}s)")
                    
                if advanced:
                    # Keep the exact start time of the newly entered phase to maintain sync
                    self.action_supervisor._last_phase_change_time[tl_id] = sim_time
                    logging.info(f"[PhaseTransitionManager] TL {tl_id} advanced to phase {current_phases[tl_id]}")
    
    def update_estimated_phase(self, tl_id: str, current_phase_idx: int, sim_time: float, current_phases: Dict[str, Any]):
        """
        Inicia a transição estritamente para a próxima fase lógica (tipicamente Amarela).
        
        Args:
            tl_id (str): ID do semáforo
            current_phase_idx (int): Índice da fase atual
            sim_time (float): Tempo de simulação atual
            current_phases (Dict): Dicionário com as fases atuais de cada TL
        """
        phase_codes = self.state_extractor.tl_phase_codes.get(tl_id, {})
        total_phases = len(phase_codes)
        
        if total_phases == 0:
            logging.warning(f"[PhaseTransitionManager] No phase codes found for TL {tl_id}")
            return
            
        # Instead of skipping directly to the next Green, just move to the next immediate phase (+1)
        next_phase_idx = (current_phase_idx + 1) % total_phases
        current_phases[tl_id] = next_phase_idx
        
        # Mark precisely when this intermediate phase was initiated by the hardware Actuator
        self.action_supervisor._last_phase_change_time[tl_id] = sim_time
        
        # Log the phase transition for debugging
        current_state = phase_codes.get(current_phase_idx, "UNKNOWN").upper()
        next_state = phase_codes.get(next_phase_idx, "UNKNOWN").upper()
