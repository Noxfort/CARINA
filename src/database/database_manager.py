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

    # =========================================================================
    # SIMULATION RUNS & EPISODES
    # =========================================================================

    def create_simulation_run(self, scenario_name: str) -> Optional[int]:
        return self.simulation_repo.create_simulation_run(scenario_name)

    def log_episode(self, run_id: int, episode_number: int, total_reward: float):
        self.simulation_repo.log_episode(run_id, episode_number, total_reward)
            
    def log_analysis_report(self, run_id: int, summary: str, report_content: str):
        self.simulation_repo.log_analysis_report(run_id, summary, report_content)

    # =========================================================================
    # SYNAPSE FLUID DYNAMICS
    # =========================================================================

    def insert_synapse_fluid_dynamics(self, samples: List[Dict]):
        self.fluid_dynamics_repo.insert_synapse_fluid_dynamics(samples)

    def query_fluid_dynamics_history(self) -> List[Dict]:
        return self.fluid_dynamics_repo.query_fluid_dynamics_history()

    def purge_old_fluid_dynamics(self, keep_minutes: int = 1440):
        self.fluid_dynamics_repo.purge_old_fluid_dynamics(keep_minutes)

    def get_fluid_dynamics_count(self) -> int:
        return self.fluid_dynamics_repo.get_fluid_dynamics_count()

    # =========================================================================
    # CLOUD FILE VAULT
    # =========================================================================

    def sync_file_to_vault(self, filepath: str, base_dir: str) -> bool:
        return self.cloud_vault_repo.sync_file_to_vault(filepath, base_dir)

    def sync_all_files_to_vault(self, base_dir: str):
        self.cloud_vault_repo.sync_all_files_to_vault(base_dir)