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

# File: src/utils/metrics_manager.py
# Author: Gabriel Moraes
# Date: December 17, 2025

"""
Defines the MetricsManager, a reusable component to manage the exposure
of metrics to Prometheus.
"""

import logging
import threading
from prometheus_client import start_http_server, Gauge, Counter

class MetricsManager:
    """
    A toolbox to create, manage and expose Prometheus metrics
    for a specific process.
    """
    def __init__(self, process_name: str, port: int):
        """
        Inicializa o gerenciador de métricas para um processo.

        Args:
            process_name (str): O nome do processo (ex: 'AI_Process', 'SDS_Worker').
                                Será usado como uma label nas métricas.
            port (int): A porta TCP onde o servidor de métricas irá escutar.
        """
        self.process_name = process_name
        self.port = port
        self.metrics = {}
        
        # Start the HTTP server in a daemon thread so as not to block the process
        self.start_server()

    def start_server(self):
        """Starts the Prometheus HTTP server in a separate thread with error handling."""
        def run_server():
            # Try the original port
            try:
                start_http_server(self.port)
                logging.info(f"[{self.process_name}-METRICS] Servidor Prometheus iniciado na porta {self.port}")
                return
            except OSError as e:
                if e.errno == 98: # Address already in use
                    logging.warning(f"[{self.process_name}-METRICS] Porta {self.port} ocupada (processo zumbi?).")
                else:
                    logging.error(f"[{self.process_name}-METRICS] Erro ao iniciar na porta {self.port}: {e}")
            except Exception as e:
                logging.error(f"[{self.process_name}-METRICS] Erro genérico na porta {self.port}: {e}")
            
            # Try an alternative port (Fallback)
            # Add 100 to the original port (ex: 8004 -> 8104) to avoid collision
            fallback_port = self.port + 100
            try:
                logging.info(f"[{self.process_name}-METRICS] Tentando porta alternativa {fallback_port}...")
                start_http_server(fallback_port)
                logging.info(f"[{self.process_name}-METRICS] Servidor Prometheus iniciado na porta {fallback_port} (Fallback)")
                self.port = fallback_port # Updates to reflect reality
            except Exception as e:
                 logging.error(f"[{self.process_name}-METRICS] Não foi possível iniciar o servidor de métricas (Metrics desativado): {e}")

        try:
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
        except Exception as e:
            logging.error(f"[{self.process_name}-METRICS] Falha crítica ao criar thread do servidor: {e}")

    def register_metric(self, name: str, description: str, metric_type: str = 'gauge'):
        """
        Cria e registra uma nova métrica.

        Args:
            name (str): O nome da métrica (ex: 'queue_size').
            description (str): Uma descrição do que a métrica representa.
            metric_type (str): O tipo de métrica ('gauge' ou 'counter').
        """
        if name in self.metrics:
            return

        label_names = ['process_name']
        
        try:
            if metric_type == 'gauge':
                metric = Gauge(name, description, labelnames=label_names)
            elif metric_type == 'counter':
                metric = Counter(name, description, labelnames=label_names)
            else:
                logging.warning(f"[{self.process_name}-METRICS] Tipo de métrica desconhecido: {metric_type}")
                return
            
            self.metrics[name] = metric
            logging.debug(f"[{self.process_name}-METRICS] Métrica '{name}' registrada.")
        except Exception as e:
            # Common error if the metric already exists in the Prometheus Client global registry
            logging.warning(f"[{self.process_name}-METRICS] Métrica '{name}' já registrada ou erro: {e}")

    def update_metric(self, name: str, value: float):
        """
        Atualiza o valor de uma métrica registrada.

        Args:
            name (str): O nome da métrica a ser atualizada.
            value (float): O novo valor para a métrica.
        """
        if name not in self.metrics:
            return

        try:
            metric = self.metrics[name]
            
            # The update method depends on the metric type
            if isinstance(metric, Gauge):
                metric.labels(process_name=self.process_name).set(value)
            elif isinstance(metric, Counter):
                # For counters we usually increment, but 'inc' with value allows flexibility
                metric.labels(process_name=self.process_name).inc(value)
        except Exception:
            # Avoid crashing the main loop if there is an error in the metric
            pass