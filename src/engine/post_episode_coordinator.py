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

# File: src/engine/post_episode_coordinator.py (MODIFIED TO SEND MATURITY UPDATES)
# Author: Gabriel Moraes
# Date: October 8, 2025

import logging
import numpy as np
from collections import Counter
from multiprocessing import Queue
import os
from typing import TYPE_CHECKING
# --- CHANGE 1: Import traci (which is actually our proxy) ---
import traci
# --- END OF CHANGE 1 ---

from core.population_manager import PopulationManager
from core.maturity_manager import MaturityManager
from core.lifecycle_manager import LifecycleManager
from core.system_reporter import SystemReporter

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class PostEpisodeCoordinator:
    """Orchestrates AI administrative tasks occurring between episodes."""

    def __init__(self, settings, population_manager: PopulationManager, maturity_manager: MaturityManager,
                 lifecycle_manager: LifecycleManager, 
                 db_data_queue: Queue, run_id: int, locale_manager: 'LocaleManagerBackend'):
        self.population_manager = population_manager
        self.maturity_manager = maturity_manager
        self.lifecycle_manager = lifecycle_manager
        self.db_data_queue = db_data_queue
        self.run_id = run_id
        self.locale_manager = locale_manager
        
        self.save_freq = settings.getint('CHECKPOINTING', 'save_frequency_episodes', fallback=0)
        pbt_settings = settings['PBT']
        self.pbt_freq = pbt_settings.getint('evolution_frequency_episodes', fallback=0)
        
        logging.info(self.locale_manager.get_string("post_episode_coordinator.init.created"))

    def run(self, episode_count: int, episode_metrics: dict):
        """
        Executa todas as tarefas de final de episódio relacionadas à IA.
        """
        lm = self.locale_manager
        if not episode_metrics:
            logging.warning(lm.get_string("post_episode_coordinator.run.no_metrics_warning"))
            return

        for agent in self.population_manager.agents.values():
            agent.episodes_done = episode_count

        # Calibrator logic removed. Dynamic entropy rules are handled internally by MaturityManager
        
        promotion_happened = self.maturity_manager.check_and_promote_agents(episode_metrics)

        # --- CHANGE 2: If a promotion happened, notify Central Control ---
        if promotion_happened:
            logging.info("Promoção detectada. Enviando estado de maturidade atualizado...")
            traci.update_maturity_state(self.maturity_manager.get_state())
        # --- END OF CHANGE 2 ---

        if self.pbt_freq > 0:
            rewards_only = {agent_id: metrics['reward'] for agent_id, metrics in episode_metrics.items()}
            self.population_manager.collect_episode_rewards(rewards_only)
            if episode_count > 0 and episode_count % self.pbt_freq == 0:
                self.population_manager.evolve()

        periodic_save_triggered = self.save_freq > 0 and episode_count > 0 and episode_count % self.save_freq == 0
        
        if periodic_save_triggered or promotion_happened:
            reason = ""
            if promotion_happened:
                reason = lm.get_string("post_episode_coordinator.checkpoint.reason_promotion")
            else:
                reason = lm.get_string("post_episode_coordinator.checkpoint.reason_periodic", episode=episode_count)
            
            maturity_state_path = os.path.join(self.lifecycle_manager.scenario_checkpoint_dir, "maturity_state.json")
            self.maturity_manager.save_state(maturity_state_path)

            self.lifecycle_manager.save_all_checkpoints(
                self.population_manager.agents,
                reason
            )
        
        total_reward = sum(m['reward'] for m in episode_metrics.values())
        maturity_counts = Counter(self.maturity_manager.agent_maturity.values())
        
        # Calibration status is now irrelevant because the limit is dynamic based on time
        calibration_status_text = lm.get_string("reporter.calib_status_done")
        
        SystemReporter.report_school_bulletin(
            lm,
            episode_count,
            total_reward,
            maturity_counts,
            calibration_status_text
        )

        try:
            log_payload = {
                "run_id": self.run_id,
                "episode_number": episode_count,
                "total_reward": total_reward
            }
            data_packet = {"type": "log_episode", "payload": log_payload}
            self.db_data_queue.put(data_packet)
        except Exception as e:
            logging.error(lm.get_string("post_episode_coordinator.run.db_queue_error", error=e))