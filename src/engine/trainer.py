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

# File: src/engine/trainer.py
# Author: Gabriel Moraes
# Date: 2026-02-22

import logging
import os
import sys
import time
import types
import configparser
import torch
from collections import defaultdict
from multiprocessing import Queue
from multiprocessing.connection import Connection

# Ensure src path is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Internal Modules ---
from utils.locale_manager_backend import LocaleManagerBackend
from controller.connection_manager import HardwareConnectionManager
from engine.action_supervisor import ActionSupervisor
from engine.state_extractor import StateExtractor
from core.maturity_manager import MaturityManager
from core.action_authorizer import ActionAuthorizer
from core.system_reporter import SystemReporter
from core.enums import Maturity
from utils.paths import get_base_output_dir

# --- SRP Specialized Modules ---
from engine.reward_computer import RewardComputer
from engine.topology_manager import TopologyManager
from engine.cycle_manager import CycleManager
from engine.input_preprocessor import InputPreprocessor
from manager.agent_manager import AgentManager
from engine.step_processor import StepProcessor
from engine.event_router import EventRouter

class Trainer:
    """
    The Orchestrator of CARINA's AI Engine (Refactored).
    
    Acts as a high-level coordinator that delegates specific tasks to specialized managers:
    - Lifecycle & Persistence -> AgentManager
    - Data Preparation -> InputPreprocessor
    - Topology Parsing -> TopologyManager
    - Execution -> ActionSupervisor
    """

    def __init__(self, settings: configparser.ConfigParser, log_dir: str, gpu_info: str,
                 pipe_conn: Connection, guardian_state_queue: Queue,
                 guardian_signal_queue: Queue, db_data_queue: Queue):
        
        self.settings = settings
        self.log_dir = log_dir
        self.pipe_conn = pipe_conn
        self.gpu_info = gpu_info
        
        self.locale_manager = LocaleManagerBackend()
        self.lm = self.locale_manager
        
        # System State
        self.is_running = True
        self.agents = {} 
        self.strategist = None
        self.current_map_path = None
        
        # AI Configuration
        self.sequence_length = self.settings.getint('AI_TRAINING', 'sequence_length', fallback=4)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # --- NEW: Specialized Managers ---
        self.agent_manager = AgentManager(
            settings=self.settings,
            device=self.device,
            project_root=project_root
        )
        
        self.input_preprocessor = InputPreprocessor(
            sequence_length=self.sequence_length,
            device=self.device
        )
        # ---------------------------------

        # Hardware Abstraction (Refactored to support multi-intersection direct connections)
        self.connection_manager = HardwareConnectionManager()
            
        # Core Engine Components
        self.state_extractor = StateExtractor(self.locale_manager)
        
        self.action_supervisor = ActionSupervisor(
            connection_manager=self.connection_manager,
            settings=self.settings,
            state_extractor=self.state_extractor,
            locale_manager=self.locale_manager
        )

        self.action_authorizer = ActionAuthorizer(
            settings=self.settings,
            locale_manager=self.locale_manager
        )

        # Population Proxy (Shared Context)
        self.population_proxy = types.SimpleNamespace(agents={})
        
        self.maturity_manager = MaturityManager(
            settings=self.settings,
            locale_manager=self.locale_manager,
            population_manager=self.population_proxy
        )
        
        self.reward_computer = RewardComputer(
            settings=self.settings, 
            state_extractor=self.state_extractor
        )
        
        self.topology_manager = TopologyManager(
            settings=self.settings,
            locale_manager=self.locale_manager,
            log_dir=self.log_dir
        )
        
        self.cycle_manager = CycleManager(
            maturity_manager=self.maturity_manager,
            pipe_conn=self.pipe_conn
        )
        
        self.step_processor = StepProcessor(
            settings=self.settings, 
            locale_manager=self.locale_manager, 
            agent_manager=self.agent_manager, 
            input_preprocessor=self.input_preprocessor, 
            state_extractor=self.state_extractor, 
            action_supervisor=self.action_supervisor, 
            action_authorizer=self.action_authorizer, 
            maturity_manager=self.maturity_manager, 
            reward_computer=self.reward_computer, 
            cycle_manager=self.cycle_manager, 
            pipe_conn=self.pipe_conn
        )
        
        self.event_router = EventRouter(
            pipe_conn=self.pipe_conn, 
            trainer_instance=self, 
            agent_manager=self.agent_manager, 
            step_processor=self.step_processor
        )
        
        logging.info(f"Trainer Orchestrator ready. GPU: {gpu_info}")

    def start_continuous_service(self):
        # Signals to the API/Controller that the backend completed 
        # loading its tools and is waiting for the map geometry
        try:
            self.pipe_conn.send(('system', 'backend_ready', (), {}))
        except Exception as e:
            logging.error(f"[Trainer] Erro ao enviar sinal de backend_ready: {e}")
            
        self.event_router.start_continuous_service()

    def _load_map(self, map_path: str):
        """
        Delegates environment setup to AgentManager.
        """
        # --- LEGACY STARTUP LOGS ---
        logging.info("[INIT_ORCHESTRATOR] Fase de Setup iniciada...")
        logging.info("[SERVICE_MANAGER] Gerenciador de Serviços criado.")
        
        # Simulate DB Connection
        db_path = os.path.join(get_base_output_dir(), "results", "database", "carina_data.db")
        logging.info(f"[DB_MANAGER] Gerenciador de Banco de Dados apontando para: {db_path}")
        map_name = os.path.basename(map_path).replace('.net.xml', '')
        logging.info(f"[DB_MANAGER] Nova execução registrada com sucesso (Cenário: {map_name}).")
        logging.info("--- NOVA EXECUÇÃO REGISTRADA COM RUN_ID: 1 ---")
        
        logging.info("[STRATEGIC_COORD] Coordenador Estratégico (GAT) criado.")
        logging.info("[STRATEGIC_COORD] Inicializando o subsistema estratégico...")
        
        self.current_map_path = map_path 
        self.agents.clear()
        
        self.step_processor.reset_state()
        
        try:
            # Delegate complex loading logic
            self.agents, current_phases, self.strategist, self.guardians = self.agent_manager.setup_environment(
                map_path=map_path,
                topology_manager=self.topology_manager,
                state_extractor=self.state_extractor,
                maturity_manager=self.maturity_manager
            )
            
            logging.info("[MATURITY_MANAGER] Diretor da Escola de Pilotagem criado.")
            logging.info("   L- Meta de Desempenho para Graduação (Baseline): Recompensa > -0.00")
            logging.info(f"[MATURITY_MANAGER] {len(self.agents)} agentes registrados na fase: INFÂNCIA.")
            logging.info("Enviando estado de maturidade inicial para o Controle Central...")
            
            logging.info("[LEARNER] Coordenador de Aprendizado criado.")
            logging.info("[THRESHOLD_CALIBRATOR] Calibrador de Confiança criado.")
            logging.info("   L- Irá monitorar a estabilidade em uma janela de 10 episódios.")
            
            self.step_processor.set_current_phases(current_phases)
            if hasattr(self.step_processor, 'set_guardians'):
                self.step_processor.set_guardians(self.guardians)

            # Initial Cycle Check
            self.cycle_manager.evaluate_cycle(0, self.agents, self.step_processor.accumulated_metrics)
            
        except Exception as e:
            logging.error(f"Failed to load environment: {e}", exc_info=True)