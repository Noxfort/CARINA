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

# File: ui/handlers/map_asset_loader.py
# Author: Gabriel Moraes
# Date: December 16, 2025

"""
Define o MapAssetLoader.

Esta classe especialista tem a responsabilidade única de encontrar e carregar
arquivos de ativos (mapas, coordenadas) do diretório de resultados da
simulação mais recente.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple

# Importing the src is necessary for the UI module to find the utils module
import sys
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path_to_add = os.path.join(project_root_path, "src")
if src_path_to_add not in sys.path:
    sys.path.insert(0, src_path_to_add)

from src.utils.map_data_parser import parse_map_data

class MapAssetLoader:
    """Encontra e carrega arquivos de ativos da simulação mais recente."""

    def __init__(self):
        """Inicializa o carregador de ativos."""
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _find_latest_scenario_dir(self) -> str | None:
        """Encontra o caminho absoluto para a pasta de cenário mais recente."""
        try:
            from src.utils.paths import get_base_output_dir
            results_dir = os.path.join(get_base_output_dir(), "results")
            if not os.path.exists(results_dir):
                logging.warning("[AssetLoader] Diretório 'results' não encontrado.")
                return None
            
            # Defines a set of service folders to ignore.
            ignored_dirs = {"database"}
            
            # Filters the directory list to remove ignored folders.
            all_scenarios = [
                d for d in os.listdir(results_dir) 
                if os.path.isdir(os.path.join(results_dir, d)) and d not in ignored_dirs
            ]

            if not all_scenarios:
                logging.warning("[AssetLoader] Nenhum cenário encontrado no diretório 'results'.")
                return None
                
            latest_scenario_name = max(all_scenarios, key=lambda d: os.path.getmtime(os.path.join(results_dir, d)))
            return os.path.join(results_dir, latest_scenario_name)
        except Exception as e:
            logging.error(f"[AssetLoader] Erro ao procurar o diretório do cenário mais recente: {e}")
            return None

    def get_asset_path(self, asset_type: str, asset_filename: str) -> str | None:
        """
        Constrói o caminho para um ativo específico no cenário mais recente.
        """
        latest_scenario_dir = self._find_latest_scenario_dir()
        if not latest_scenario_dir:
            return None
        
        asset_path = os.path.join(latest_scenario_dir, asset_type, asset_filename)
        return asset_path if os.path.exists(asset_path) else None

    def load_coordinates(self) -> Dict[str, Any] | None:
        """
        Encontra e carrega o conteúdo do arquivo de coordenadas mais recente.
        """
        coords_path = self.get_asset_path("maps", "map_coords.json")
        if not coords_path:
            logging.error("[AssetLoader] Não foi possível encontrar o arquivo 'map_coords.json'.")
            return None
        
        try:
            with open(coords_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"[AssetLoader] Falha ao ler ou processar 'map_coords.json': {e}")
            return None

    def load_map_data(self) -> Tuple[Dict, Any, Dict] | None:
        """
        Encontra e carrega os dados brutos do mapa.
        Prioriza o arquivo 'map_topology.json' (Novo Sistema Synapse).
        Faz fallback para arquivos XML (Sistema Legado) se o JSON não existir.
        """
        latest_scenario_dir = self._find_latest_scenario_dir()
        if not latest_scenario_dir:
            logging.debug("[AssetLoader] Diretório de cenário não encontrado para carregar dados do mapa.")
            return None

        try:
            maps_dir = os.path.join(latest_scenario_dir, "maps")
            
            # --- ATTEMPT 1: Load Topology JSON (Synapse/HFT Standard) ---
            json_topology_path = os.path.join(maps_dir, "map_topology.json")
            if os.path.exists(json_topology_path):
                logging.info(f"[AssetLoader] Carregando topologia vetorial moderna: {json_topology_path}")
                try:
                    with open(json_topology_path, 'r', encoding='utf-8') as f:
                        topology = json.load(f)
                    
                    # Extract lists from JSON
                    nodes_list = topology.get("nodes", [])
                    edges_list = topology.get("edges", [])
                    bounds = topology.get("bounds", {})

                    # Converts the node list to a Dictionary {id: data}, as expected by the UI
                    nodes_dict = {node["id"]: node for node in nodes_list}

                    # Returns in the format (nodes_dict, edges_list, bounds)
                    # MapDrawer must be prepared to receive edges_list of dicts
                    return nodes_dict, edges_list, bounds
                    
                except Exception as e:
                    logging.error(f"[AssetLoader] Erro ao processar map_topology.json: {e}", exc_info=True)
                    # If it fails, try the fallback below
            
            # --- ATTEMPT 2: Load Legacy XML (SUMO Native) ---
            scenario_name = os.path.basename(latest_scenario_dir)
            map_data_prefix = os.path.join(maps_dir, f"{scenario_name}_map")
            
            logging.info(f"[AssetLoader] Fallback: Procurando por arquivos de mapa XML legado: {map_data_prefix}")
            
            if not os.path.exists(map_data_prefix + ".nod.xml"):
                 logging.warning(f"[AssetLoader] ARQUIVO NÃO ENCONTRADO: {map_data_prefix}.nod.xml")
                 return None

            parsed_data = parse_map_data(map_data_prefix)
            if parsed_data and len(parsed_data) == 3:
                return parsed_data
            else:
                logging.error("[AssetLoader] parse_map_data não retornou os 3 valores esperados.")
                return None

        except Exception as e:
            logging.error(f"[AssetLoader] Falha crítica ao carregar os dados do mapa: {e}", exc_info=True)
            return None