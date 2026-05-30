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

# File: src/engine/analysis_runner.py (FIXED TO CALL UNIFIED RUNNER)
# Author: Gabriel Moraes
# Date: October 6, 2025

"""
Defines the AnalysisRunner, a specialist class responsible for
executing the system's analysis phase.
"""
import logging
import sys
import os
from typing import List, Dict, Any

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from engine.episode_runner import EpisodeRunner
from core.childhood_analyzer import ChildhoodAnalyzer

class AnalysisRunner:
    """
    Orchestrates the execution of analysis episodes to establish
    the baseline and traffic profiles, using the EpisodeRunner.
    """
    def __init__(self, episode_runner: EpisodeRunner, analyzer: ChildhoodAnalyzer):
        """
        Inicializa o Executor de Análise.
        """
        self.episode_runner = episode_runner
        self.analyzer = analyzer
        self.locale_manager = analyzer.locale_manager
        logging.info("[ANALYSIS_RUNNER] Executor da Fase de Análise criado.")

    def run(self) -> tuple:
        """
        Executa o ciclo completo de análise e retorna os resultados.
        """
        lm = self.locale_manager
        # The log has been generalized as mode is no longer an important distinction here.
        logging.info("[ANALYSIS_RUNNER] A iniciar fase de análise inicial...")
        
        all_episode_metrics: List[Dict[str, Any]] = []
        
        for i in range(self.analyzer.analysis_episodes):
            logging.info(f"   L- A executar episódio de análise {i+1}/{self.analyzer.analysis_episodes}...")
            
            # --- MAIN CHANGE HERE ---
            # The call to 'run' now no longer needs the 'mode' parameter.
            # The episode performed will be a full training episode.
            episode_metrics = self.episode_runner.run(episode_count=(i + 1))
            # --- END OF CHANGE ---
            
            if episode_metrics:
                all_episode_metrics.append(episode_metrics)
        
        # The results of these first training episodes are used to define the baseline.
        profiles, baseline = self.analyzer.run_analysis(all_episode_metrics)
        
        self.analyzer.save_to_cache(profiles, baseline)
        
        return profiles, baseline