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

    def _has_map_files(self, folder_path: str) -> bool:
        """Verifica se um diretório (ou sua subpasta maps) possui arquivos de mapa suportados."""
        if not os.path.exists(folder_path):
            return False
        candidates = [folder_path]
        maps_sub = os.path.join(folder_path, "maps")
        if os.path.exists(maps_sub):
            candidates.insert(0, maps_sub)
            
        for cand in candidates:
            try:
                for f in os.listdir(cand):
                    if f == "map_topology.json" or f.endswith(".net.xml.gz") or f.endswith(".net.xml") or f.endswith(".nod.xml"):
                        return True
            except Exception:
                continue
        return False

    def _find_latest_scenario_dir(self) -> str | None:
        """Retorna exclusivamente o caminho para a sessão hft_live_session."""
        try:
            from src.utils.paths import get_base_output_dir
            hft_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session")
            if not os.path.exists(hft_dir):
                os.makedirs(hft_dir, exist_ok=True)
            return hft_dir
        except Exception as e:
            logging.error(f"[AssetLoader] Erro ao obter diretório hft_live_session: {e}")
            return None

    def get_asset_path(self, asset_type: str, asset_filename: str) -> str | None:
        """
        Constrói o caminho para um ativo específico exclusivamente na sessão hft_live_session.
        """
        scenario_dir = self._find_latest_scenario_dir()
        if scenario_dir:
            asset_path = os.path.join(scenario_dir, asset_type, asset_filename)
            if os.path.exists(asset_path):
                return asset_path
            direct_path = os.path.join(scenario_dir, asset_filename)
            if os.path.exists(direct_path):
                return direct_path
        return None

    def load_coordinates(self) -> Dict[str, Any] | None:
        """
        Encontra e carrega o conteúdo do arquivo de coordenadas da hft_live_session.
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
        Carrega os dados do mapa exclusivamente do diretório hft_live_session.
        Prioriza 'map_topology.json' e converte arquivos SUMO (.net.xml.gz / .net.xml) dinamicamente se necessário.
        """
        scenario_dir = self._find_latest_scenario_dir()
        if not scenario_dir:
            logging.error("[AssetLoader] Diretório hft_live_session não encontrado.")
            return None

        res = self._try_load_from_scenario_dir(scenario_dir)
        if res:
            return res

        logging.error("[AssetLoader] Falha ao encontrar mapa válido em hft_live_session (.net.xml.gz, .net.xml ou map_topology.json).")
        return None

    def _try_load_from_scenario_dir(self, scenario_dir: str) -> Tuple[Dict, Any, Dict] | None:
        try:
            maps_dir = os.path.join(scenario_dir, "maps")
            target_dir = maps_dir if os.path.exists(maps_dir) else scenario_dir
            
            # --- ATTEMPT 1: Load Topology JSON ---
            json_topology_path = os.path.join(target_dir, "map_topology.json")
            if os.path.exists(json_topology_path):
                logging.info(f"[AssetLoader] Carregando topologia vetorial moderna: {json_topology_path}")
                try:
                    with open(json_topology_path, 'r', encoding='utf-8') as f:
                        topology = json.load(f)
                    nodes_list = topology.get("nodes", [])
                    edges_list = topology.get("edges", [])
                    bounds = topology.get("bounds", {})
                    nodes_dict = {node["id"]: node for node in nodes_list}
                    return nodes_dict, edges_list, bounds
                except Exception as e:
                    logging.error(f"[AssetLoader] Erro ao processar map_topology.json: {e}", exc_info=True)

            # --- ATTEMPT 2: Load SUMO Network Map (*.net.xml.gz / *.net.xml) ---
            net_file_path = None
            if os.path.exists(target_dir):
                gz_candidates = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(".net.xml.gz")]
                xml_candidates = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(".net.xml")]
                if gz_candidates:
                    net_file_path = gz_candidates[0]
                elif xml_candidates:
                    net_file_path = xml_candidates[0]
            
            if net_file_path:
                logging.info(f"[AssetLoader] Mapa SUMO encontrado ({os.path.basename(net_file_path)}): {net_file_path}. Extraindo topologia JSON...")
                from src.utils.map_processor import MapProcessor
                try:
                    MapProcessor.extract_topology_to_json(net_file_path, json_topology_path)
                    if os.path.exists(json_topology_path):
                        with open(json_topology_path, 'r', encoding='utf-8') as f:
                            topology = json.load(f)
                        nodes_list = topology.get("nodes", [])
                        edges_list = topology.get("edges", [])
                        bounds = topology.get("bounds", {})
                        nodes_dict = {node["id"]: node for node in nodes_list}
                        return nodes_dict, edges_list, bounds
                except Exception as e:
                    logging.error(f"[AssetLoader] Erro ao extrair topologia de {net_file_path}: {e}", exc_info=True)

            # --- ATTEMPT 3: Load Legacy Plain XML (.nod.xml) ---
            scenario_name = os.path.basename(scenario_dir)
            map_data_prefix = os.path.join(target_dir, f"{scenario_name}_map")
            if os.path.exists(map_data_prefix + ".nod.xml"):
                logging.info(f"[AssetLoader] Carregando arquivos XML legado: {map_data_prefix}")
                parsed_data = parse_map_data(map_data_prefix)
                if parsed_data and len(parsed_data) == 3:
                    return parsed_data

        except Exception as e:
            logging.error(f"[AssetLoader] Erro ao tentar carregar mapa de {scenario_dir}: {e}", exc_info=True)
            
        return None

    def load_background_map(self) -> tuple[str, dict] | None:
        """
        Encontra e carrega a imagem de fundo do mapa (Base64) e as suas coordenadas.
        """
        bg_json_path = self.get_asset_path("maps", "map_background.json")
        bg_png_path = self.get_asset_path("maps", "map_background.png")
        if not bg_json_path or not bg_png_path:
            logging.debug("[AssetLoader] Arquivos de imagem de fundo ou coordenadas não encontrados.")
            return None
        
        try:
            import base64
            with open(bg_json_path, "r", encoding="utf-8") as f:
                bg_data = json.load(f)
            with open(bg_png_path, "rb") as f:
                b64_string = base64.b64encode(f.read()).decode("utf-8")
            return b64_string, bg_data
        except Exception as e:
            logging.error(f"[AssetLoader] Falha ao carregar mapa de fundo: {e}", exc_info=True)
            return None