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

# File: src/rendering/precise_heatmap_renderer.py
# Author: Gabriel Moraes
# Date: April 23, 2026

import logging
import io
import base64
from typing import TYPE_CHECKING
import matplotlib.pyplot as plt
import threading
import numpy as np

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class PreciseHeatmapRenderer:
    """Renderizador de mapas de calor com alta precisão para valores de congestão."""

    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """Inicializa o renderizador de mapas de calor preciso."""
        self.locale_manager = locale_manager
        # Cache simples para evitar renderizações desnecessárias
        self._cache = {}
        self._cache_size_limit = 5
        # Lock para proteger o acesso ao cache
        self._cache_lock = threading.Lock()
        
        logging.info(self.locale_manager.get_string("precise_heatmap_renderer.init.created"))

    def create_heatmap_image_in_memory(
        self, 
        map_data: tuple, 
        congestion_data: dict,
        saturation_threshold: float = 100.0
    ) -> str | None:
        """
        Gera uma imagem de mapa com as ruas coloridas pelo nível de
        congestionamento e a retorna como uma string Base64.
        
        Esta versão precisa inclui:
        - Representação precisa dos valores de congestão
        - Escala de cores refinada para melhor distinção
        - Cache de renderizações anteriores
        """
        lm = self.locale_manager
        
        try:
            # Criar chave para cache baseada nos dados de congestão
            cache_key = self._generate_cache_key(congestion_data, saturation_threshold)
            
            # Verificar se já existe no cache
            with self._cache_lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]
            
            nodes, edges = map_data
            
            # Usar figura menor para maior velocidade
            fig, ax = plt.subplots(figsize=(4.0, 2.4), dpi=80)  # Tamanho e DPI reduzidos para velocidade

            cmap = plt.get_cmap('viridis')  # Usar colormap mais preciso

            threshold = max(saturation_threshold, 1.0)

            # Processar todas as arestas para manter consistência
            for edge in edges:
                edge_id = edge.get('id', '')
                
                # Obter valor de congestão com fallback
                congestion_value = congestion_data.get(edge_id, 0.0)
                
                # Converter para dicionário se necessário
                if isinstance(congestion_value, dict):
                    congestion_value = congestion_value.get('congestion', 0.0)
                
                # Calcular cor com alta precisão
                normalized_congestion = min(max(congestion_value / threshold, 0.0), 1.0)
                color = cmap(normalized_congestion)
                
                shape = edge['shape']
                if len(shape) < 2:
                    continue
                    
                x_coords, y_coords = zip(*shape)

                # Reduzir largura e qualidade para maior velocidade
                ax.plot(
                    x_coords, y_coords, 
                    color=color, 
                    linewidth=1.5,  # Linewidth reduzido
                    zorder=1, 
                    solid_capstyle='round',
                    antialiased=False  # Desativar anti-aliasing para velocidade
                )

            # Desenhar nós se existirem, com tamanho reduzido
            if nodes:
                node_x = [n['x'] for n in nodes.values() if 'x' in n and 'y' in n]
                node_y = [n['y'] for n in nodes.values() if 'x' in n and 'y' in n]
                if node_x and node_y:
                    ax.scatter(node_x, node_y, s=5, color='#808080', zorder=2, alpha=0.7)  # Tamanho e opacidade reduzidos

            ax.set_aspect('equal', adjustable='box')
            # Remover eixos para velocidade
            ax.set_xticks([])
            ax.set_yticks([])
            ax.axis('off')
            ax.set_facecolor('#F7F7F7')
            
            buf = io.BytesIO()
            # Salvar com configurações otimizadas para velocidade
            plt.savefig(buf, format='png', dpi=80, facecolor=ax.get_facecolor(),
                       bbox_inches='tight', pad_inches=0.02,
                       edgecolor='none')
            plt.close(fig)
            buf.seek(0)
            
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Armazenar no cache
            with self._cache_lock:
                if len(self._cache) >= self._cache_size_limit:
                    # Remover item mais antigo se cache estiver cheio
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[cache_key] = image_base64
            
            return image_base64

        except Exception as e:
            logging.error(lm.get_string("precise_heatmap_renderer.run.error", error=e), exc_info=True)
            return None

    def _generate_cache_key(self, congestion_data: dict, threshold: float) -> str:
        """Gera uma chave de cache baseada nos dados de congestão."""
        # Criar uma representação mais precisa dos dados para a chave
        sorted_keys = sorted(congestion_data.keys())
        key_parts = [str(congestion_data[k]) for k in sorted_keys[:10]]  # Pegar apenas primeiros 10 para evitar chaves grandes
        key_content = "_".join(key_parts)
        return f"{key_content}_{threshold}"

    def clear_cache(self):
        """Limpa o cache de renderizações."""
        with self._cache_lock:
            self._cache.clear()

    def get_precise_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> str:
        """
        Converte um valor de congestão em uma cor hexadecimal com alta precisão.
        Implementa uma escala de cores similar às usadas por Waze e Google Maps.
        
        Args:
            value: Valor de congestão a ser convertido
            max_expected_value: Valor máximo esperado (para normalização)
            
        Returns:
            String hexadecimal representando a cor apropriada
        """
        # Normaliza o valor entre 0 e 1, considerando o valor máximo esperado
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        
        # Escala de cores usada por serviços como Waze e Google Maps:
        # Verde escuro (tráfego livre) -> Verde -> Amarelo -> Laranja -> Vermelho -> Roxo (congestionamento extremo)
        # Esta é uma escala de 6 pontos para representar com mais precisão os diferentes níveis de tráfego
        
        # Definindo os pontos de controle da escala de cores (0.0 a 1.0)
        # Cada ponto representa um limite entre diferentes estados de tráfego
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
                
                return f"#{r:02x}{g:02x}{b:02x}"
        
        # Caso especial para o último intervalo
        r, g, b = color_stops[-1][1]
        return f"#{r:02x}{g:02x}{b:02x}"

    def get_enhanced_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> str:
        """
        Converte um valor de congestão em uma cor hexadecimal com escala avançada.
        Usa uma curva logarítmica para melhor representação de pequenas variações,
        similar às usadas por Waze e Google Maps.
        
        Args:
            value: Valor de congestão a ser convertido
            max_expected_value: Valor máximo esperado (para normalização)
            
        Returns:
            String hexadecimal representando a cor apropriada
        """
        # Usar transformação logarítmica para dar mais destaque a pequenas variações
        # Isso melhora a percepção de mudanças sutis nos dados
        import math
        
        # Normalizar o valor
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        
        # Aplicar uma transformação logarítmica suavizada para realçar pequenas variações
        # Esta abordagem é usada por muitos sistemas de navegação para destacar mudanças subtis
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
                
                return f"#{r:02x}{g:02x}{b:02x}"
        
        # Caso especial para o último intervalo
        r, g, b = color_stops[-1][1]
        return f"#{r:02x}{g:02x}{b:02x}"
