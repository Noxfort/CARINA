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
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Summary

class MetricsManager:
    """
    A toolbox to create, manage and expose Prometheus metrics
    for a specific process.
    """
    def __init__(self, process_name: str, port: int, locale_manager=None):
        """
        Inicializa o gerenciador de métricas para um processo.

        Args:
            process_name (str): O nome do processo (ex: 'AI_Process', 'SDS_Worker').
                                Será usado como uma label nas métricas.
            port (int): A porta TCP onde o servidor de métricas irá escutar.
            locale_manager: Instância opcional de LocaleManagerBackend.
        """
        self.process_name = process_name
        self.port = port
        self.locale_manager = locale_manager
        self.metrics = {}
        
        # Start the HTTP server in a daemon thread so as not to block the process
        self.start_server()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def start_server(self):
        """Starts the Prometheus HTTP server in a separate thread with error handling."""
        def run_server():
            max_attempts = 5
            last_error = None
            for attempt in range(max_attempts):
                port_to_try = self.port if attempt == 0 else self.port + (attempt * 100)
                try:
                    if attempt > 0:
                        logging.info(self._get_string("metrics_manager.trying_fallback", default="[{process}-METRICS] Trying alternative port {port}...", process=self.process_name, port=port_to_try))
                    start_http_server(port_to_try)
                    if attempt == 0:
                        logging.info(self._get_string("metrics_manager.server_started", default="[{process}-METRICS] Prometheus server started on port {port}", process=self.process_name, port=port_to_try))
                    else:
                        logging.info(self._get_string("metrics_manager.fallback_started", default="[{process}-METRICS] Prometheus server started on port {port} (Fallback)", process=self.process_name, port=port_to_try))
                    self.port = port_to_try  # Updates to reflect reality
                    return
                except OSError as e:
                    last_error = e
                    if e.errno == 98:  # Address already in use
                        logging.warning(self._get_string("metrics_manager.port_in_use", default="[{process}-METRICS] Port {port} in use (zombie process?).", process=self.process_name, port=port_to_try))
                    else:
                        logging.error(self._get_string("metrics_manager.port_error", default="[{process}-METRICS] Error starting on port {port}: {error}", process=self.process_name, port=port_to_try, error=e))
                except Exception as e:
                    last_error = e
                    logging.error(self._get_string("metrics_manager.generic_error", default="[{process}-METRICS] Generic error on port {port}: {error}", process=self.process_name, port=port_to_try, error=e))

            logging.error(self._get_string("metrics_manager.server_disabled", default="[{process}-METRICS] Unable to start metrics server (Metrics disabled): {error}", process=self.process_name, error=last_error))

        try:
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
        except Exception as e:
            logging.error(self._get_string("metrics_manager.thread_critical_error", default="[{process}-METRICS] Critical failure creating server thread: {error}", process=self.process_name, error=e))

    def register_metric(self, name: str, description: str, metric_type: str = 'gauge', buckets: list = None):
        """
        Cria e registra uma nova métrica.

        Args:
            name (str): O nome da métrica (ex: 'queue_size').
            description (str): Uma descrição do que a métrica representa.
            metric_type (str): O tipo de métrica ('gauge', 'counter', 'histogram' ou 'summary').
            buckets (list): Lista opcional de limites de buckets para Histogram.
        """
        if name in self.metrics:
            return

        label_names = ['process_name']
        
        try:
            if metric_type == 'gauge':
                metric = Gauge(name, description, labelnames=label_names)
            elif metric_type == 'counter':
                metric = Counter(name, description, labelnames=label_names)
            elif metric_type == 'histogram':
                kwargs = {'labelnames': label_names}
                if buckets:
                    kwargs['buckets'] = buckets
                metric = Histogram(name, description, **kwargs)
            elif metric_type == 'summary':
                metric = Summary(name, description, labelnames=label_names)
            else:
                logging.warning(self._get_string("metrics_manager.unknown_type", default="[{process}-METRICS] Unknown metric type: {type}", process=self.process_name, type=metric_type))
                return
            
            self.metrics[name] = metric
            logging.debug(self._get_string("metrics_manager.registered", default="[{process}-METRICS] Metric '{name}' registered.", process=self.process_name, name=name))
        except Exception as e:
            # Common error if the metric already exists in the Prometheus Client global registry
            logging.warning(self._get_string("metrics_manager.already_registered", default="[{process}-METRICS] Metric '{name}' already registered or error: {error}", process=self.process_name, name=name, error=e))

    def update_metric(self, name: str, value: float):
        """
        Atualiza o valor de uma métrica registrada.

        Args:
            name (str): O nome da métrica a ser atualizada.
            value (float): O novo valor para a métrica ou observação.
        """
        if name not in self.metrics:
            return

        try:
            metric = self.metrics[name]
            
            # The update method depends on the metric type
            if isinstance(metric, Gauge):
                metric.labels(process_name=self.process_name).set(value)
            elif isinstance(metric, Counter):
                metric.labels(process_name=self.process_name).inc(value)
            elif isinstance(metric, (Histogram, Summary)):
                metric.labels(process_name=self.process_name).observe(value)
        except Exception:
            # Avoid crashing the main loop if there is an error in the metric
            pass