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
    """Renderizador assíncrono de mapas de calor para evitar congelamento da interface."""

    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """Inicializa o renderizador assíncrono de mapas de calor."""
        self.locale_manager = locale_manager
        self.executor = ThreadPoolExecutor(max_workers=2)  # 2 workers para renderização
        self.render_queue = queue.Queue()
        self.result_cache = {}
        self.cache_size_limit = 10  # Limite de cache para evitar consumo excessivo de memória
        
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
        # Submeter a tarefa para execução em thread separada
        future = self.executor.submit(
            self._create_heatmap_internal,
            map_data,
            congestion_data,
            saturation_threshold
        )
        
        # Se houver callback, executar quando a tarefa for concluída
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
        # Normaliza o valor entre 0 e 1, considerando o valor máximo esperado
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        
        # Escala de cores usada por serviços como Waze e Google Maps:
        # Verde escuro (tráfego livre) -> Verde -> Amarelo -> Laranja -> Vermelho -> Roxo (congestionamento extremo)
        color_stops = [
            (0.0, (0, 100, 0)),      # Verde escuro - tráfego livre
            (0.25, (0, 255, 0)),     # Verde - tráfego leve
            (0.5, (255, 255, 0)),    # Amarelo - tráfego moderado
            (0.7, (255, 165, 0)),    # Laranja - tráfego pesado
            (0.85, (255, 69, 0)),    # Laranja vermelho - tráfego muito pesado
            (1.0, (255, 0, 0))       # Vermelho - congestionamento severo
        ]
        
        # Encontrar entre quais pontos de controle o valor normalizado está
        for i in range(len(color_stops) - 1):
            if normalized >= color_stops[i][0] and normalized <= color_stops[i+1][0]:
                # Calcular a fração entre os dois pontos de controle
                start_value, start_color = color_stops[i]
                end_value, end_color = color_stops[i+1]
                
                # Normalizar novamente entre os dois pontos de controle
                segment_normalized = (normalized - start_value) / (end_value - start_value)
                
                # Interpolar linearmente entre as duas cores
                r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)
                
                return (r/255.0, g/255.0, b/255.0)  # Retorna valores normalizados para matplotlib
        
        # Caso especial para o último intervalo
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
        
        # Aplicar uma transformação logarítmica suavizada para realçar pequenas variações
        if normalized == 0:
            adjusted = 0
        else:
            # Usar uma combinação de funções para realçar variações em diferentes faixas
            if normalized < 0.3:
                # Aumentar sensibilidade para valores baixos
                adjusted = math.pow(normalized / 0.3, 0.7) * 0.3
            elif normalized < 0.7:
                # Manter linearidade média para a faixa intermediária
                adjusted = 0.3 + ((normalized - 0.3) / 0.4) * 0.4
            else:
                # Ajustar para destacar altos valores
                adjusted = 0.7 + math.pow((normalized - 0.7) / 0.3, 1.3) * 0.3
        
        # Agora usar a escala de cores padronizada
        color_stops = [
            (0.0, (0, 100, 0)),      # Verde escuro - tráfego livre
            (0.25, (0, 255, 0)),     # Verde - tráfego leve
            (0.5, (255, 255, 0)),    # Amarelo - tráfego moderado
            (0.7, (255, 165, 0)),    # Laranja - tráfego pesado
            (0.85, (255, 69, 0)),    # Laranja vermelho - tráfego muito pesado
            (1.0, (255, 0, 0))       # Vermelho - congestionamento severo
        ]
        
        # Encontrar entre quais pontos de controle o valor ajustado está
        for i in range(len(color_stops) - 1):
            if adjusted >= color_stops[i][0] and adjusted <= color_stops[i+1][0]:
                # Calcular a fração entre os dois pontos de controle
                start_value, start_color = color_stops[i]
                end_value, end_color = color_stops[i+1]
                
                # Normalizar novamente entre os dois pontos de controle
                segment_normalized = (adjusted - start_value) / (end_value - start_value)
                
                # Interpolar linearmente entre as duas cores
                r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)
                
                return (r/255.0, g/255.0, b/255.0)  # Retorna valores normalizados para matplotlib
        
        # Caso especial para o último intervalo
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
            # Usar figura menor para maior velocidade
            fig, ax = plt.subplots(figsize=(4.8, 2.88), dpi=100)  # Tamanho reduzido para velocidade

            threshold = max(saturation_threshold, 1.0)

            for edge in edges:
                edge_id = edge.get('id', '')
                congestion_index = congestion_data.get(edge_id, 0.0)
                
                # Usar a nova função aprimorada para obter cores mais precisas
                color = self.get_enhanced_color_for_congestion(congestion_index, threshold)
                
                shape = edge['shape']
                x_coords, y_coords = zip(*shape)

                ax.plot(
                    x_coords, y_coords,
                    color=color,
                    linewidth=2.0,  # Linewidth reduzido para velocidade
                    zorder=1,
                    solid_capstyle='round'
                )

            if nodes:
                node_x = [n['x'] for n in nodes.values()]
                node_y = [n['y'] for n in nodes.values()]
                ax.scatter(node_x, node_y, s=10, color='#808080', zorder=2)  # Tamanho reduzido para velocidade

            ax.set_aspect('equal', adjustable='box')
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False); ax.spines['left'].set_visible(False)
            ax.get_xaxis().set_ticks([]); ax.get_yaxis().set_ticks([])
            ax.set_facecolor('#F7F7F7')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, facecolor=ax.get_facecolor(),
                       bbox_inches='tight', pad_inches=0.05)  # Menor padding para velocidade
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
    """Controla a taxa de atualizações para evitar sobrecarga."""
    
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
    """Gerenciador de buffers para renderização suave."""
    
    def __init__(self, buffer_count: int = 2):
        self.buffers = [None] * buffer_count
        self.current_write_idx = 0
        self.current_read_idx = 1
        self.lock = threading.Lock()
        
    def write_buffer(self, data):
        """Escreve dados no buffer de escrita."""
        with self.lock:
            self.buffers[self.current_write_idx] = data
            # Troca os índices de leitura e escrita
            self.current_write_idx, self.current_read_idx = self.current_read_idx, self.current_write_idx
            
    def read_buffer(self):
        """Lê dados do buffer de leitura."""
        with self.lock:
            return self.buffers[self.current_read_idx]