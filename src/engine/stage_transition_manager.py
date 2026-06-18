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

# File: src/engine/stage_transition_manager.py
# Author: Gabriel Moraes
# Date: April 26, 2026

import logging
from typing import Dict, Any
from utils.safety_rules import SafetyRules

class StageTransitionManager:
    """
    Componente especializado no gerenciamento de transições físicas de estágio
    (Yellow, All-red, Red) baseadas no tempo de simulação decorrido.
    """
    
    def __init__(self, state_extractor, action_supervisor):
        self.state_extractor = state_extractor
        self.action_supervisor = action_supervisor
        self.yellow_time = SafetyRules.get_yellow()
        self.all_red_time = SafetyRules.get_all_red()
    
    def auto_advance_transitions(self, sim_time: float, current_stages: Dict[str, Any]):
        """
        Avança as transições físicas automaticamente baseadas no tempo de simulação decorrido.
        
        Args:
            sim_time (float): Tempo de simulação atual
            current_stages (Dict): Dicionário com os estágios atuais de cada TL
        """
        for tl_id in list(current_stages.keys()):
            current_stage_idx = current_stages.get(tl_id, 0)
            green_stages = self.state_extractor.tl_green_stages.get(tl_id, [])
            
            # If current stage is NOT a green stage, it's a physical transition (Yellow, Red, etc)
            if green_stages and current_stage_idx not in green_stages:
                duration = sim_time - self.action_supervisor._last_stage_change_time.get(tl_id, 0)
                stage_codes = self.state_extractor.tl_stage_codes.get(tl_id, {})
                state_string = stage_codes.get(current_stage_idx, "").upper()
                total_stages = len(stage_codes)
                
                if total_stages == 0:
                    continue
                    
                advanced = False
                if 'Y' in state_string and duration >= self.yellow_time:
                    current_stages[tl_id] = (current_stage_idx + 1) % total_stages
                    advanced = True
                    logging.debug(f"[StageTransitionManager] TL {tl_id} YELLOW->NEXT stage after {duration:.2f}s (threshold: {self.yellow_time}s)")
                elif 'R' in state_string:
                    prev_stage_idx = (current_stage_idx - 1) % total_stages
                    prev_state_string = stage_codes.get(prev_stage_idx, "").upper()
                    is_clearance = 'Y' in prev_state_string
                    
                    threshold = self.all_red_time if is_clearance else SafetyRules.get_red()
                    
                    if duration >= threshold:
                        current_stages[tl_id] = (current_stage_idx + 1) % total_stages
                        advanced = True
                        logging.debug(f"[StageTransitionManager] TL {tl_id} RED->NEXT stage after {duration:.2f}s (threshold: {threshold}s)")
                elif 'Y' in state_string:
                    logging.debug(f"[StageTransitionManager] TL {tl_id} in YELLOW stage for {duration:.2f}s (threshold: {self.yellow_time}s)")
                elif 'R' in state_string:
                    logging.debug(f"[StageTransitionManager] TL {tl_id} in RED stage for {duration:.2f}s")
                    
                if advanced:
                    # Keep the exact start time of the newly entered stage to maintain sync
                    self.action_supervisor._last_stage_change_time[tl_id] = sim_time
                    logging.info(f"[StageTransitionManager] TL {tl_id} advanced to stage {current_stages[tl_id]}")
    
    def update_estimated_stage(self, tl_id: str, current_stage_idx: int, sim_time: float, current_stages: Dict[str, Any]):
        """
        Inicia a transição estritamente para o próximo estágio lógico (tipicamente Amarelo).
        
        Args:
            tl_id (str): ID do semáforo
            current_stage_idx (int): Índice do estágio atual
            sim_time (float): Tempo de simulação atual
            current_stages (Dict): Dicionário com os estágios atuais de cada TL
        """
        stage_codes = self.state_extractor.tl_stage_codes.get(tl_id, {})
        total_stages = len(stage_codes)
        
        if total_stages == 0:
            logging.warning(f"[StageTransitionManager] No stage codes found for TL {tl_id}")
            return
            
        # Instead of skipping directly to the next Green, just move to the next immediate stage (+1)
        next_stage_idx = (current_stage_idx + 1) % total_stages
        current_stages[tl_id] = next_stage_idx
        
        # Mark precisely when this intermediate stage was initiated by the hardware Actuator
        self.action_supervisor._last_stage_change_time[tl_id] = sim_time
        
        # Log the stage transition for debugging
        current_state = stage_codes.get(current_stage_idx, "UNKNOWN").upper()
        next_state = stage_codes.get(next_stage_idx, "UNKNOWN").upper()
        logging.info(f"[StageTransitionManager] TL {tl_id} stage transition: {current_state} -> {next_state} at time {sim_time:.2f}")

