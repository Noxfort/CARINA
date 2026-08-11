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
    """The specialist in rendering static maps and their associated assets."""

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

    def _draw_map_and_icons_with_matplotlib(self, nodes, edges, bounds, icon_requests, output_path: str):
        lm = self.locale_manager
        # --- REVERSED: Remove fallback ---
        logging.info(lm.get_string("static_map_renderer.run.rendering_map", path=output_path))
        # --- END ---
        # Size set to (12, 8) to perfectly match the 1.5 ratio (1200x800) of Flet's InteractiveMap
        fig, ax = plt.subplots(figsize=(12, 8), dpi=100)

        # Replicate Flet's PlanningMapRenderer coordinate projection
        base_width = 1200
        base_height = 800
        fit_scale = 1.0
        fit_offset_x = 0
        fit_offset_y = 0

        # Calculate real geographical bounds from nodes and edges coordinates
        all_x = [n['x'] for n in nodes.values() if 'x' in n] if nodes else []
        all_y = [n['y'] for n in nodes.values() if 'y' in n] if nodes else []
        if edges:
            for edge in edges:
                shape = edge.get('shape')
                if shape:
                    for pt in shape:
                        all_x.append(pt[0])
                        all_y.append(pt[1])

        if all_x and all_y:
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            
            map_w = max_x - min_x
            map_h = max_y - min_y
            if map_w == 0: map_w = 1
            if map_h == 0: map_h = 1

            scale_x = base_width / map_w
            scale_y = base_height / map_h
            fit_scale = min(scale_x, scale_y) * 0.95

            pixel_map_w = map_w * fit_scale
            pixel_map_h = map_h * fit_scale

            fit_offset_x = (base_width - pixel_map_w) / 2
            fit_offset_y = (base_height - pixel_map_h) / 2
        else:
            min_x, max_x = 0.0, 1200.0
            min_y, max_y = 0.0, 800.0

        def map_to_canvas(mx: float, my: float) -> tuple[float, float]:
            rel_x = mx - min_x
            rel_y = my - min_y
            cx = fit_offset_x + (rel_x * fit_scale)
            cy = fit_offset_y + (rel_y * fit_scale)
            return cx, cy

        # Draw the streets
        for edge in edges:
            shape = edge.get('shape') # Use .get() for security
            if not shape: continue # Skip if shape does not exist
            try:
                projected_shape = [map_to_canvas(pt[0], pt[1]) for pt in shape]
                x_coords, y_coords = zip(*projected_shape)
                # Replicating Flet's street width (4.5) and color (black)
                ax.plot(x_coords, y_coords, color='black', linewidth=4.5, zorder=1)
            except ValueError: # Handle empty or invalid shape cases
                 logging.warning(f"Forma inválida encontrada para aresta: {edge.get('id', 'N/A')}")

        # Draw the nodes (intersections and traffic lights) matching the UI exactly
        from matplotlib.offsetbox import DrawingArea, AnnotationBbox
        import matplotlib.patches as patches

        if nodes:
            for node_id, node in nodes.items():
                if 'x' not in node or 'y' not in node: continue
                cx, cy = map_to_canvas(node['x'], node['y'])
                
                # Resolve recommendation type (rec_type) robustly
                clean_node_id = str(node_id).strip()
                rec_type = "existing"
                if icon_requests:
                    if clean_node_id in icon_requests:
                        rec_type = icon_requests[clean_node_id]
                    elif node_id in icon_requests:
                        rec_type = icon_requests[node_id]
                
                node_type = node.get('type')
                is_traffic_light = False
                if node_type is None or "traffic_light" in str(node_type):
                    is_traffic_light = True
                
                if (is_traffic_light and rec_type != "no_signal") or rec_type == "add":
                    # Draw a vertical 3-light traffic light icon matching the UI (16x42 px)
                    da = DrawingArea(width=16, height=42, xdescent=0, ydescent=0)
                    
                    # Box color matching the UI's box_color
                    if rec_type == "add":
                        box_color = '#388E3C'  # Green_700 (Adicionar)
                    elif rec_type == "remove":
                        box_color = '#D32F2F'  # Red_700 (Remover)
                    else:
                        box_color = '#1565C0'  # Blue_800 (Manter)
                        
                    # Housing box
                    rect = patches.Rectangle((0, 0), 16, 42, facecolor=box_color, edgecolor='none')
                    da.add_artist(rect)
                    
                    # Three light bulbs: Red (top), Amber (middle), Green (bottom)
                    c_red = patches.Circle((8, 33), 4, color='#FF0000')
                    c_amber = patches.Circle((8, 21), 4, color='#FFC107')
                    c_green = patches.Circle((8, 9), 4, color='#4CAF50')
                    
                    da.add_artist(c_red)
                    da.add_artist(c_amber)
                    da.add_artist(c_green)
                    
                    # Force exact center alignment at (cx, cy) via box_alignment=(0.5, 0.5)
                    ab = AnnotationBbox(da, (cx, cy), box_alignment=(0.5, 0.5), frameon=False, pad=0.0, zorder=3)
                    ax.add_artist(ab)
                else:
                    # Draw simple junction matching the UI (Orange circle of radius 6)
                    da = DrawingArea(width=12, height=12, xdescent=0, ydescent=0)
                    circle = patches.Circle((6, 6), 6, color='#FB8C00')
                    da.add_artist(circle)
                    
                    # Force exact center alignment at (cx, cy) via box_alignment=(0.5, 0.5)
                    ab = AnnotationBbox(da, (cx, cy), box_alignment=(0.5, 0.5), frameon=False, pad=0.0, zorder=2)
                    ax.add_artist(ab)

        # Chart style settings and limits aligned to Flet's (1200x800) coordinate spaces
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False); ax.spines['left'].set_visible(False)
        ax.get_xaxis().set_ticks([]); ax.get_yaxis().set_ticks([])
        ax.set_facecolor('#F7F7F7')

        # Standard Matplotlib coordinates space (0 to 1200 on X, 0 to 800 on Y)
        ax.set_xlim(0, 1200)
        ax.set_ylim(0, 800)

        # Eliminate plot padding to occupy 100% of the canvas width/height
        plt.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)

        # Save with DPI=100 (12x8 inches -> exactly 1200x800 px)
        try:
            plt.savefig(output_path, format='png', dpi=100, facecolor=ax.get_facecolor(), bbox_inches=None, pad_inches=0.0)
        except MemoryError as me:
             logging.critical(f"MemoryError ao salvar a imagem '{output_path}'.")
             raise me
        except Exception as save_err:
             logging.error(f"Erro inesperado ao salvar a imagem '{output_path}': {save_err}")
             raise save_err
        finally:
            plt.close(fig)

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

            nodes, edges, bounds = map_data
            if not nodes:
                logging.error("Nenhum nó encontrado nos dados do mapa parseados.")
                return None, None

            final_image_path = os.path.join(maps_output_dir, output_filename)
            self._draw_map_and_icons_with_matplotlib(nodes, edges, bounds, icon_requests, final_image_path)

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
        Delegates the coordinates data file generation to MapCoordinateGenerator.
        """
        from rendering.map_coordinate_generator import MapCoordinateGenerator
        generator = MapCoordinateGenerator(self.locale_manager)
        return generator.generate_coordinates_file(
            map_data=map_data,
            traffic_light_ids=traffic_light_ids,
            scenario_results_dir=scenario_results_dir,
            image_width=image_width,
            image_height=image_height
        )