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
Defines the LiveDataProvider.

In this version, the WebSocket client implements a 'Port Hunting' strategy,
attempting to connect sequentially to alternative ports (8765, 8766, 8767) if the default fails.
This synchronizes the UI with the fallback mechanism implemented on the server.
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
    A service that connects to the back-end via WebSocket to provide
    real-time simulation data packets and send commands.
    """
    GLOBAL_SHUTDOWN_EVENT = None
    
    def __init__(self, on_data_received: Callable[[Dict[str, Any]], None], shutdown_event: threading.Event = None):
        self.on_data_received = on_data_received
        self.shutdown_event = shutdown_event
        self._thread = None
        self._is_running = False
        self.loop = None
        
        # List of ports to try to connect to (Sync with websocket_server.py)
        self.target_ports = [8765, 8766, 8767]
        self.current_uri = "" 
        self.websocket_connection = None

    @property
    def is_stopped(self) -> bool:
        """Returns True if the provider has been stopped or system shutdown is requested."""
        if not self._is_running:
            return True
        if self.shutdown_event and self.shutdown_event.is_set():
            return True
        if LiveDataProvider.GLOBAL_SHUTDOWN_EVENT and LiveDataProvider.GLOBAL_SHUTDOWN_EVENT.is_set():
            return True
        return False

    def start(self):
        """Starts the WebSocket client in a separate thread."""
        if not self._thread or not self._thread.is_alive():
            self._is_running = True
            self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self._thread.start()
            logging.info("[LiveDataProvider] WebSocket client to the back-end started.")

    def stop(self):
        """Stops the thread and the WebSocket connection."""
        self._is_running = False
        if self.websocket_connection and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.websocket_connection.close(), self.loop)
            except Exception:
                pass
        if self.loop and self.loop.is_running():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass
        logging.info("[LiveDataProvider] Stop signal sent to the WebSocket client.")

    def _run_async_loop(self):
        """Defines the event loop for the new thread and executes it."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._websocket_thread_loop())
        except Exception as e:
            if not self.is_stopped:
                logging.debug(f"[LiveDataProvider] Error in event loop: {e}")
        finally:
            try:
                pending = [t for t in asyncio.all_tasks(self.loop) if not t.done()]
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self.loop.close()
            except Exception:
                pass

    async def _websocket_thread_loop(self):
        """
        The main loop that manages the connection with port rotation.
        """
        port_index = 0
        
        while not self.is_stopped:
            # Select current port based on index
            port = self.target_ports[port_index]
            self.current_uri = f"ws://127.0.0.1:{port}"
            
            try:
                if self.is_stopped:
                    break
                logging.debug(f"[LiveDataProvider] Attempting to connect to {self.current_uri}...")
                
                async with websockets.connect(self.current_uri) as websocket:
                    self.websocket_connection = websocket
                    logging.info(f"[LiveDataProvider] Successfully connected to the back-end (SDS) on port {port}.")
                    
                    # Ensure UI immediately knows if it's locked down
                    await websocket.send(json.dumps({"type": "check_lockdown"}))
                    
                    # If you connected successfully, we process the messages
                    async for message in websocket:
                        if self.is_stopped:
                            break
                        try:
                            data_packet = json.loads(message)
                            if self.on_data_received:
                                self.on_data_received(data_packet)
                        except json.JSONDecodeError:
                            logging.warning("[LiveDataProvider] Invalid (non-JSON) message received from the back-end.")
            
            except (ConnectionRefusedError, OSError, websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as e:
                self.websocket_connection = None
                if self.is_stopped:
                    break
                
                # Advances to the next port in the list (Round-Robin)
                port_index = (port_index + 1) % len(self.target_ports)
                
                # Wait a while before the next attempt (interruptible if stopping)
                for _ in range(10):
                    if self.is_stopped:
                        break
                    await asyncio.sleep(0.1)
                
                if self.is_stopped:
                    break
                logging.debug(f"[LiveDataProvider] Connection attempt to {self.current_uri} unsuccessful: {e}")
                
            except Exception as e:
                self.websocket_connection = None
                if self.is_stopped:
                    break
                for _ in range(50):
                    if self.is_stopped:
                        break
                    await asyncio.sleep(0.1)
                if not self.is_stopped:
                    logging.debug(f"[LiveDataProvider] Unexpected WebSocket error: {e}")

    def send_command_to_backend(self, command: dict):
        """
        Sends a command (Python dictionary) to the back-end safely
        from any thread.
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
                logging.warning(f"[LiveDataProvider] Failed to send command. The connection may be closed. Error: {e}")
        else:
            # logging.warning("[LiveDataProvider] Attempting to send command without an active connection to the backend.")
            pass