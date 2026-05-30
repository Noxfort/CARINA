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

# File: ui/handlers/live_data_provider.py (FIXED: Multiple Port Support)
# Author: Gabriel Moraes
# Date: December 17, 2025

"""
Define o LiveDataProvider.

Nesta versão, o cliente WebSocket implementa uma estratégia de 'Port Hunting' (Caça à Porta),
tentando conectar sequencialmente em portas alternativas (8765, 8766, 8767) caso a padrão falhe.
Isso sincroniza a UI com o mecanismo de fallback implementado no servidor.
"""

import logging
import threading
import time
import json
import asyncio
import websockets
from typing import Callable, Dict, Any

class LiveDataProvider:
    """
    Um serviço que se conecta ao back-end via WebSocket para fornecer
    pacotes de dados da simulação em tempo real e enviar comandos.
    """
    
    def __init__(self, on_data_received: Callable[[Dict[str, Any]], None]):
        self.on_data_received = on_data_received
        self._thread = None
        self._is_running = False
        self.loop = None
        
        # List of ports to try to connect to (Sync with websocket_server.py)
        self.target_ports = [8765, 8766, 8767]
        self.current_uri = "" 
        self.websocket_connection = None

    def start(self):
        """Inicia o cliente WebSocket em uma thread separada."""
        if not self._thread or not self._thread.is_alive():
            self._is_running = True
            self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self._thread.start()
            logging.info("[LiveDataProvider] Cliente WebSocket para o back-end iniciado.")

    def stop(self):
        """Para a thread e a conexão WebSocket."""
        self._is_running = False
        if self.websocket_connection and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.websocket_connection.close(), self.loop)
            except Exception:
                pass
        logging.info("[LiveDataProvider] Sinal de parada enviado para o cliente WebSocket.")

    def _run_async_loop(self):
        """Define o loop de eventos para a nova thread e o executa."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._websocket_thread_loop())

    async def _websocket_thread_loop(self):
        """
        O loop principal que gerencia a conexão com rotação de portas.
        """
        port_index = 0
        
        while self._is_running:
            # Select current port based on index
            port = self.target_ports[port_index]
            self.current_uri = f"ws://127.0.0.1:{port}"
            
            try:
                logging.info(f"[LiveDataProvider] Tentando conectar a {self.current_uri}...")
                
                async with websockets.connect(self.current_uri) as websocket:
                    self.websocket_connection = websocket
                    logging.info(f"[LiveDataProvider] Conectado com sucesso ao back-end (SDS) na porta {port}.")
                    
                    # If you connected successfully, we process the messages
                    async for message in websocket:
                        if not self._is_running:
                            break
                        try:
                            data_packet = json.loads(message)
                            if self.on_data_received:
                                self.on_data_received(data_packet)
                        except json.JSONDecodeError:
                            logging.warning("[LiveDataProvider] Mensagem inválida (não-JSON) recebida do back-end.")
            
            except (ConnectionRefusedError, OSError, websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as e:
                # Connection failed: Log warning and prepare to try the next port
                logging.warning(f"[LiveDataProvider] Falha ao conectar em {self.current_uri}: {e}")
                self.websocket_connection = None
                
                # Advances to the next port in the list (Round-Robin)
                port_index = (port_index + 1) % len(self.target_ports)
                
                # Wait a while before the next attempt (quick to find the right door soon)
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logging.error(f"[LiveDataProvider] Erro inesperado no WebSocket: {e}", exc_info=True)
                self.websocket_connection = None
                await asyncio.sleep(5)

    def send_command_to_backend(self, command: dict):
        """
        Envia um comando (dicionário Python) para o back-end de forma segura
        a partir de qualquer thread.
        """
        if self.websocket_connection and self.loop and self.loop.is_running():
            try:
                message_json = json.dumps(command)
                # The send itself is scheduled in the event loop thread
                asyncio.run_coroutine_threadsafe(
                    self.websocket_connection.send(message_json), 
                    self.loop
                )
            except RuntimeError:
                pass # Event loop closed
            except Exception as e:
                # If send() fails (for example, because the connection was closed),
                # we catch the exception here.
                logging.warning(f"[LiveDataProvider] Falha ao enviar comando. A conexão pode estar fechada. Erro: {e}")
        else:
            # logging.warning("[LiveDataProvider] Attempting to send command without an active connection to the backend.")
            pass