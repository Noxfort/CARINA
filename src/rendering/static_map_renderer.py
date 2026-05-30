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

# File: src/rendering/static_map_renderer.py (Reduced DPI)
# Author: Gabriel Moraes
# Date: October 23, 2025 # <-- DATE UPDATED

import logging
import os
import sys
import json
from typing import Dict, List, Tuple, TYPE_CHECKING

# --- MAINTAINED: Import resource_path correctly ---
project_root_render = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path_render = os.path.join(project_root_render, 'src')
if src_path_render not in sys.path:
    sys.path.insert(0, src_path_render)

from src.utils.paths import resource_path # Changed to import from src.utils.paths
# --- END ---

# --- REVERSED: Import LocaleManagerBackend ---
if TYPE_CHECKING:
    # The correct import is from the backend, as this file is in 'src'
    from src.utils.locale_manager_backend import LocaleManagerBackend
# --- END ---

# Add the 'src' directory to the path for the import to work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.map_generator import generate_map_data_files
from utils.map_data_parser import parse_map_data
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# --- REMOVED: Comment about matplotlib.use('Agg') ---

class StaticMapRenderer:
    """O especialista em renderizar mapas estáticos e seus ativos associados."""

    # --- REVERSED: Use LocaleManagerBackend ---
    def __init__(self, locale_manager: 'LocaleManagerBackend'):
    # --- END ---
        self.locale_manager = locale_manager

        # --- MAINTAINED: Use resource_path to load icons ---
        self.icon_paths = {
            "existing": resource_path(os.path.join("ui", "assets", "icon_existing.png")),
            "add": resource_path(os.path.join("ui", "assets", "icon_add.png")),
            "remove": resource_path(os.path.join("ui", "assets", "icon_remove.png")),
        }
        # --- END ---
        # --- REVERSED: Remove fallback ---
        logging.info(self.locale_manager.get_string("static_map_renderer.init.created"))
        # --- END ---

    def _draw_map_and_icons_with_matplotlib(self, nodes, edges, icon_requests, output_path: str):
        lm = self.locale_manager
        # --- REVERSED: Remove fallback ---
        logging.info(lm.get_string("static_map_renderer.run.rendering_map", path=output_path))
        # --- END ---
        # --- REVERSED: Original size of the figure ---
        fig, ax = plt.subplots(figsize=(6.4, 3.6))
        # --- END ---

        # Draw the streets
        for edge in edges:
            shape = edge.get('shape') # Use .get() for security
            if not shape: continue # Skip if shape does not exist
            try:
                x_coords, y_coords = zip(*shape)
                ax.plot(x_coords, y_coords, color='black', linewidth=2.0, zorder=1)
            except ValueError: # Handle empty or invalid shape cases
                 logging.warning(f"Forma inválida encontrada para aresta: {edge.get('id', 'N/A')}")


        # Draw the nodes (intersections)
        if nodes:
            node_x = [n['x'] for n in nodes.values() if 'x' in n] # Ensure that x exists
            node_y = [n['y'] for n in nodes.values() if 'y' in n] # Ensure that y exists
            if node_x and node_y: # Only draw if there are coordinates
                ax.scatter(node_x, node_y, s=20, color='#808080', zorder=2)

        # Design recommendation icons
        if icon_requests:
            for junction_id, icon_type in icon_requests.items():
                if junction_id not in nodes: continue

                icon_path = self.icon_paths.get(icon_type)
                # --- REMOVED: Extra check for os.path.exists and try...except ---
                if not icon_path or not os.path.exists(icon_path): # Added existence check here for security
                    logging.warning(f"Ícone '{icon_type}' não encontrado em '{icon_path}'")
                    continue

                node_coords = nodes[junction_id]
                x, y = node_coords.get('x'), node_coords.get('y') # Use .get()
                if x is None or y is None: continue # Skip if x or y does not exist

                try: # Added try-except for reading the image
                    icon_image = plt.imread(icon_path)
                    imagebox = OffsetImage(icon_image, zoom=0.5)
                    ab = AnnotationBbox(imagebox, (x, y), frameon=False, pad=0.0, zorder=3)
                    ax.add_artist(ab)
                except Exception as img_err:
                    logging.error(f"Erro ao carregar ou adicionar ícone '{icon_path}': {img_err}")
                # --- END ---

        # Chart style settings
        ax.set_aspect('equal', adjustable='box')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False); ax.spines['left'].set_visible(False)
        ax.get_xaxis().set_ticks([]); ax.get_yaxis().set_ticks([])
        ax.set_facecolor('#F7F7F7')

        # --- KEY CHANGE HERE: Reduced DPI ---
        # Reduce from 600 to 150 (or 300 if the quality is very low)
        try:
            plt.savefig(output_path, format='png', dpi=150, facecolor=ax.get_facecolor(), pad_inches=0.1)
        except MemoryError as me: # Specifically catches MemoryError
             logging.critical(f"MemoryError ao salvar a imagem '{output_path}'. Tente reduzir ainda mais o DPI ou verificar a RAM disponível.")
             raise me # Re-throws error after logging in
        except Exception as save_err: # Catch other errors
             logging.error(f"Erro inesperado ao salvar a imagem '{output_path}': {save_err}")
             raise save_err # Re-throw the error
        finally:
            plt.close(fig) # Ensures the figure is closed
        # --- END OF CHANGE ---

        # --- REVERSED: Remove fallback ---
        logging.info(lm.get_string("static_map_renderer.run.render_complete", filename=os.path.basename(output_path)))
        # --- END ---

    def create_map_with_icons(
        self, net_file_path: str, scenario_results_dir: str,
        icon_requests: dict, output_filename: str
    ) -> tuple[str | None, tuple | None]:
        """
        Orquestra a criação de um mapa estático com ícones.
        """
        lm = self.locale_manager
        plain_xml_prefix = None # Initializes to the finally block
        nodes = None # Initialize
        edges = None # Initialize
        try:
            maps_output_dir = os.path.join(scenario_results_dir, "maps")
            os.makedirs(maps_output_dir, exist_ok=True) # Create the directory if it doesn't exist

            # --- IMPORTANT FIX: Pass 'lm' to generate_map_data_files ---
            plain_xml_prefix = generate_map_data_files(net_file_path=net_file_path, output_dir=scenario_results_dir, lm=self.locale_manager) # Pass lm
            # --- END CORRECTION ---

            if not plain_xml_prefix:
                logging.error("Falha ao gerar arquivos de dados do mapa. Prefixo plain XML não retornado.")
                return None, None

            map_data = parse_map_data(plain_xml_prefix)
            if not map_data:
                logging.error("Falha ao parsear os dados do mapa a partir dos arquivos XML.")
                return None, None

            nodes, edges, _ = map_data
            if not nodes:
                logging.error("Nenhum nó encontrado nos dados do mapa parseados.")
                return None, None

            final_image_path = os.path.join(maps_output_dir, output_filename)
            self._draw_map_and_icons_with_matplotlib(nodes, edges, icon_requests, final_image_path)

            return final_image_path, (nodes, edges)
        except MemoryError: # Catches MemoryError specifically coming from _draw_map...
            logging.critical("Falha ao gerar mapa devido a erro de memória (RAM). Verifique o log anterior.")
            return None, None
        except Exception as e:
            # --- REVERSED: Remove fallback ---
            logging.error(lm.get_string("static_map_renderer.run.critical_error_icons", error=e), exc_info=True)
            # --- END ---
            return None, None
        finally:
             # Cleaning up temporary XML files, if they were created
             if plain_xml_prefix:
                 try:
                     if os.path.exists(plain_xml_prefix + ".nod.xml"): os.remove(plain_xml_prefix + ".nod.xml")
                     if os.path.exists(plain_xml_prefix + ".edg.xml"): os.remove(plain_xml_prefix + ".edg.xml")
                 except Exception as cleanup_err:
                     logging.warning(f"Erro ao limpar arquivos XML temporários: {cleanup_err}")


    def generate_coordinates_file(
        self, map_data: tuple, traffic_light_ids: list,
        scenario_results_dir: str, image_width: int = 3840, image_height: int = 2160
    ) -> str | None:
        """
        Generates a JSON file with the pixel coordinates of each traffic light on the rendered map.
        """
        lm = self.locale_manager
        try:
            # --- REVERSED: Removal of logs ---
            if not isinstance(map_data, tuple) or len(map_data) != 2:
                 logging.error("Dados do mapa inválidos para gerar coordenadas.")
                 return None
            nodes, edges = map_data
            if not nodes or not edges:
                 logging.error("Nós ou arestas ausentes nos dados do mapa para gerar coordenadas.")
                 return None
            # --- END ---

            # --- REVERSED: Original (approximate) coordinate calculation logic ---
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
                         pass # Ignore invalid shapes

            if not all_x or not all_y:
                 logging.error("Não foi possível extrair coordenadas dos nós/arestas.")
                 return None

            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            map_width = max_x - min_x
            map_height = max_y - min_y
            # --- REVERSED: Remove warning log ---
            if map_width <= 0 or map_height <= 0:
                 logging.warning(f"Dimensões do mapa inválidas calculadas: W={map_width}, H={map_height}. Não é possível gerar coordenadas.")
                 return None
            # --- END ---

            # Use padding_ratio based on original figsize
            padding_ratio = (0.1 * 2) / 6.4 # 0.1 pad_inches on each side, 6.4 figsize width
            padding = image_width * padding_ratio / 2 # Padding in pixels for each side
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
            # Offset X: (full width - map width)/2 - (minimum coordinate * scale)
            offset_x = (image_width - centered_map_width) / 2 - (min_x * scale)

            # Y Offset: (total height - map height)/2 + (MAX coordinate * scale)
            # Sum max_y * scale because the Y origin of the image is at the TOP left,
            # while the Y origin of SUMO/matplotlib is on the left BASE.
            offset_y_canvas_top = (image_height - centered_map_height) / 2 # Empty space above the map
            offset_y = offset_y_canvas_top + (max_y * scale) # Moves the origin to max_y (top of the SUMO map) and adjusts by scale

            coordinates = {}
            for tl_id in traffic_light_ids:
                if tl_id in nodes:
                    node = nodes[tl_id]
                    # Ensures that x and y exist
                    if 'x' in node and 'y' in node:
                        # Apply scale and offset
                        pixel_x = node['x'] * scale + offset_x
                        # Inverts the Y coordinate when applying scale and offset
                        pixel_y = offset_y - (node['y'] * scale)
                        coordinates[tl_id] = {'x': round(pixel_x, 2), 'y': round(pixel_y, 2)}
                    else:
                         logging.warning(f"Nó '{tl_id}' não possui coordenadas 'x' ou 'y'.")
            # --- END OF REVERSED LOGIC ---

            maps_output_dir = os.path.join(scenario_results_dir, "maps")
            os.makedirs(maps_output_dir, exist_ok=True)
            output_path = os.path.join(maps_output_dir, "map_coords.json")

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(coordinates, f, indent=4)

            return output_path
        except Exception as e:
            # --- REVERSED: Remove fallback ---
            logging.error(lm.get_string("static_map_renderer.run.critical_error_coords", error=e), exc_info=True)
            # --- END ---
            return None