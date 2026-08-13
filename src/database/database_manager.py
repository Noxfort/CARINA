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

# File: src/database/database_manager.py
# Author: Gabriel Moraes
# Date: May 31, 2026

import os
import sys
import logging
from typing import TYPE_CHECKING, Any, List, Dict, Optional

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.database.db_engine import DatabaseEngine
from src.repositories.simulation_repo import SimulationRepository
from src.repositories.fluid_dynamics_repo import FluidDynamicsRepository
from src.repositories.cloud_vault_repo import CloudVaultRepository
from src.repositories.step_decision_repo import StepDecisionRepository
from src.database.step_decision_worker import StepDecisionWorker

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend

class DatabaseManager:
    """
    Facade Pattern.
    Manages all interactions with the database. 
    Acts as a Unit of Work delegating calls to specialized repositories
    to respect the Single Responsibility Principle (SRP).
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend', db_name: str = "carina_data.db"):
        self.locale_manager = locale_manager
        
        # Initializes the Central Engine (Infrastructure/Connection)
        self.engine = DatabaseEngine(locale_manager=locale_manager, db_name=db_name)
        
        # Initializes the Specialized Repositories (Business Logic)
        self.simulation_repo = SimulationRepository(self.engine, locale_manager)
        self.fluid_dynamics_repo = FluidDynamicsRepository(self.engine, locale_manager)
        self.cloud_vault_repo = CloudVaultRepository(self.engine, locale_manager)
        self.step_decision_repo = StepDecisionRepository(self.engine, locale_manager)

        # Async telemetry worker thread
        self.step_decision_worker = StepDecisionWorker(self.step_decision_repo)
        self.step_decision_worker.start()

    # =========================================================================
    # SIMULATION RUNS & EPISODES
    # =========================================================================

    def create_simulation_run(self, scenario_name: str) -> Optional[int]:
        return self.simulation_repo.create_simulation_run(scenario_name)

    def log_episode(self, run_id: int, episode_number: int, total_reward: float):
        self.simulation_repo.log_episode(run_id, episode_number, total_reward)
            
    def log_analysis_report(self, run_id: int, summary: str, report_content: str):
        self.simulation_repo.log_analysis_report(run_id, summary, report_content)

    def get_sas_analysis_cache(self, scenario_name: str) -> dict:
        return self.simulation_repo.get_sas_analysis_cache(scenario_name)

    def save_sas_analysis_cache(self, scenario_name: str, cache_data: dict):
        self.simulation_repo.save_sas_analysis_cache(scenario_name, cache_data)

    def get_mfd_analysis_baselines(self, scenario_name: str) -> tuple:
        return self.simulation_repo.get_mfd_analysis_baselines(scenario_name)

    def save_mfd_analysis_baselines(self, scenario_name: str, snapshot: dict):
        self.simulation_repo.save_mfd_analysis_baselines(scenario_name, snapshot)

    # =========================================================================
    # SYNAPSE FLUID DYNAMICS
    # =========================================================================

    def insert_synapse_fluid_dynamics(self, samples: List[Dict]):
        self.fluid_dynamics_repo.insert_synapse_fluid_dynamics(samples)

    def query_fluid_dynamics_history(self, limit_seconds: Optional[int] = None) -> List[Dict]:
        return self.fluid_dynamics_repo.query_fluid_dynamics_history(limit_seconds=limit_seconds)

    def query_traffic_history(self, limit_seconds: Optional[int] = None) -> List[Dict]:
        """Alias for query_fluid_dynamics_history to avoid backward-compatibility errors."""
        return self.query_fluid_dynamics_history(limit_seconds=limit_seconds)

    def query_fluid_dynamics_history_batches(self, limit_seconds: Optional[int] = None, batch_size: int = 50000):
        return self.fluid_dynamics_repo.query_fluid_dynamics_history_batches(limit_seconds=limit_seconds, batch_size=batch_size)

    def query_aggregated_fluid_dynamics(self, limit_seconds: Optional[int] = None) -> List[Dict]:
        return self.fluid_dynamics_repo.query_aggregated_fluid_dynamics(limit_seconds=limit_seconds)

    def purge_old_fluid_dynamics(self, keep_minutes: int = 1440):
        self.fluid_dynamics_repo.purge_old_fluid_dynamics(keep_minutes)

    def consolidate_and_purge_old_data(self, keep_hours: int = 48):
        self.fluid_dynamics_repo.consolidate_and_purge_old_data(keep_hours)

    def get_fluid_dynamics_count(self) -> int:
        return self.fluid_dynamics_repo.get_fluid_dynamics_count()

    def get_fluid_dynamics_time_range(self) -> float:
        return self.fluid_dynamics_repo.get_fluid_dynamics_time_range()

    def get_fluid_dynamics_min_max_timestamps(self, limit_seconds: Optional[int] = None):
        return self.fluid_dynamics_repo.get_fluid_dynamics_min_max_timestamps(limit_seconds=limit_seconds)

    # =========================================================================
    # CLOUD FILE VAULT
    # =========================================================================

    def sync_file_to_vault(self, filepath: str, base_dir: str) -> bool:
        return self.cloud_vault_repo.sync_file_to_vault(filepath, base_dir)

    def sync_all_files_to_vault(self, base_dir: str):
        self.cloud_vault_repo.sync_all_files_to_vault(base_dir)

    def fetch_file_from_vault(self, relative_path: str) -> Optional[bytes]:
        return self.cloud_vault_repo.fetch_file_from_vault(relative_path)

    def restore_file_from_vault(self, relative_path: str, target_filepath: str) -> bool:
        return self.cloud_vault_repo.restore_file_from_vault(relative_path, target_filepath)

    def restore_all_files_from_vault(self, base_dir: str) -> int:
        return self.cloud_vault_repo.restore_all_files_from_vault(base_dir)