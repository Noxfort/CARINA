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

# File: src/engine/environment.py (Refactored with robust TraCIException import)
# Author: Gabriel Moraes
# Date: October 26, 2025

import logging
import configparser
import sys
import os
from typing import TYPE_CHECKING, Dict, Any, Tuple, List, Optional

# Add 'src' directory to path (kept)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from engine.state_extractor import StateExtractor
from engine.reward_calculator import RewardCalculator
from engine.action_supervisor import ActionSupervisor

class SumoEnvironment:
    """The environment 'Maestro': orchestrates the specialists."""

    def __init__(self, settings: configparser.ConfigParser, locale_manager: 'LocaleManagerBackend') -> None:
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager

        self.conn = None # Assigned via Dependency Injection if necessary or managed by ActionSupervisor
        self.scenario_path = "synapse_managed_session"

        self.episode_max_steps = self.settings.getint('AI_TRAINING', 'episode_max_steps', fallback=5000)
        self.current_episode_steps = 0

        self.state_extractor: StateExtractor | None = None
        self.reward_calculator: RewardCalculator | None = None
        self.action_supervisor: ActionSupervisor | None = None

        self._last_batched_data = {}

        logging.info(lm.get_string("environment.init.maestro_created"))

    def connect(self, conn_proxy: Any = None) -> None:
        """Prepares the environment and binds the Synapse connection."""
        lm = self.locale_manager
        
        # The real connection now comes from outside or from the CentralController, the engine just passes it on
        self.conn = conn_proxy

        if self.conn:
            try:
                # Initialize the experts
                self.state_extractor = StateExtractor(self.conn, self.locale_manager)
                self.reward_calculator = RewardCalculator(self.settings, self.locale_manager)
                self.action_supervisor = ActionSupervisor(self.conn, self.settings, self.state_extractor, self.locale_manager)

                logging.info(lm.get_string("environment.connect.success", scenario=self.scenario_path))

            except Exception as e_general:
                 logging.error(f"[Environment] Erro inesperado durante a inicialização pós-conexão: {e_general}", exc_info=True)
                 self.scenario_path = lm.get_string("environment.connect.unknown_scenario")

    def close(self) -> None:
        """Clears local references (connection managed remotely)."""
        self.conn = None

    def reset(self) -> None:
        """Resets the environment for a new episode, delegating to specialists."""
        lm = self.locale_manager
        logging.info(lm.get_string("environment.reset.start"))

        # Checks if the connection (proxy) exists
        if not self.conn:
            logging.error(lm.get_string("environment.error.reset_no_conn", default="[Environment] Attempt to reset without active connection."))
            # Depending on the logic, it may return or throw an error
            return # Or raise RuntimeError("...")

        # Actual vehicle cleaning occurs on the Synapse side
        # Environment now just clears its internal counters

        # Reset experts (ActionSupervisor needs to be reset)
        if self.action_supervisor:
            self.action_supervisor.reset()
        # StateExtractor and RewardCalculator generally do not need internal state reset here

        self.current_episode_steps = 0
        self._last_batched_data = {}
        logging.info(lm.get_string("environment.reset.success"))

    def step(self, actions: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """Executes a full step in the environment, orchestrating the specialists."""
        if not self.conn:
             logging.error(self.locale_manager.get_string("environment.error.step_no_conn", default="[Environment] Attempt to step without active connection."))
             return {}, {}, True # Returns empty state, empty reward, done=True

        try:
            # Applies actions via ActionSupervisor (which uses the self.conn proxy)
            if self.action_supervisor:
                self.action_supervisor.apply_actions(actions)

            # --- The simulation step is delegated to the proxy ---
            # The proxy sends 'simulationStep' to the Controller, which executes it
            # and ONLY THEN responds to the proxy, unlocking this call.
            # self.conn.simulationStep() # This line is NOT needed here anymore, as the proxy handles it internally.

            # Gets ALREADY UPDATED data from the Controller via proxy
            # The Controller collects the data AFTER the actual simulationStep has occurred.
            current_batched_data = self.conn.custom.get_batched_step_data()

            if not current_batched_data:
                logging.warning(self.locale_manager.get_string("environment.step.no_batch_data"))
                # If there is no data, we consider it the end or a serious error
                self.close() # Close the proxy connection
                return {}, {}, True # Returns empty state, empty reward, done=True

            self.current_episode_steps += 1

            # Checks termination conditions (should the Controller include MinExpectedNumber in the data?)
            # For now, we rely on the Controller to move forward and max_steps
            # Or we can ask the Controller to include 'min_expected_number' in the batch
            min_expected_num = current_batched_data.get('sim_min_expected_number', 1) # Assume > 0 if it doesn't come
            time_limit_reached = self.current_episode_steps >= self.episode_max_steps
            natural_end = min_expected_num == 0 # Use batch value if available
            done = time_limit_reached or (natural_end and self.current_episode_steps > 1) # Make sure you don't end up at step 0

            # Extracts the state of received data
            next_states = {}
            if self.state_extractor:
                next_states = self.state_extractor.get_global_state_from_batch(current_batched_data)

            # Ensures important metadata keys are passed on (maintained)
            if "override_commands" in current_batched_data:
                next_states["override_commands"] = current_batched_data["override_commands"]
            if "active_overrides" in current_batched_data:
                next_states["active_overrides"] = current_batched_data["active_overrides"]
            if "operation_mode" in current_batched_data:
                next_states["operation_mode"] = current_batched_data["operation_mode"]

            # Calculates rewards
            rewards = {}
            if self.reward_calculator:
                rewards = self.reward_calculator.calculate_rewards_from_batch(
                    list(next_states.keys()), # Uses the keys from the extracted state
                    current_batched_data,
                    self._last_batched_data # Data from the previous step
                )

            # Save current data for next reward calculation
            self._last_batched_data = current_batched_data

            return next_states, rewards, done

        except Exception as e_general:
             logging.error(self.locale_manager.get_string("environment.error.step_unexpected", default="[Environment] Unexpected error during step: {error}", error=e_general), exc_info=True)
             self.close()
             return {}, {}, True


    def get_global_state(self) -> Dict[str, Any]:
        """Gets the initial state of the environment, before the first step."""
        if not self.conn:
             logging.error(self.locale_manager.get_string("environment.error.get_state_no_conn", default="[Environment] Attempt to get_global_state without active connection."))
             return {}
        try:
            # Request initial data from the Controller via proxy
            initial_batch = self.conn.custom.get_batched_step_data()
            if not initial_batch:
                 logging.warning(self.locale_manager.get_string("environment.error.no_initial_batch", default="[Environment] Initial batch data not received."))
                 return {}

            self._last_batched_data = initial_batch # Save for the first step

            initial_states = self.state_extractor.get_global_state_from_batch(initial_batch) if self.state_extractor else {}

            # Ensures that the initial operating mode is also propagated (maintained)
            if "operation_mode" in initial_batch:
                initial_states["operation_mode"] = initial_batch["operation_mode"]

            return initial_states

        except Exception as e_general:
            logging.error(self.locale_manager.get_string("environment.error.get_state_unexpected", default="[Environment] Unexpected error getting initial global state: {error}", error=e_general), exc_info=True)
            self.close()
            return {}


    def get_traffic_light_ids(self) -> List[str]:
        """Delegates ID retrieval to the StateExtractor."""
        return self.state_extractor.get_traffic_light_ids() if self.state_extractor else []

    def get_observation_space_size_for_tl(self, tl_id: str) -> int:
        """Delegates the calculation of the observation size to the StateExtractor."""
        # Note: StateExtractor now uses self.conn (proxy) internally
        return self.state_extractor.get_observation_space_size_for_tl(tl_id) if self.state_extractor else 0

    def get_num_green_phases_for_tl(self, tl_id: str) -> int:
        """Delegates the retrieval of the number of green stages to the StateExtractor."""
        # Note: StateExtractor now uses self.conn (proxy) and internal cache
        return self.state_extractor._get_green_phases_for_tl(tl_id) if self.state_extractor else 0 # Call curly method