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

from ui.loader.map_asset_loader import MapAssetLoader as StandardMapAssetLoader

class MapAssetLoader(StandardMapAssetLoader):
    """Encontra e carrega arquivos de ativos da simulação mais recente (Handler wrapper)."""
    pass