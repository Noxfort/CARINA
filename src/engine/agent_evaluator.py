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

# File: src/engine/agent_evaluator.py
# Author: Gabriel Moraes
# Date: April 15, 2026

from typing import Dict, Any, Tuple, Optional
import logging
from core.enums import Maturity
from core.system_reporter import SystemReporter

class AgentEvaluator:
    """
    Encapsula o ciclo de inteligência e controle de um único agente local no tempo.
    Mede seus tempos de operação usando o StepTimer injetado.
    """

    def __init__(self, state_extractor: Any, input_preprocessor: Any, reward_computer: Any, 
                 action_authorizer: Any, action_supervisor: Any, maturity_manager: Any, locale_manager: Any) -> None:
        self.state_extractor = state_extractor
        self.input_preprocessor = input_preprocessor
        self.reward_computer = reward_computer
        self.action_authorizer = action_authorizer
        self.action_supervisor = action_supervisor
        self.maturity_manager = maturity_manager
        self.lm = locale_manager

    def evaluate_agent(self, tl_id: str, agent: Any, current_phase_idx: int, traffic_data: dict, 
                       edges_data: dict, sim_time: float, guardian: Optional[Any], step_timer: Any) -> Tuple[Optional[int], str, bool, float, float, Dict[str, str]]:
        """
        Executes the agent pipeline: Extraction -> Prep -> Inference -> Reward -> Guardian -> Auth.
        Returns:
            action_to_apply (int or None),
            maturity_name (str),
            guardian_vetoed (bool),
            reward (float),
            entropy_val (float),
            tls_lanes_state (Dict)
        """
        # --- UI DATA ---
        tls_lanes_state = self.state_extractor.get_phase_lane_states(tl_id, current_phase_idx)
        
        # Population Maturity Info
        agent_maturity = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
        maturity_name = agent_maturity.name
        
        # 1. Extract State
        step_timer.start_phase()
        
        # Log Pedestrian Action if present
        if 'tls_telemetry' in traffic_data:
            telemetry = traffic_data['tls_telemetry'].get(tl_id, {})
            if telemetry.get('active_ped_calls', 0) > 0:
                logging.info(f"🚶‍♂️ [AgentEvaluator] TL {tl_id}: Botão de pedestre pressionado detectado pelo hardware (UTMC/NTCIP).")
        
        state_vector = self.state_extractor.extract_state(traffic_data, tl_id, current_phase_idx)
        if len(state_vector) == 0: 
            return None, maturity_name, False, 0.0, 0.0, tls_lanes_state

        state_tensor, state_seq = self.input_preprocessor.prepare_tensor(tl_id, state_vector)
        step_timer.stop_phase('extraction')
        
        # 2. Agent Inference
        step_timer.start_phase()
        action_idx, action_log_prob, state_val, dist_entropy = agent.choose_action(state_tensor)
        step_timer.stop_phase('inference')
        
        action_int = action_idx.item()
        entropy_val = dist_entropy.item() if hasattr(dist_entropy, 'item') else 0.0
        
        # 3. Compute Reward
        step_timer.start_phase()
        reward = self.reward_computer.calculate(tl_id, edges_data)
        step_timer.stop_phase('reward')
        
        # 4. Store Experience
        agent.push_memory(state_seq, action_idx, action_log_prob, reward, False, state_val)

        # 5. Core Authorization
        step_timer.start_phase()
        is_auth, reason = self.action_authorizer.is_action_authorized(tl_id, agent_maturity, sim_time)
        step_timer.stop_phase('auth')

        # 6. Guardian Veto Control
        guardian_vetoed = False
        step_timer.start_phase()
        if is_auth and action_int == 0 and guardian:
            current_phase_duration = sim_time - self.action_supervisor._last_phase_change_time.get(tl_id, 0)
            state_string = self.state_extractor.tl_phase_codes.get(tl_id, {}).get(current_phase_idx, "G")
            
            # Improve context with more accurate information
            context = {
                'tl_id': tl_id,
                'current_phase_duration': current_phase_duration,
                'current_phase_state': state_string.upper(),
                'next_phase_has_flow': True
            }
            
            logging.debug(f"[AgentEvaluator] TL {tl_id} requesting phase change. Duration: {current_phase_duration:.2f}s, State: {state_string}")
            guard_action, guard_reason = guardian.select_action(state_vector, context)
            logging.debug(f"[AgentEvaluator] Guardian decision for TL {tl_id}: action={guard_action}, reason='{guard_reason}'")
            
            if guard_action == guardian.ACTION_KEEP_PHASE:
                is_auth = False
                reason = f"VETADA PELO GUARDIÃO ({guard_reason})"
                guardian_vetoed = True
                logging.info(f"[AgentEvaluator] TL {tl_id} phase change VETOED by Guardian: {guard_reason}")
            else:
                logging.info(f"[AgentEvaluator] TL {tl_id} phase change ALLOWED by Guardian: {guard_reason}")
        step_timer.stop_phase('guardian')

        # 7. Reporting
        action_str = self.lm.get_string("actions.change_phase") if action_int == 0 else self.lm.get_string("actions.keep_phase")
        SystemReporter.report_agent_decision(
            self.lm, tl_id, maturity_name, action_str, is_auth, reason, "NORMAL"
        )
        
        action_to_apply = action_int if is_auth else None
        
        return action_to_apply, maturity_name, guardian_vetoed, reward, entropy_val, tls_lanes_state
