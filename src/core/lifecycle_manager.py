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

# File: src/core/lifecycle_manager.py
# Author: Gabriel Moraes
# Date: December 16, 2025

import os
import logging
import configparser
import sys
from typing import TYPE_CHECKING

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend
    from engine.environment import SumoEnvironment

from agents.local_agent import LocalAgent
from agents.guardian_agent import GuardianAgent
from core.system_reporter import SystemReporter

class LifecycleManager:
    """Manages the lifecycle (creation, saving, loading) of the agents."""

    def __init__(self, settings: configparser.ConfigParser, log_dir: str,
                 scenario_results_dir: str, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.log_dir = log_dir
        self.locale_manager = locale_manager
        
        self.scenario_checkpoint_dir = os.path.join(scenario_results_dir, "checkpoints")
        os.makedirs(self.scenario_checkpoint_dir, exist_ok=True)
        
        lm = self.locale_manager
        logging.info(lm.get_string("lifecycle_manager.init.manager_created"))
        logging.info(lm.get_string("lifecycle_manager.init.checkpoint_dir_set", path=self.scenario_checkpoint_dir))

    def create_all_controllers(self, 
                               environment: 'SumoEnvironment', 
                               initial_population_dna: dict, 
                               max_local_obs_size: int,
                               gat_output_dim: int,
                               shared_pae=None) -> tuple:
        """
        Creates all agent instances with a uniform observation size.
        Returns (agents, guardians, n_observations)
        """
        lm = self.locale_manager
        if not self.scenario_checkpoint_dir:
            error_msg = lm.get_string("lifecycle_manager.create.no_checkpoint_dir_error")
            raise RuntimeError(error_msg)

        logging.info(lm.get_string("lifecycle_manager.create.loading_checkpoints", path=self.scenario_checkpoint_dir))
        
        agents, guardians = {}, {}
        tlight_ids = environment.get_traffic_light_ids()
        
        # Calculating the total size of the observation
        num_override_flags = 2
        uniform_observation_size = max_local_obs_size + gat_output_dim + num_override_flags

        logging.info(lm.get_string("lifecycle_manager.create.uniform_obs_size", size=uniform_observation_size))

        for tl_id in tlight_ids:
            agent_log_dir = os.path.join(self.log_dir, f"agent_{tl_id}")
            os.makedirs(agent_log_dir, exist_ok=True)
            
            agent_dna = initial_population_dna.get(tl_id)
            if not agent_dna:
                logging.error(lm.get_string("lifecycle_manager.create.no_dna_found", tl_id=tl_id))
                continue

            agent = LocalAgent(
                tlight_id=tl_id,
                n_observations=uniform_observation_size,
                n_actions=3,
                initial_hyperparams=agent_dna,
                log_dir=agent_log_dir,
                locale_manager=self.locale_manager,
                shared_pae=shared_pae
            )
            checkpoint_path = os.path.join(self.scenario_checkpoint_dir, f"agent_{tl_id}.pth")
            
            # 1. Try to load (if it exists)
            agent.load_checkpoint(checkpoint_path)
            
            # 2. --- IMPORTANT FIX ---
            # Immediately saves the current state (whether loaded or newly created).
            # This ensures that the physical .pth file exists in the folder so that the UI (XAI Viewer)
            # be able to detect the agent in the directory scan.
            agent.save_checkpoint(checkpoint_path)
            # ------------------------------

            agents[tl_id] = agent
            
            guardian_config = self.settings['GUARDIAN_AGENT']
            traffic_rules_config = self.settings['TRAFFIC_RULES'] if 'TRAFFIC_RULES' in self.settings else guardian_config
            guardians[tl_id] = GuardianAgent(
                aiconfig=guardian_config,
                traffic_rules_config=traffic_rules_config,
                locale_manager=self.locale_manager,
                shared_pae=shared_pae
            )
            
            SystemReporter.report_agent_creation(tl_id, agent.scaler.is_enabled(), lm)
            
        logging.info(lm.get_string("lifecycle_manager.create.creation_complete", num_agents=len(agents), num_guardians=len(guardians)))
        
        return agents, guardians, uniform_observation_size

    def save_all_checkpoints(self, agents: dict, reason: str):
        lm = self.locale_manager
        if not self.scenario_checkpoint_dir: return
        if not agents: return
        
        logging.info(lm.get_string("lifecycle_manager.save.starting_checkpoint", reason=reason, path=self.scenario_checkpoint_dir))
        for tl_id, agent in agents.items():
            save_path = os.path.join(self.scenario_checkpoint_dir, f"agent_{tl_id}.pth")
            agent.save_checkpoint(save_path)
        logging.info(lm.get_string("lifecycle_manager.save.checkpoint_complete"))