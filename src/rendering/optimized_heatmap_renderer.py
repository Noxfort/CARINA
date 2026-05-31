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

# File: src/rendering/optimized_heatmap_renderer.py
# Author: Gabriel Moraes
# Date: April 23, 2026

import logging
import io
import base64
from typing import TYPE_CHECKING
import matplotlib.pyplot as plt
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class OptimizedHeatmapRenderer:
    """The specialist in rendering dynamic heatmaps in memory with performance optimizations."""

    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """Initializes the optimized heatmap renderer."""
        self.locale_manager = locale_manager
        # Executor with only 1 worker to avoid overload on systems with few cores
        self.executor = ThreadPoolExecutor(max_workers=1)
        # Simple cache to avoid unnecessary renders
        self._cache = {}
        self._cache_size_limit = 5
        # Lock to protect cache access
        self._cache_lock = threading.Lock()
        
        logging.info(self.locale_manager.get_string("optimized_heatmap_renderer.init.created"))

    def create_heatmap_image_in_memory(
        self, 
        map_data: tuple, 
        congestion_data: dict,
        saturation_threshold: float = 100.0
    ) -> str | None:
        """
        Gera uma imagem de mapa com as ruas coloridas pelo nível de
        congestionamento e a retorna como uma string Base64.
        
        Esta versão otimizada inclui:
        - Cache de renderizações anteriores
        - Redução da resolução para maior velocidade
        - Simplificação do processo de renderização
        """
        lm = self.locale_manager
        
        try:
            # Create cache key based on congestion data
            cache_key = self._generate_cache_key(congestion_data, saturation_threshold)
            
            # Check if it already exists in cache
            with self._cache_lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]
            
            nodes, edges = map_data
            
            # Use smaller figure for higher speed
            fig, ax = plt.subplots(figsize=(4.0, 2.4), dpi=80)  # Reduced size and DPI for speed

            cmap = plt.get_cmap('viridis')  # Use more precise colormap to represent data

            threshold = max(saturation_threshold, 1.0)

            # Optimization: only process edges with congestion data
            congestion_edges = {k for k in congestion_data.keys()}
            
            for edge in edges:
                edge_id = edge.get('id', '')
                
                # Only process edges with congestion data
                if edge_id not in congestion_edges:
                    continue
                    
                congestion_index = congestion_data.get(edge_id, 0.0)
                
                # Use the new improved function to get more precise colors
                rgb_color = self.get_enhanced_color_for_congestion(congestion_index, threshold)
                color = rgb_color
                
                shape = edge['shape']
                if len(shape) < 2:
                    continue
                    
                x_coords, y_coords = zip(*shape)

                # Reduce width and quality for higher speed
                ax.plot(
                    x_coords, y_coords, 
                    color=color, 
                    linewidth=1.5,  # Linewidth reduzido
                    zorder=1, 
                    solid_capstyle='round',
                    antialiased=False  # Disable anti-aliasing for speed
                )

            # Draw nodes if they exist, with reduced size
            if nodes:
                node_x = [n['x'] for n in nodes.values() if 'x' in n and 'y' in n]
                node_y = [n['y'] for n in nodes.values() if 'x' in n and 'y' in n]
                if node_x and node_y:
                    ax.scatter(node_x, node_y, s=5, color='#808080', zorder=2, alpha=0.7)  # Reduced size and opacity

            ax.set_aspect('equal', adjustable='box')
            # Remove axes for speed
            ax.set_xticks([])
            ax.set_yticks([])
            ax.axis('off')
            ax.set_facecolor('#F7F7F7')
            
            buf = io.BytesIO()
            # Save with optimized settings for speed
            plt.savefig(buf, format='png', dpi=80, facecolor=ax.get_facecolor(),
                       bbox_inches='tight', pad_inches=0.02,
                       edgecolor='none')
            plt.close(fig)
            buf.seek(0)
            
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Store in cache
            with self._cache_lock:
                if len(self._cache) >= self._cache_size_limit:
                    # Remove oldest item if cache is full
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[cache_key] = image_base64
            
            return image_base64

        except Exception as e:
            # --- CHANGE 4 ---
            logging.error(lm.get_string("optimized_heatmap_renderer.run.error", error=e), exc_info=True)
            return None

    def _generate_cache_key(self, congestion_data: dict, threshold: float) -> str:
        """Generates a cache key based on congestion data."""
        # Create a simplified representation of the data for the key
        total_congestion = sum(congestion_data.values()) if congestion_data else 0
        edge_count = len(congestion_data)
        return f"{total_congestion:.2f}_{edge_count}_{threshold}"

    def get_precise_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> tuple:
        """
        Converte um valor de congestão em uma tupla RGB com alta precisão.
        Implementa uma escala de cores similar às usadas por Waze e Google Maps.
        
        Args:
            value: Valor de congestão a ser convertido
            max_expected_value: Valor máximo esperado (para normalização)
            
        Returns:
            Tupla RGB representando a cor apropriada
        """
        # Normalize the value between 0 and 1, considering the maximum expected value
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        
        # Color scale used by services like Waze and Google Maps:
        # Verde escuro (tráfego livre) -> Verde -> Amarelo -> Laranja -> Vermelho -> Roxo (congestionamento extremo)
        color_stops = [
            (0.0, (0, 100, 0)),      # Verde escuro - tráfego livre
            (0.25, (0, 255, 0)),     # Verde - tráfego leve
            (0.5, (255, 255, 0)),    # Amarelo - tráfego moderado
            (0.7, (255, 165, 0)),    # Laranja - tráfego pesado
            (0.85, (255, 69, 0)),    # Laranja vermelho - tráfego muito pesado
            (1.0, (255, 0, 0))       # Vermelho - congestionamento severo
        ]
        
        # Find between which control points the normalized value is
        for i in range(len(color_stops) - 1):
            if normalized >= color_stops[i][0] and normalized <= color_stops[i+1][0]:
                # Calculate the fraction between the two control points
                start_value, start_color = color_stops[i]
                end_value, end_color = color_stops[i+1]
                
                # Normalize again between the two control points
                segment_normalized = (normalized - start_value) / (end_value - start_value)
                
                # Linearly interpolate between the two colors
                r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)
                
                return (r/255.0, g/255.0, b/255.0)  # Returns normalized values for matplotlib
        
        # Special case for the last interval
        r, g, b = color_stops[-1][1]
        return (r/255.0, g/255.0, b/255.0)

    def get_enhanced_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> tuple:
        """
        Converte um valor de congestão em uma tupla RGB com escala avançada.
        Usa uma curva logarítmica para melhor representação de pequenas variações.
        
        Args:
            value: Valor de congestão a ser convertido
            max_expected_value: Valor máximo esperado (para normalização)
            
        Returns:
            Tupla RGB representando a cor apropriada
        """
        import math
        
        # Normalizar o valor
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        
        # Apply a smoothed logarithmic transformation to highlight small variations
        if normalized == 0:
            adjusted = 0
        else:
            # Use a combination of functions to highlight variations in different ranges
            if normalized < 0.3:
                # Increase sensitivity for low values
                adjusted = math.pow(normalized / 0.3, 0.7) * 0.3
            elif normalized < 0.7:
                # Maintain average linearity for intermediate range
                adjusted = 0.3 + ((normalized - 0.3) / 0.4) * 0.4
            else:
                # Adjust to highlight high values
                adjusted = 0.7 + math.pow((normalized - 0.7) / 0.3, 1.3) * 0.3
        
        # Now use the standardized color scale
        color_stops = [
            (0.0, (0, 100, 0)),      # Verde escuro - tráfego livre
            (0.25, (0, 255, 0)),     # Verde - tráfego leve
            (0.5, (255, 255, 0)),    # Amarelo - tráfego moderado
            (0.7, (255, 165, 0)),    # Laranja - tráfego pesado
            (0.85, (255, 69, 0)),    # Laranja vermelho - tráfego muito pesado
            (1.0, (255, 0, 0))       # Vermelho - congestionamento severo
        ]
        
        # Find between which control points the adjusted value is
        for i in range(len(color_stops) - 1):
            if adjusted >= color_stops[i][0] and adjusted <= color_stops[i+1][0]:
                # Calculate the fraction between the two control points
                start_value, start_color = color_stops[i]
                end_value, end_color = color_stops[i+1]
                
                # Normalize again between the two control points
                segment_normalized = (adjusted - start_value) / (end_value - start_value)
                
                # Linearly interpolate between the two colors
                r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)
                
                return (r/255.0, g/255.0, b/255.0)  # Returns normalized values for matplotlib
        
        # Special case for the last interval
        r, g, b = color_stops[-1][1]
        return (r/255.0, g/255.0, b/255.0)

    def clear_cache(self):
        """Clears the render cache."""
        with self._cache_lock:
            self._cache.clear()

    def shutdown(self):
        """Encerra o executor e libera recursos."""
        self.executor.shutdown(wait=True)