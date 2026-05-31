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

# File: src/sds/websocket_server.py (FIXED: Port Robustness)
# Author: Gabriel Moraes
# Date: December 17, 2025

import asyncio
import websockets
import json
import logging
import threading
from multiprocessing import Queue
from queue import Full
import sys
import os
from typing import TYPE_CHECKING, Dict, Any, Optional, Set

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class WebSocketServer:
    """Manages the WebSocket server, data transmission, and command reception."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, 
                 ui_command_queue: Optional[Queue] = None, locale_manager: Optional['LocaleManagerBackend'] = None) -> None:
        self.host = host
        self.port = port
        self.clients = set()
        self.loop = None
        self.thread = None
        self.ui_command_queue = ui_command_queue
        self.locale_manager = locale_manager
        
        self.cached_initial_geometry_packet: str | None = None

    async def _register(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Registers a newly connected client and sends the initialization packet if available."""
        logging.info(self.locale_manager.get_string("sds_websocket.register.client_connected", address=websocket.remote_address))
        self.clients.add(websocket)
        
        if self.cached_initial_geometry_packet:
            logging.info(self.locale_manager.get_string("sds_websocket.register.sending_cache", default="[WS_SERVER] Sending cached geometry packet to new client: {address}", address=websocket.remote_address))
            try:
                await websocket.send(self.cached_initial_geometry_packet)
            except Exception as e:
                logging.error(self.locale_manager.get_string("sds_websocket.register.error_cache", default="[WS_SERVER] Error sending cache to new client: {error}", error=e))

    async def _unregister(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Removes a disconnected client."""
        if websocket in self.clients:
            logging.info(self.locale_manager.get_string("sds_websocket.unregister.client_disconnected", address=websocket.remote_address))
            self.clients.remove(websocket)

    async def _handler(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Manages the lifecycle of a client connection, including message reception."""
        lm = self.locale_manager
        await self._register(websocket)
        try:
            async for message in websocket:
                if self.ui_command_queue:
                    try:
                        command = json.loads(message)
                        logging.info(lm.get_string("sds_websocket.handler.command_received", command=command))
                        self.ui_command_queue.put(command)
                    except json.JSONDecodeError:
                        logging.warning(lm.get_string("sds_websocket.handler.invalid_json", address=websocket.remote_address))
                    except Full:
                        logging.warning(lm.get_string("sds_websocket.handler.queue_full"))
        except websockets.exceptions.ConnectionClosed:
            pass 
        finally:
            await self._unregister(websocket)

    def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Sends a message to all connected clients.
        """
        if not self.loop:
            return

        if message.get("type") == "initial_map_geometry":
            logging.info(self.locale_manager.get_string("sds_websocket.broadcast.cache_saved", default="[WS_SERVER] 'initial_map_geometry' packet received and cached."))
            self.cached_initial_geometry_packet = json.dumps(message)
        
        if not self.clients:
            return

        message_json = json.dumps(message)
        
        asyncio.run_coroutine_threadsafe(
            self._broadcast_async(message_json), 
            self.loop
        )

    async def _broadcast_async(self, message_json: str) -> None:
        """The coroutine that effectively sends the message."""
        if not self.clients:
            return
            
        clients_to_send = list(self.clients)
        tasks = [client.send(message_json) for client in clients_to_send]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, (websockets.exceptions.ConnectionClosed, ConnectionResetError)):
                await self._unregister(clients_to_send[i])


    async def _main_loop(self) -> None:
        """The main loop that runs the server with port fallback attempt."""
        ports_to_try = [self.port, self.port + 1, self.port + 2]
        server = None
        
        for port in ports_to_try:
            try:
                # Try starting the server on the current port
                server = await websockets.serve(
                    self._handler, 
                    self.host, 
                    port, 
                    ping_interval=20, 
                    ping_timeout=20
                )
                self.port = port # Update if changed
                logging.info(self.locale_manager.get_string("sds_websocket.main_loop.server_started", host=self.host, port=self.port))
                break
            except OSError as e:
                if e.errno == 98: # Address already in use
                    logging.warning(self.locale_manager.get_string("sds_websocket.main_loop.port_busy", default="[WS_SERVER] Port {port} is busy. Trying next...", port=port))
                else:
                    raise e
        
        if server is None:
            logging.critical(self.locale_manager.get_string("sds_websocket.main_loop.fatal_error", default="[WS_SERVER] Fatal failure: Could not bind WebSocket to any of the ports: {ports}", ports=ports_to_try))
            return

        # Keeps the server running until the loop stops
        async with server:
            await asyncio.Future()

    def start(self) -> None:
        """
        Starts the WebSocket server in a separate thread.
        """
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def _run_async_loop(self) -> None:
        """Defines the event loop for the new thread and executes it."""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main_loop())
        except Exception as e:
            logging.error(self.locale_manager.get_string("sds_websocket.main_loop.async_error", default="[WS_SERVER] Critical error in Asyncio loop: {error}", error=e))