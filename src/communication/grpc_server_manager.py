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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/communication/grpc_server_manager.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import logging
import grpc
from concurrent import futures

class GrpcServerManager:
    """
    Manages the lifecycle of the gRPC server (start, stop, bind).
    """
    def __init__(self, settings, locale_manager, implementation_instance):
        self.settings = settings
        self.locale_manager = locale_manager
        self.implementation_instance = implementation_instance
        self.server = None

    def start(self):
        server_port = self.settings.get('SYNAPSE', 'port', fallback='50051')
        max_workers = self.settings.getint('SYNAPSE', 'max_workers', fallback=10)
        
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        
        try:
            import synapse_hft_pb2_grpc as pb2_grpc
            from communication.hft_server import CarinaHFTImpl
            pb2_grpc.add_HFTLinkServicer_to_server(CarinaHFTImpl(self.implementation_instance), self.server)
        except ImportError:
            logging.critical("[GrpcServerManager] Failed to import generated gRPC modules. Ensure 'proto' folder exists.")
            return

        bind_address = f'[::]:{server_port}'
        self.server.add_insecure_port(bind_address)
        
        logging.info(self.locale_manager.get_string("central_controller.grpc.starting", port=server_port, fallback=f"gRPC Server listening on {bind_address}"))
        self.server.start()

    def stop(self):
        if self.server:
            self.server.stop(0)
