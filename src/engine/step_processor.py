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

# File: src/engine/step_processor.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict

from core.enums import Maturity
from core.system_reporter import SystemReporter
from engine.step_timer import StepTimer
from engine.agent_evaluator import AgentEvaluator
from utils.safety_rules import SafetyRules

class StepProcessor:
    """
    Responsible for managing the lifecycle and internal state of a
    Simulation/Session (Steps). Acts EXCLUSIVELY as an orchestrator.
    """
    def __init__(self, settings: Any, locale_manager: Any, agent_manager: Any, input_preprocessor: Any, 
                 state_extractor: Any, action_supervisor: Any, action_authorizer: Any, 
                 maturity_manager: Any, reward_computer: Any, cycle_manager: Any, pipe_conn: Any) -> None:
        self.settings = settings
        self.lm = locale_manager
        
        self.agent_manager = agent_manager
        self.input_preprocessor = input_preprocessor
        self.state_extractor = state_extractor
        self.action_supervisor = action_supervisor
        self.action_authorizer = action_authorizer
        self.maturity_manager = maturity_manager
        self.reward_computer = reward_computer
        self.cycle_manager = cycle_manager
        
        self.pipe_conn = pipe_conn
        
        # SRP Instantiations
        self.step_timer = StepTimer()
        self.agent_evaluator = AgentEvaluator(
            state_extractor=self.state_extractor,
            input_preprocessor=self.input_preprocessor,
            reward_computer=self.reward_computer,
            action_authorizer=self.action_authorizer,
            action_supervisor=self.action_supervisor,
            maturity_manager=self.maturity_manager,
            locale_manager=self.lm
        )
        
        # Session State Variables
        self.step_counter = 0
        self.start_time_offset: Optional[float] = None
        self.current_phases: Dict[str, Any] = {}
        self.accumulated_metrics = defaultdict(lambda: {'rewards': [], 'entropies': []})
        self.log_step_progress = True
        self.guardians = {}
        
        # --- Physical Time Transition Rules ---
        self.yellow_time = SafetyRules.get_yellow()
        self.all_red_time = SafetyRules.get_all_red()
            
        # --- Episode tracking ---
        self._episode_counter = 0
        self._episode_total_reward = 0.0
        self._episode_steps_in_current = 0

    def reset_state(self) -> None:
        """Resets the counters for a new session (or new map)."""
        self.step_counter = 0
        self.start_time_offset = None
        self.current_phases.clear()
        self.accumulated_metrics.clear()
        self.action_supervisor.reset()
        self.input_preprocessor.reset()
        self._episode_counter = 0
        self._episode_total_reward = 0.0
        self._episode_steps_in_current = 0

    def set_current_phases(self, phases: Dict[str, Any]) -> None:
        self.current_phases = phases

    def set_guardians(self, guardians: Dict[str, Any]) -> None:
        self.guardians = guardians

    def process_hft_step(self, traffic_data: Dict[str, Any], agents: Dict[str, Any]) -> None:
        """
        Orchestrates a single simulation step based on Real-Time Traffic Data.

        Produces detailed diagnostic logs matching the legacy system:
        - Step header with number, elapsed time, and operation mode
        - Per-agent decision log with maturity, action, and authorization
        - Granular timing breakdown (Extraction, PPO, Reward, Auth, Total)
        - Episode boundary bulletins with maturity promotions
        """
        self.step_timer.start_step()
        
        # Time Management
        raw_timestamp = traffic_data.get('timestamp', 0)
        if self.start_time_offset is None:
            self.start_time_offset = raw_timestamp
        sim_time = raw_timestamp - self.start_time_offset
        self.step_counter += 1
        self._episode_steps_in_current += 1
        
        # Log current time settings for debugging
        logging.debug(f"[StepProcessor] Current time settings - Yellow: {self.yellow_time}s, All-Red: {self.all_red_time}s")
        
        # --- Physical Transitions Synchronization ---
        # Evaluate automatic hardware transitions (Yellow/All-red) based on sim_time
        self._auto_advance_transitions(sim_time)
        
        # --- STEP HEADER ---
        if self.log_step_progress:
            SystemReporter.report_step_start(self.lm, self.step_counter, sim_time, "AUTOMATIC")

        actions_to_apply = {}
        edges_data = traffic_data.get('edges', {})
        tls_lanes_state = {}
        maturity_info = {}

        guardian_vetoed_any = False
        step_reward_sum = 0.0

        # --- Main Agent Loop ---
        for tl_id, agent in agents.items():
            current_phase_idx = self.current_phases.get(tl_id, 0)
            guardian = self.guardians.get(tl_id)

            # Execution via isolated evaluator component
            action, maturity_name, vetoed, reward, entropy, lanes_state = self.agent_evaluator.evaluate_agent(
                tl_id, agent, current_phase_idx, traffic_data, edges_data, sim_time, guardian, self.step_timer
            )
            
            tls_lanes_state[tl_id] = lanes_state
            maturity_info[tl_id] = maturity_name
            step_reward_sum += reward
            self.accumulated_metrics[tl_id]['rewards'].append(reward)
            self.accumulated_metrics[tl_id]['entropies'].append(entropy)
            
            if vetoed:
                guardian_vetoed_any = True
                
            if action is not None:
                actions_to_apply[tl_id] = action

        # --- Execute Actions ---
        if actions_to_apply:
            self.action_supervisor.apply_actions(actions_to_apply, sim_time, self.current_phases)
            
        # --- Update Software Phases after Hardware Actions ---
        for tl_id, action in actions_to_apply.items():
            if action == 0:
                current_phase_idx = self.current_phases.get(tl_id, 0)
                self._update_estimated_phase(tl_id, current_phase_idx, sim_time)

        self._episode_total_reward += step_reward_sum
            
        # --- STEP TIMER (Finish and Log) ---
        self.step_timer.log_and_finish_step(guardian_vetoed_any, self.log_step_progress)

        # --- Lifecycle Check (Episode Boundary) ---
        episode_steps = self.settings.getint('AI_TRAINING', 'episode_max_steps', fallback=100)
        if self.step_counter % episode_steps == 0:
            self._episode_counter += 1
            
            # CycleManager handles: metrics aggregation, promotion check, checkpoints, UI sync
            self.cycle_manager.evaluate_cycle(self.step_counter, agents, self.accumulated_metrics)
            
            # --- SCHOOL BULLETIN (Legacy Format) ---
            self._report_episode_bulletin(agents, episode_steps)
            
            # Reset episode-level counters
            self._episode_total_reward = 0.0
            self._episode_steps_in_current = 0

        # --- SEND HFT FEEDBACK TO CENTRAL CONTROLLER CACHE ---
        # Renamed from 'hft_rich_update' to 'ai_telemetry_sync' to avoid conflicting with the UI (SDS/SAS)
        rich_payload = {
            "edges": edges_data,
            "tls_phases": self.current_phases,
            "tls_lanes_state": tls_lanes_state,
            "maturity": maturity_info
        }
        
        # Sends to the Central Controller via Pipe
        if self.pipe_conn:
            try:
                self.pipe_conn.send(("ai_telemetry_sync", rich_payload))
            except Exception as e:
                logging.error(f"[TRAINER] Failed to send AI Telemetry update: {e}")

    def _report_episode_bulletin(self, agents: Dict[str, Any], episode_steps: int) -> None:
        """
        Logs the detailed 'School Bulletin' at the end of each episode.
        
        Legacy format:
        ────────────────────────────────────────────────────────────
        END OF EPISODE {N} | SCHOOL BULLETIN
          - Episode Performance: Total Reward = {R}
          - Class Status: {A} Adults | {T} Teens | {C} Children
          - Confidence Calibration Status: Ongoing
        ────────────────────────────────────────────────────────────
        """
        from collections import Counter
        
        maturity_counts = Counter()
        for tl_id in agents:
            phase = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
            maturity_counts[phase] += 1
        
        calibration_status = self.lm.get_string("reporter.calib_status_done") if self.maturity_manager.is_calibrated else self.lm.get_string("reporter.calib_status_ongoing")
        
        SystemReporter.report_school_bulletin(
            lm=self.lm,
            episode_count=self._episode_counter,
            total_reward=self._episode_total_reward,
            maturity_counts=maturity_counts,
            calibration_status=calibration_status
        )

    def _auto_advance_transitions(self, sim_time: float) -> None:
        """Advances physical phases automatically based on simulation elapsed time."""
        for tl_id in list(self.current_phases.keys()):
            current_phase_idx = self.current_phases.get(tl_id, 0)
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
                    self.current_phases[tl_id] = (current_phase_idx + 1) % total_phases
                    advanced = True
                    logging.debug(f"[StepProcessor] TL {tl_id} YELLOW->NEXT phase after {duration:.2f}s (threshold: {self.yellow_time}s)")
                elif 'R' in state_string and duration >= self.all_red_time:
                    self.current_phases[tl_id] = (current_phase_idx + 1) % total_phases
                    advanced = True
                    logging.debug(f"[StepProcessor] TL {tl_id} ALL-RED->NEXT phase after {duration:.2f}s (threshold: {self.all_red_time}s)")
                elif 'Y' in state_string:
                    logging.debug(f"[StepProcessor] TL {tl_id} in YELLOW phase for {duration:.2f}s (threshold: {self.yellow_time}s)")
                elif 'R' in state_string:
                    logging.debug(f"[StepProcessor] TL {tl_id} in ALL-RED phase for {duration:.2f}s (threshold: {self.all_red_time}s)")
                    
                if advanced:
                    # Keep the exact start time of the newly entered phase to maintain sync
                    self.action_supervisor._last_phase_change_time[tl_id] = sim_time
                    logging.info(f"[StepProcessor] TL {tl_id} advanced to phase {self.current_phases[tl_id]}")

    def _update_estimated_phase(self, tl_id: str, current_phase_idx: int, sim_time: float) -> None:
        """Initiates the transition strictly to the next logical phase (typically Yellow)."""
        phase_codes = self.state_extractor.tl_phase_codes.get(tl_id, {})
        total_phases = len(phase_codes)
        
        if total_phases == 0:
            logging.warning(f"[StepProcessor] No phase codes found for TL {tl_id}")
            return
            
        # Instead of skipping directly to the next Green, just move to the next immediate phase (+1)
        next_phase_idx = (current_phase_idx + 1) % total_phases
        self.current_phases[tl_id] = next_phase_idx
        
        # Mark precisely when this intermediate phase was initiated by the hardware Actuator
        self.action_supervisor._last_phase_change_time[tl_id] = sim_time
        
        # Log the phase transition for debugging
        current_state = phase_codes.get(current_phase_idx, "UNKNOWN").upper()
        next_state = phase_codes.get(next_phase_idx, "UNKNOWN").upper()
        logging.info(f"[StepProcessor] TL {tl_id} phase transition: {current_state} -> {next_state} at time {sim_time:.2f}")
