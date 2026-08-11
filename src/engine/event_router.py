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

# File: src/engine/event_router.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import time
import logging
from multiprocessing.connection import Connection
from typing import Any

from manager.agent_manager import AgentManager
from engine.step_processor import StepProcessor

class EventRouter:
    """
    Orchestrates the infinite WebSocket/Pipe event loop, consuming data until
    a valid message arrives and routing it to the internal Simulation step (StepProcessor)
    or Map update step (Trainer root).
    """
    def __init__(self, pipe_conn: Connection, trainer_instance: Any, agent_manager: AgentManager, step_processor: StepProcessor):
        self.pipe_conn = pipe_conn
        self.trainer = trainer_instance
        self.agent_manager = agent_manager
        self.step_processor = step_processor

    def start_continuous_service(self):
        """
        Main Event Loop: Hibernate -> Drain -> Decide.
        """
        logging.info("Trainer entering Active Standby mode (Event-Driven)...")
        last_warn_time = 0
        
        while self.trainer.is_running:
            try:
                # 1. HIBERNATE: Block until data arrives
                if self.pipe_conn.poll(timeout=None):
                    
                    # 2. DRAIN BUFFER (Conflation)
                    commands = []
                    try:
                        commands.append(self.pipe_conn.recv())
                    except EOFError:
                        self.trainer.is_running = False
                        break

                    while self.pipe_conn.poll():
                        try:
                            commands.append(self.pipe_conn.recv())
                        except EOFError:
                            self.trainer.is_running = False
                            break
                    
                    if not self.trainer.is_running: break

                    hft_command = None
                    dropped_frames = 0
                    
                    for cmd in commands:
                        if not isinstance(cmd, (list, tuple)) or len(cmd) < 3:
                            continue
                            
                        module, func, args = cmd[0], cmd[1], cmd[2]
                        
                        if module == "custom" and func == "hft_step":
                            if hft_command is not None:
                                dropped_frames += 1
                            hft_command = cmd
                        else:
                            # 3. ROUTE ADMIN COMMANDS IMMEDIATELY
                            self._execute_command(module, func, args)
                            
                    if dropped_frames > 0:
                        logging.debug(f"[SYNC] Drained {dropped_frames} stale frames.")

                    # 4. ROUTE THE LATEST HFT FRAME
                    if hft_command:
                        self._execute_command(hft_command[0], hft_command[1], hft_command[2])

            except (EOFError, KeyboardInterrupt, SystemExit):
                self.trainer.is_running = False
                break
            except Exception as e:
                logging.error(f"Event Loop Error: {e}", exc_info=True)
                
    def _execute_command(self, module: str, func: str, args: tuple):
        """Routes unpacked commands to the correct modules."""
        if module == "custom" and func == "hft_step":
            if not self.trainer.agents:
                if not hasattr(self, '_last_warn_time'): self._last_warn_time = 0
                if time.time() - self._last_warn_time > 5:
                    logging.warning("[HFT] Data received but AGENTS not loaded.")
                    self._last_warn_time = time.time()
            else:
                if not getattr(self, '_ai_started_logged', False):
                    logging.info("--- AI Engine Started Operating (HFT Mode) ---")
                    print("[AI Process] --- AI Engine Started Operating (HFT Mode) ---")
                    self._ai_started_logged = True
                self.step_processor.process_hft_step(args[0], self.trainer.agents)
                
        elif module == "custom" and func == "load_map":
            self.trainer._load_map(args[0])
        
        elif module == "system" and func == "save_checkpoint":
            self.agent_manager.save_system_state(
                self.trainer.current_map_path, self.trainer.agents, self.trainer.strategist
            )
            
        elif module == "hardware" and func == "toggle_connection":
            action = args[2] if len(args) > 2 else "toggle"
            self.trainer.connection_manager.toggle_connection(args[0], args[1], action=action)

        elif module == "hardware" and func == "apply_override":
            if self.trainer.action_supervisor:
                self.trainer.action_supervisor.apply_hardware_override(args[0], args[1])
            
        elif module == "system" and func == "shutdown":
            self.trainer.is_running = False
