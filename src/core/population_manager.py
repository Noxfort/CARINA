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

# File: src/core/population_manager.py (Fixed: Initialize_population signature)
# Author: Gabriel Moraes
# Date: November 1, 2025

import logging
import random
import numpy as np
from collections import defaultdict
import sys
import os
from typing import TYPE_CHECKING

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend
    from core.lifecycle_manager import LifecycleManager
    from engine.environment import SumoEnvironment # Import required for type hint

class PopulationManager:
    """Manages the lifecycle and evolution of a population of agents."""

    def __init__(self, settings: dict, lifecycle_manager: 'LifecycleManager', locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.lifecycle_manager = lifecycle_manager
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        self.agents = {}
        self.guardians = {}
        
        self.pbt_config = {}
        self.evolution_cycle_rewards = []
        
        self._load_pbt_config()
        logging.info(lm.get_string("population_manager.init.manager_created"))
        if self.pbt_config.get('evolution_freq', -1) > 0:
            logging.info(lm.get_string("population_manager.init.evolution_freq", freq=self.pbt_config['evolution_freq']))
            logging.info(lm.get_string("population_manager.init.exploit_percentile", percentile=self.pbt_config['exploit_percentile']))

    def _load_pbt_config(self):
        if self.settings.has_section('PBT'):
            pbt_section = self.settings['PBT']
            self.pbt_config['evolution_freq'] = pbt_section.getint('evolution_frequency_episodes', fallback=-1)
            self.pbt_config['exploit_percentile'] = pbt_section.getint('exploitation_percentile', fallback=25)
            self.pbt_config['hyperparam_ranges'] = {
                'learning_rate': [float(v.strip()) for v in pbt_section.get('learning_rate_range').split(',')],
                'dropout_p': [float(v.strip()) for v in pbt_section.get('dropout_p_range').split(',')],
                'regularization_alpha': [float(v.strip()) for v in pbt_section.get('regularization_alpha_range').split(',')]
            }
        else:
            self.pbt_config['evolution_freq'] = -1

    # --- CHANGE 1: Function signature changed ---
    def initialize_population(self, environment: 'SumoEnvironment', max_local_obs_size: int, gat_output_dim: int) -> int:
        """
        Creates the initial population of agents.
        Returns the final observation size (n_observations).
        """
    # --- END OF CHANGE 1 ---
        lm = self.locale_manager
        logging.info(lm.get_string("population_manager.init.initializing_population"))
        
        fixed_hyperparams = {key: val for key, val in self.settings['AI_TRAINING'].items()}
        
        # This remains a local variable, not a class attribute
        initial_population_dna = {}
        
        for tl_id in environment.get_traffic_light_ids():
            dna = fixed_hyperparams.copy()
            if self.pbt_config.get('evolution_freq', -1) > 0:
                for key, value_range in self.pbt_config['hyperparam_ranges'].items():
                    dna[key] = random.uniform(value_range[0], value_range[1])
            initial_population_dna[tl_id] = dna
            
        # --- CHANGE 2: Updated LifecycleManager call ---
        # Now pass all the necessary arguments and store the results
        # in class attributes (self.agents, self.guardians)
        self.agents, self.guardians, n_observations = self.lifecycle_manager.create_all_controllers(
            environment, 
            initial_population_dna, 
            max_local_obs_size,
            gat_output_dim # Pass the missing argument
        )
        # --- END OF CHANGE 2 ---
        
        logging.info(lm.get_string("population_manager.init.population_created", count=len(self.agents)))

        # --- CHANGE 3: Returns the n_observations ---
        return n_observations
        # --- END OF CHANGE 3 ---

    def collect_episode_rewards(self, episode_rewards: dict):
        self.evolution_cycle_rewards.append(episode_rewards)

    def evolve(self):
        lm = self.locale_manager
        if not self.agents or self.pbt_config.get('evolution_freq', -1) <= 0:
            self.evolution_cycle_rewards.clear()
            return

        logging.info(lm.get_string("population_manager.evolve.start_cycle"))
        
        rewards_per_agent = defaultdict(list)
        for episode_rewards in self.evolution_cycle_rewards:
            for tl_id, reward in episode_rewards.items():
                rewards_per_agent[tl_id].append(reward)
        
        agent_scores = {tl_id: np.mean(rewards) for tl_id, rewards in rewards_per_agent.items() if rewards}
        
        if not agent_scores:
            logging.warning(lm.get_string("population_manager.evolve.no_scores_warning"))
            self.evolution_cycle_rewards.clear()
            return
            
        sorted_agents = sorted(agent_scores.items(), key=lambda item: item[1], reverse=True)
        
        exploit_percentile = self.pbt_config.get('exploit_percentile', 25)
        num_to_exploit = int(len(sorted_agents) * (exploit_percentile / 100))
        if num_to_exploit == 0 and len(sorted_agents) > 1:
            num_to_exploit = 1
            
        best_agents_ids = [agent_id for agent_id, _ in sorted_agents[:num_to_exploit]]
        worst_agents_ids = [agent_id for agent_id, _ in sorted_agents[-num_to_exploit:]]
        
        for worst_id in worst_agents_ids:
            if not best_agents_ids or worst_id in best_agents_ids:
                continue

            best_id = random.choice(best_agents_ids)
            worst_agent = self.agents.get(worst_id)
            best_agent = self.agents.get(best_id)

            if not worst_agent or not best_agent:
                continue

            logging.info(lm.get_string("population_manager.evolve.agent_copy", 
                                       worst_id=worst_id, worst_score=f"{agent_scores.get(worst_id, 0):.2f}",
                                       best_id=best_id, best_score=f"{agent_scores.get(best_id, 0):.2f}"))
            
            worst_agent.policy_net.load_state_dict(best_agent.policy_net.state_dict())
            new_hyperparams = best_agent.hyperparams.copy()
            
            param_to_mutate = random.choice(list(self.pbt_config['hyperparam_ranges'].keys()))
            mutation_factor = random.uniform(0.8, 1.2)
            current_value = float(new_hyperparams[param_to_mutate])
            new_value = current_value * mutation_factor
            
            min_val, max_val = self.pbt_config['hyperparam_ranges'][param_to_mutate]
            new_hyperparams[param_to_mutate] = np.clip(new_value, min_val, max_val)
            
            logging.info(lm.get_string("population_manager.evolve.mutating_param",
                                       param=param_to_mutate, 
                                       old_value=f"{current_value:.6f}", 
                                       new_value=f"{new_hyperparams[param_to_mutate]:.6f}"))
            worst_agent.update_hyperparameters(new_hyperparams)

        self.evolution_cycle_rewards.clear()
        logging.info(lm.get_string("population_manager.evolve.end_cycle"))