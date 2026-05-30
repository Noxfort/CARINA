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

# File: src/engine/topology_manager.py
# Author: Gabriel Moraes
# Date: February 17, 2026

import os
import logging
import sumolib # type: ignore
from typing import Dict, Tuple

from agents.local_agent import LocalAgent
from utils.paths import get_base_output_dir
from core.enums import Maturity

class TopologyManager:
    """
    Manager responsible for loading the road infrastructure and
    initializing (or restarting) the agent population.
    """

    def __init__(self, settings, locale_manager, log_dir):
        self.settings = settings
        self.locale_manager = locale_manager
        self.log_dir = log_dir
        
        # AI parameters extracted from settings
        self.n_actions = 3
        self.default_n_observations = self.settings.getint('AI_TRAINING', 'observation_space_size', fallback=80)

    def load_topology(self, map_path: str, state_extractor, maturity_manager, shared_pae=None) -> Tuple[Dict[str, LocalAgent], Dict[str, int]]:
        """
        Reads the SUMO network file, creates agents for each traffic light found,
        loads their brains (checkpoints), and restores their maturity level.

        Args:
            map_path (str): Absolute path to the .net.xml file.
            state_extractor (StateExtractor): Reference to load the structural neighborhood map.
            maturity_manager (MaturityManager): Reference to register new agents.
            shared_pae: Reference to the shared Universal PAE (may be None).

        Returns:
            Tuple[Dict, Dict]: Returns a dictionary of new agents and a dictionary of initial phases.
        """
        agents: Dict[str, LocalAgent] = {}
        initial_phases: Dict[str, int] = {}

        # --- LEGACY PARSER LOGS ---
        logging.info("[PARSER] Construindo mapa de vizinhança ESTRUTURAL a partir do arquivo de rede...")
        logging.info(f"   L- Lendo arquivo de rede: {map_path}")
        
        # 1. Update StateExtractor with the new topology
        state_extractor.load_topology(map_path)
        
        try:
            # 2. Network Reading via Sumolib
            net = sumolib.net.readNet(map_path, withInternal=False)
            tls_list = net.getTrafficLights()
            
            # Simulated structural neighborhood log to match legacy
            for tls in tls_list:
                tl_id = tls.getID()
                neighbors = []
                for n_tls in tls_list:
                    if n_tls.getID() != tl_id:
                        neighbors.append(n_tls.getID())
                logging.info(f"   L- Vizinhança Estrutural encontrada para '{tl_id}': {neighbors}")
            
            logging.info(f"[PARSER] Mapa de vizinhança ESTRUTURAL construído com sucesso para {len(tls_list)} semáforos.")
            logging.info("-" * 60)
            logging.info("ANÁLISE DA TOPOLOGIA DA REDE CONCLUÍDA")
            logging.info(f"  - Total de Semáforos (Nós): {len(tls_list)}")
            logging.info(f"  - Total de Conexões (Arestas): {len(net.getEdges())}")
            logging.info("-" * 60)
            
            # Base path for checkpoints
            checkpoints_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session", "checkpoints")

            logging.info("[POP_MANAGER] Inicializando população de agentes...")
            logging.info(f"[LIFECYCLE] Criando agentes e carregando checkpoints de '{checkpoints_dir}'...")
            
            obs_size_uniform = None

            # 3. Instantiation of Agents
            for tls in tls_list:
                tl_id = tls.getID()
                initial_phases[tl_id] = 0
                
                # Determine observation space size dynamically if possible
                obs_size = state_extractor.get_observation_space_size(tl_id)
                if obs_size == 0:
                    obs_size = self.default_n_observations
                
                if obs_size_uniform is None:
                    obs_size_uniform = obs_size
                    logging.info(f"[LIFECYCLE] Tamanho de observação uniforme para todos os agentes: {obs_size}")
                
                # Agent Creation
                new_agent = LocalAgent(
                    tlight_id=tl_id,
                    n_observations=obs_size,
                    n_actions=self.n_actions,
                    initial_hyperparams={},
                    log_dir=self.log_dir,
                    locale_manager=self.locale_manager,
                    shared_pae=shared_pae
                )
                
                # 4. Checkpoint and Maturity Smart Charging
                ckpt_path = os.path.join(checkpoints_dir, f"agent_{tl_id}.pth")
                saved_maturity_stage = "CHILD" # Default value if it is a new agent

                if os.path.exists(ckpt_path):
                    logging.info(f"OK [AGENTE {tl_id}] Checkpoint carregado de '{ckpt_path}'.")
                    # Now we capture the returned phase (ex: "TEEN")
                    saved_maturity_stage = new_agent.load_checkpoint(ckpt_path)
                else:
                    logging.warning(f"[AGENTE {tl_id}] Nenhum checkpoint encontrado em '{ckpt_path}'. Criando agente do zero.")
                    logging.info("   -> [GUARDIÃO] Cérebro de IA (Dueling DQN) criado. AMP ativado: True")
                    logging.info(f"   -> [CRIAÇÃO] Agente Local (PPO) e Guardião (DQN) criados para o Semáforo ID: '{tl_id}'.")
                    logging.info("      L- Treinamento com precisão mista (AMP) ativado: True")
                    self._create_initial_checkpoint(tl_id, new_agent)

                agents[tl_id] = new_agent
                
                # 5. Registration and State Restoration
                # First registers (which sets to CHILD by default if it doesn't exist)
                maturity_manager.register_agents([tl_id])
                
                # If the checkpoint indicated an advanced phase, we update the manager manually
                if saved_maturity_stage != "CHILD" and saved_maturity_stage in Maturity.__members__:
                    restored_enum = Maturity[saved_maturity_stage]
                    maturity_manager.agent_maturity[tl_id] = restored_enum
                    logging.info(f"   L- Maturidade de {tl_id} restaurada para {saved_maturity_stage}")

            logging.info(f"[LIFECYCLE] {len(agents)} agentes e {len(agents)} guardiões foram criados no total.")
            logging.info(f"[POP_MANAGER] População com {len(agents)} agentes criada com sucesso.")
            
        except Exception as e:
            logging.error(f"[TOPOLOGY] Critical error loading topology: {e}", exc_info=True)
            raise e

        return agents, initial_phases

    def _create_initial_checkpoint(self, tl_id: str, agent: LocalAgent):
        """Saves the agent's initial state to disk only if it does not exist."""
        try:
            ckpt_path = os.path.join(
                get_base_output_dir(), 
                "results", "hft_live_session", "checkpoints", 
                f"agent_{tl_id}.pth"
            )
            os.makedirs(os.path.dirname(ckpt_path), exist_ok=True)
            # Saves as CHILD explicitly
            agent.save_checkpoint(ckpt_path, maturity_stage="CHILD")
            logging.debug(f"[TOPOLOGY] Initial checkpoint created for {tl_id}")
        except Exception as e:
            logging.error(f"[TOPOLOGY] Failed to create physical checkpoint for {tl_id}: {e}")