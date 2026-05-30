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

# File: src/sds/dashboard_orchestrator.py (MODIFIED FOR TRANSLATION)
# Author: Gabriel Moraes
# Date: October 2, 2025

import logging
import threading
from multiprocessing import Queue
import configparser
import sys
import os
from typing import TYPE_CHECKING

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from sds.data_processor import DataProcessor
from sds.websocket_server import WebSocketServer

class Orchestrator:
    """O maestro que gerencia o fluxo de trabalho do serviço SDS."""

    def __init__(self, sds_data_queue: Queue, settings: configparser.ConfigParser, 
                 ui_command_queue: Queue, locale_manager: 'LocaleManagerBackend'):
        """
        Inicializa o orquestrador e seus componentes especialistas.
        """
        self.data_queue = sds_data_queue
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        # --- CHANGE: Pass the translator to the experts ---
        self.processor = DataProcessor(settings, lm)
        self.ws_server = WebSocketServer(ui_command_queue=ui_command_queue, locale_manager=lm)
        
        logging.info(lm.get_string("sds_orchestrator.init.orchestrator_created"))

    def run(self):
        """
        Inicia os serviços e entra no loop principal de processamento de dados.
        """
        lm = self.locale_manager
        try:
            ws_thread = threading.Thread(target=self.ws_server.start, daemon=True)
            ws_thread.start()
            logging.info(lm.get_string("sds_orchestrator.run.ws_thread_started"))

            logging.info(lm.get_string("sds_orchestrator.run.main_loop_start"))
            while True:
                raw_sim_data = self.data_queue.get()

                if raw_sim_data is None:
                    break

                ui_data_package = self.processor.process_for_ui(raw_sim_data)

                if ui_data_package:
                    self.ws_server.broadcast(ui_data_package)

        except KeyboardInterrupt:
            logging.info(lm.get_string("sds_orchestrator.run.interrupt_received"))
        except Exception as e:
            logging.error(lm.get_string("sds_orchestrator.run.fatal_error", error=e), exc_info=True)
        finally:
            logging.info(lm.get_string("sds_orchestrator.run.orchestrator_finished"))