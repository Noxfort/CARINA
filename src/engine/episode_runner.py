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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/engine/episode_runner.py
# Author: Gabriel Moraes
# Date: 2026-06-09

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

# File: src/engine/episode_runner.py (Fixed: Re-added Authorization logic, Decision Log and Detailed Timers)
# Author: Gabriel Moraes
# Date: November 1, 2025

import logging
from collections import deque, defaultdict
import numpy as np
import configparser
from multiprocessing import Queue
from queue import Empty, Full
import time
from typing import TYPE_CHECKING, Dict, Any, Union

# Add 'src' directory to path (kept)
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


# Imports that should not cause a cycle
from core.system_reporter import SystemReporter
from core.childhood_analyzer import ChildhoodAnalyzer
from core.maturity_manager import MaturityManager
from core.enums import Maturity
from engine.step_timer import StepTimer
from engine.guardian_communicator import GuardianCommunicator
from engine.action_filter import ActionFilter
from engine.metrics_tracker import MetricsTracker
from engine.state_history_manager import StateHistoryManager

from core.decision_coordinator import DecisionCoordinator

if TYPE_CHECKING:
    from core.action_authorizer import ActionAuthorizer
    from utils.locale_manager_backend import LocaleManagerBackend
    from engine.environment import SumoEnvironment
    from core.population_manager import PopulationManager
    from core.learning_coordinator import LearningCoordinator
    from core.strategic_coordinator import StrategicCoordinator


