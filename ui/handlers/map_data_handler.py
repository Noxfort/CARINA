# File: ui/handlers/map_asset_loader.py
# Author: Gabriel Moraes
# Date: September 18, 2025
# FIXED TO HANDLE 3 PARSER RETURN VALUES

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
            
            all_scenarios = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
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
        Encontra e carrega os dados brutos do mapa (nós e arestas) a partir
        dos ficheiros plain XML.
        """
        latest_scenario_dir = self._find_latest_scenario_dir()
        if not latest_scenario_dir:
            logging.debug("[AssetLoader] Diretório de cenário não encontrado para carregar dados do mapa.")
            return None

        try:
            scenario_name = os.path.basename(latest_scenario_dir)
            maps_dir = os.path.join(latest_scenario_dir, "maps")
            map_data_prefix = os.path.join(maps_dir, f"{scenario_name}_map")
            
            if not os.path.exists(map_data_prefix + ".nod.xml"):
                 logging.debug(f"[AssetLoader] Arquivo de nós do mapa não encontrado em: {map_data_prefix}.nod.xml")
                 return None

            # --- CORRECTION APPLIED HERE ---
            # parse_map_data now returns 3 values, and we return them correctly.
            parsed_data = parse_map_data(map_data_prefix)
            if parsed_data and len(parsed_data) == 3:
                return parsed_data
            else:
                logging.error("[AssetLoader] parse_map_data não retornou os 3 valores esperados.")
                return None

        except Exception as e:
            logging.error(f"[AssetLoader] Falha crítica ao carregar os dados do mapa: {e}", exc_info=True)
            return None