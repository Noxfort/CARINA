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

# File: src/rendering/async_heatmap_renderer.py
# Author: Gabriel Moraes
# Date: April 23, 2026

import logging
import io
import base64
from typing import TYPE_CHECKING, Callable, Any
import matplotlib.pyplot as plt
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class AsyncHeatmapRenderer:
    """Asynchronous heatmap renderer to avoid interface freezing."""

    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """Initializes the asynchronous heatmap renderer."""
        self.locale_manager = locale_manager
        self.executor = ThreadPoolExecutor(max_workers=2)  # 2 workers for rendering
        self.render_queue = queue.Queue()
        self.result_cache = {}
        self.cache_size_limit = 10  # Cache limit to avoid excessive memory consumption
        
        logging.info(self.locale_manager.get_string("async_heatmap_renderer.init.created"))

    def create_heatmap_image_in_memory_async(
        self, 
        map_data: tuple, 
        congestion_data: dict,
        saturation_threshold: float = 100.0,
        callback: Callable[[str | None], None] = None
    ):
        """
        Gera uma imagem de mapa com as ruas coloridas pelo nível de
        congestionamento de forma assíncrona e chama o callback com o resultado.
        """
        # Submit task for execution in a separate thread
        future = self.executor.submit(
            self._create_heatmap_internal,
            map_data,
            congestion_data,
            saturation_threshold
        )
        
        # If there is a callback, execute when the task is completed
        if callback:
            def handle_result(future):
                try:
                    result = future.result()
                    callback(result)
                except Exception as e:
                    logging.error(f"Erro no callback do heatmap: {e}")
                    callback(None)
                    
            future.add_done_callback(handle_result)

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

    def _create_heatmap_internal(
        self,
        map_data: tuple,
        congestion_data: dict,
        saturation_threshold: float
    ) -> str | None:
        """
        Método interno que realiza a renderização do heatmap (executado fora da thread UI).
        """
        lm = self.locale_manager
        try:
            nodes, edges = map_data
            # Use smaller figure for higher speed
            fig, ax = plt.subplots(figsize=(4.8, 2.88), dpi=100)  # Reduced size for speed

            threshold = max(saturation_threshold, 1.0)

            for edge in edges:
                edge_id = edge.get('id', '')
                congestion_index = congestion_data.get(edge_id, 0.0)
                
                # Use the new improved function to get more precise colors
                color = self.get_enhanced_color_for_congestion(congestion_index, threshold)
                
                shape = edge['shape']
                x_coords, y_coords = zip(*shape)

                ax.plot(
                    x_coords, y_coords,
                    color=color,
                    linewidth=2.0,  # Reduced linewidth for speed
                    zorder=1,
                    solid_capstyle='round'
                )

            if nodes:
                node_x = [n['x'] for n in nodes.values()]
                node_y = [n['y'] for n in nodes.values()]
                ax.scatter(node_x, node_y, s=10, color='#808080', zorder=2)  # Reduced size for speed

            ax.set_aspect('equal', adjustable='box')
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False); ax.spines['left'].set_visible(False)
            ax.get_xaxis().set_ticks([]); ax.get_yaxis().set_ticks([])
            ax.set_facecolor('#F7F7F7')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, facecolor=ax.get_facecolor(),
                       bbox_inches='tight', pad_inches=0.05)  # Smaller padding for speed
            plt.close(fig)
            buf.seek(0)
            
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return image_base64

        except Exception as e:
            logging.error(lm.get_string("async_heatmap_renderer.run.error", error=e), exc_info=True)
            return None

    def shutdown(self):
        """Encerra o executor e libera recursos."""
        self.executor.shutdown(wait=True)


class UpdateThrottler:
    """Controls the update rate to avoid overload."""
    
    def __init__(self, min_interval: float = 0.2):  # 200ms entre atualizações
        self.min_interval = min_interval
        self.last_update = 0
        self.pending_update = None
        self.lock = threading.Lock()
        
    def request_update(self, data: Any, callback: Callable, force: bool = False):
        """Recebe solicitação de atualização."""
        current_time = time.time()
        self.pending_update = (data, callback)
        
        if force or (current_time - self.last_update) >= self.min_interval:
            self._perform_update()
            
    def _perform_update(self):
        """Realiza a atualização real."""
        if self.pending_update is not None:
            data, callback = self.pending_update
            # Processa a atualização pendente
            callback(data)
            self.pending_update = None
            self.last_update = time.time()


class RenderBufferManager:
    """Buffer manager for smooth rendering."""
    
    def __init__(self, buffer_count: int = 2):
        self.buffers = [None] * buffer_count
        self.current_write_idx = 0
        self.current_read_idx = 1
        self.lock = threading.Lock()
        
    def write_buffer(self, data):
        """Writes data to the write buffer."""
        with self.lock:
            self.buffers[self.current_write_idx] = data
            # Swap read and write indices
            self.current_write_idx, self.current_read_idx = self.current_read_idx, self.current_write_idx
            
    def read_buffer(self):
        """Reads data from the read buffer."""
        with self.lock:
            return self.buffers[self.current_read_idx]