class EpisodeRunner:
    """Orchestrates the execution of a single episode, focused on the RL cycle."""

    def __init__(self, settings: configparser.ConfigParser, env: 'SumoEnvironment',
                 population_manager: 'PopulationManager', maturity_manager: MaturityManager,
                 learning_coordinator: 'LearningCoordinator', strategic_coordinator: 'StrategicCoordinator',
                 childhood_analyzer: ChildhoodAnalyzer,
                 action_authorizer: 'ActionAuthorizer',
                 n_observations: int, # Received from Trainer
                 guardian_state_queue: Union[Queue, None] = None,
                 guardian_signal_queue: Union[Queue, None] = None):

        self.settings = settings
        self.env = env
        self.learning_coordinator = learning_coordinator
        self.childhood_analyzer = childhood_analyzer
        self.population_manager = population_manager
        self.maturity_manager = maturity_manager
        self.strategic_coordinator = strategic_coordinator 
        self.action_authorizer = action_authorizer 
        self.n_observations = n_observations

        self.locale_manager = maturity_manager.locale_manager

        self.state_history: Dict[str, deque] = {}
        
        self.override_states: Dict[str, str] = {}
        self.current_operation_mode = "AUTOMATIC"

        self.guardian_comm = GuardianCommunicator(
            guardian_state_queue=guardian_state_queue,
            guardian_signal_queue=guardian_signal_queue
        )
        
        self.action_filter = ActionFilter(
            action_authorizer=self.action_authorizer,
            maturity_manager=self.maturity_manager,
            locale_manager=self.locale_manager
        )
        
        seq_len = self.settings.getint('AI_TRAINING', 'sequence_length', fallback=4)
        self.state_history_manager = StateHistoryManager(seq_len, self.n_observations)

        # old sumolib or direct Lane object
        self.decision_coordinator = DecisionCoordinator(
            agents=population_manager.agents,
            neighborhoods=strategic_coordinator.neighborhoods if hasattr(strategic_coordinator, 'neighborhoods') and strategic_coordinator.neighborhoods else {},
            environment=env,
            strategic_coordinator=strategic_coordinator, 
            n_observations=self.n_observations,        
            message_size=2 
        )


        self.episode_max_steps = self.settings.getint('AI_TRAINING', 'episode_max_steps', fallback=5000)
        
        if self.settings.has_option('AI_TRAINING', 'update_timestep'):
             self.update_timestep = self.settings.getint('AI_TRAINING', 'update_timestep', fallback=2048)
        else:
             self.update_timestep = 2048
             logging.warning("[EpisodeRunner] Chave 'update_timestep' não encontrada em [AI_TRAINING]. Usando fallback 2048.")

        log_settings = self.settings['LOGGING'] if self.settings.has_section('LOGGING') else {}
        self.log_step_progress = log_settings.getboolean('log_step_progress', fallback=False)
        self.log_progress_frequency = log_settings.getint('log_progress_frequency', fallback=500)

        logging.info(self.locale_manager.get_string("episode_runner.init.created"))


    def run(self, episode_count: int) -> Dict[str, Dict[str, Any]]:
        lm = self.locale_manager
        self.env.reset()
        current_states_dict = self.env.get_global_state()
        if not current_states_dict:
             logging.error("[EpisodeRunner] Falha ao obter estado global inicial. Encerrando episódio.")
             return {}

        self.state_history_manager.initialize_history(current_states_dict, list(self.population_manager.agents.keys()))

        self.current_operation_mode = current_states_dict.get("operation_mode", "AUTOMATIC")

        metrics_tracker = MetricsTracker()
        done = False
        step_count = 0
        last_decision_data = {}
        self.latest_veto_map = {} # Store the latest veto map from background thinking

        logging.info(lm.get_string("episode_runner.run.start_unified").format(episode=episode_count))
        
        timer = StepTimer(self.log_step_progress, self.log_progress_frequency)

        while not done and step_count < self.episode_max_steps:
            if not self.env.conn:
                 logging.warning("[EpisodeRunner] Conexão com o ambiente (proxy) perdida. Encerrando episódio.")
                 done = True
                 break

            timer.mark_total_start()

            step_count += 1
            current_sim_time = 0.0
            try:
                 if hasattr(self.env, 'conn') and self.env.conn and hasattr(self.env.conn, 'simulation'):
                      current_sim_time = self.env.conn.simulation.getTime()
                 else:
                      logging.warning("[EpisodeRunner] Conexão com simulação (proxy) inválida ao tentar obter tempo. Usando 0.0.")
                      done = True
                      break
            except Exception as e_time:
                 logging.warning(f"[EpisodeRunner] Erro ao obter tempo da simulação: {e_time}. Usando 0.0.")
                 done = True
                 break

            if self.log_step_progress and (step_count == 1 or step_count % self.log_progress_frequency == 0):
                SystemReporter.report_step_start(lm, step_count, current_sim_time, self.current_operation_mode)

            timer.mark_analysis_pre_start()
            if hasattr(self, 'strategic_coordinator'):
                 try:
                      state_values_for_gat = {tl_id: state for tl_id, state in current_states_dict.items() if isinstance(state, list)}
                      self.strategic_coordinator.update_if_needed(current_sim_time, state_values_for_gat)
                 except Exception as e_strat:
                      logging.error(f"[EpisodeRunner] Erro ao atualizar StrategicCoordinator: {e_strat}", exc_info=True)
            timer.mark_analysis_pre_end()

            timer.mark_decision_start()
            actions_to_apply, last_decision_data = self.decision_coordinator.get_coordinated_actions(
                current_states_dict, 
                self.state_history_manager.history,
                self.current_operation_mode,
                self.latest_veto_map # Inject background thought
            )
            timer.mark_decision_end()

            entropies = {}
            if last_decision_data: 
                 entropies = {tl_id: data['entropy'] for tl_id, data in last_decision_data.items() if 'entropy' in data}

            timer.mark_auth_start()
            authorized_actions = self.action_filter.filter_actions(
                actions_to_apply, 
                self.decision_coordinator.override_states,
                current_sim_time
            )
            timer.mark_auth_end()

            timer.mark_guardian_send_start()
            augmented_states_dict = {}
            if last_decision_data:
                augmented_states_dict = {tl_id: data['state_sequence'][-1] for tl_id, data in last_decision_data.items() if 'state_sequence' in data and data['state_sequence']}
            # Ensure we send something if augmented is missing
            state_to_send = augmented_states_dict if augmented_states_dict else current_states_dict
            self.guardian_comm.send_state(state_to_send, done)
            timer.mark_guardian_send_end()

            timer.mark_guardian_recv_start()
            vetos_recebidos = self.guardian_comm.receive_vetos()
            if vetos_recebidos:
                self.latest_veto_map = vetos_recebidos
            timer.mark_guardian_recv_end()

            if self.latest_veto_map and self.env.action_supervisor:
                self.env.action_supervisor.update_vetos(self.latest_veto_map)

            timer.mark_env_step_start()
            next_states_dict, rewards, done = self.env.step(authorized_actions)
            timer.mark_env_step_end()

            timer.mark_analysis_post_start()
            timer.mark_analysis_post_end()

            if next_states_dict:
                if "operation_mode" in next_states_dict:
                    self.current_operation_mode = next_states_dict["operation_mode"]
                if "override_commands" in next_states_dict:
                    commands = next_states_dict.pop("override_commands")
                    for command in commands:
                        semaphore_id = command.get("semaphore_id")
                        state = command.get("state")
                        if semaphore_id and state:
                            self.decision_coordinator.override_states[semaphore_id] = state
                            if self.env.action_supervisor:
                                self.env.action_supervisor.apply_hardware_override(semaphore_id, state)
                if "active_overrides" in next_states_dict:
                     self.decision_coordinator.override_states.clear()
                     self.decision_coordinator.override_states.update(next_states_dict.get("active_overrides", {}))
                     next_states_dict.pop("active_overrides", None)

            timer.mark_learning_start()
            if rewards and last_decision_data:
                self.learning_coordinator.store_experience(last_decision_data, rewards, done)

            agent_list = list(self.population_manager.agents.values())
            update_ts = int(self.update_timestep) if self.update_timestep > 0 else 2048
            if agent_list and (len(agent_list[0].memory) >= update_ts or (done and len(agent_list[0].memory) > 0)):
                self.learning_coordinator.update_agents(next_states_dict, done)
            timer.mark_learning_end()

            if next_states_dict:
                current_states_dict = next_states_dict
            else:
                 logging.warning("[EpisodeRunner] Dicionário de próximos estados está inválido. Encerrando episódio.")
                 done = True

            metrics_tracker.record_step(rewards, entropies)
            timer.log_if_needed(step_count)

        logging.info(f"Episódio {episode_count} concluído após {step_count} passos.")
        final_metrics = metrics_tracker.finalize_episode(episode_count)
        if hasattr(metrics_tracker, 'close'):
            metrics_tracker.close()
        return final_metrics