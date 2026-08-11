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

# File: src/rendering/map_coordinate_generator.py
# Author: Gabriel Moraes
# Date: July 20, 2026

import os
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend

class MapCoordinateGenerator:
    """Specialist responsible for generating standard pixel coordinates JSON for traffic light nodes."""

    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        self.locale_manager = locale_manager

    def generate_coordinates_file(
        self, map_data: tuple, traffic_light_ids: list,
        scenario_results_dir: str, image_width: int = 3840, image_height: int = 2160
    ) -> str | None:
        lm = self.locale_manager
        try:
            if not isinstance(map_data, tuple) or len(map_data) != 2:
                 logging.error("Dados do mapa inválidos para gerar coordenadas.")
                 return None
            nodes, edges = map_data
            if not nodes or not edges:
                 logging.error("Nós ou arestas ausentes nos dados do mapa para gerar coordenadas.")
                 return None

            # Collects all x and y coordinates to find the limits
            all_x = [n['x'] for n in nodes.values() if 'x' in n]
            all_y = [n['y'] for n in nodes.values() if 'y' in n]
            for e in edges:
                if 'shape' in e and e['shape']:
                    try:
                        x_coords, y_coords = zip(*e['shape'])
                        all_x.extend(x_coords)
                        all_y.extend(y_coords)
                    except ValueError:
                         pass

            if not all_x or not all_y:
                 logging.error("Não foi possível extrair coordenadas dos nós/arestas.")
                 return None

            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            map_width = max_x - min_x
            map_height = max_y - min_y
            if map_width <= 0 or map_height <= 0:
                 logging.warning(f"Dimensões do mapa inválidas calculadas: W={map_width}, H={map_height}. Não é possível gerar coordenadas.")
                 return None

            padding_ratio = (0.1 * 2) / 9.6
            padding = image_width * padding_ratio / 2
            view_width = image_width - (padding * 2)
            view_height = image_height - (padding * 2)

            # Calculates scale ensuring the map fits in the viewing area
            scale_x = view_width / map_width if map_width > 0 else 1
            scale_y = view_height / map_height if map_height > 0 else 1
            scale = min(scale_x, scale_y)

            # Calculates the width and height of the scaled map
            centered_map_width = map_width * scale
            centered_map_height = map_height * scale

            # Calculates offsets to center the map in the image
            offset_x = (image_width - centered_map_width) / 2 - (min_x * scale)
            offset_y_canvas_top = (image_height - centered_map_height) / 2
            offset_y = offset_y_canvas_top + (max_y * scale)

            coordinates = {}
            for tl_id in traffic_light_ids:
                if tl_id in nodes:
                    node = nodes[tl_id]
                    if 'x' in node and 'y' in node:
                        pixel_x = node['x'] * scale + offset_x
                        pixel_y = offset_y - (node['y'] * scale)
                        coordinates[tl_id] = {'x': round(pixel_x, 2), 'y': round(pixel_y, 2)}
                    else:
                         logging.warning(f"Nó '{tl_id}' não possui coordenadas 'x' ou 'y'.")

            maps_output_dir = os.path.join(scenario_results_dir, "maps")
            os.makedirs(maps_output_dir, exist_ok=True)
            output_path = os.path.join(maps_output_dir, "map_coords.json")

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(coordinates, f, indent=4)

            return output_path
        except Exception as e:
            logging.error(lm.get_string("static_map_renderer.run.critical_error_coords", error=e), exc_info=True)
            return None
