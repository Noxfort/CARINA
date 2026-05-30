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

# File: src/central_controller.py
# Author: Gabriel Moraes
# Date: 09/01/2026

import logging
import configparser
import time
import sys
import os
import json
import grpc
from concurrent import futures
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import TYPE_CHECKING, Dict

# Add 'src' directory to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add 'proto' directory to path
proto_path = os.path.join(project_root, 'proto')
if proto_path not in sys.path:
    sys.path.insert(0, proto_path)

# Import generated gRPC modules (dynamically added to path)
try:
    import synapse_hft_pb2 as pb2 # type: ignore
    import synapse_hft_pb2_grpc as pb2_grpc # type: ignore
except ImportError:
    logging.critical("[CentralController] Failed to import generated gRPC modules. Ensure 'proto' folder exists and contains generated files.")
    pb2, pb2_grpc = None, None # type: ignore

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from controller.health_monitor import AIHealthMonitor
from controller.request_processor import RequestProcessor
from controller.override_manager import OverrideManager
from communication.hft_server import CarinaHFTImpl
from utils.map_processor import MapProcessor
from sds.telemetry_aggregator import TelemetryAggregator
from communication.monitor_client import MonitorClient
from utils.settings_manager import SettingsManager

from controller.failsafe_manager import FailsafeManager
from controller.traffic_frame_processor import TrafficFrameProcessor
from controller.topology_manager import TopologyManager
from sas.traffic_data_recorder import TrafficDataRecorder
from database.database_manager import DatabaseManager
from utils.safety_rules import SafetyRules

# --- CENTRAL CONTROLLER ---
class CentralController:
    """
    The Brain of the Operation.
    Orchestrates the flow of data between the Perception Layer (Synapse),
    the AI Engine, the Safety Watchdog, and the User Interface.
    
    Adheres to SRP: Delegates specific tasks (I/O, Communication, Aggregation) to specialized modules.
    """

    def __init__(self, settings: configparser.ConfigParser, ai_pipe_conn: Connection,
                 watchdog_queue: Queue, sds_data_queue: Queue, sas_data_queue: Queue,
                 ui_command_queue: Queue, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_queue = watchdog_queue
        self.sds_data_queue = sds_data_queue
        self.ui_command_queue = ui_command_queue
        self.locale_manager = locale_manager
        
        self.override_manager = OverrideManager(locale_manager=self.locale_manager)
        
        # Telemetry Aggregator (Handles Visualization Logic). Decreased to 5.0s for realistic Heatmap rendering.
        self.telemetry_aggregator = TelemetryAggregator(update_interval=5.0)
        
        # Fallback 0.30 (300ms) as per CARINA real-time safety requirement
        heartbeat_timeout = settings.getfloat('WATCHDOG', 'heartbeat_timeout_seconds', fallback=0.30)
        self.health_monitor = AIHealthMonitor(
            heartbeat_timeout=heartbeat_timeout,
            locale_manager=self.locale_manager
        )
        
        self.server = None
        self.is_running = True
        
        # Monitor Integration
        self.monitor_client = MonitorClient(SettingsManager())
        self.monitor_client.start()
        
        # --- Traffic Rules from Centralized Config (for Fixed-Time Controller / Failsafe) ---
        green_duration = SafetyRules.get_min_green()
        yellow_duration = SafetyRules.get_yellow()
        all_red_duration = SafetyRules.get_all_red()
        
        self.failsafe_manager = FailsafeManager(
            ai_pipe_conn=self.ai_pipe_conn,
            monitor_client=self.monitor_client,
            green_duration=green_duration,
            yellow_duration=yellow_duration,
            all_red_duration=all_red_duration
        )
        # Wire the Synapse silence timeout to match watchdog
        self.failsafe_manager.set_failsafe_timeout(heartbeat_timeout)
        
        self.topology_manager = TopologyManager(
            project_root=project_root,
            ai_pipe_conn=self.ai_pipe_conn,
            sds_data_queue=self.sds_data_queue
        )
        # --- TrafficDataRecorder: Records gRPC frames to DB for optimization analysis ---
        try:
            self.db_manager = DatabaseManager(self.locale_manager)
            self.traffic_data_recorder = TrafficDataRecorder(
                db_manager=self.db_manager,
                batch_size=10
            )
        except Exception as e:
            logging.warning(f"[CentralController] Failed to initialize TrafficDataRecorder: {e}")
            self.db_manager = None
            self.traffic_data_recorder = None

        self.traffic_frame_processor = TrafficFrameProcessor(
            ai_pipe_conn=self.ai_pipe_conn,
            watchdog_queue=self.watchdog_queue,
            sds_data_queue=self.sds_data_queue,
            failsafe_manager=self.failsafe_manager,
            topology_manager=self.topology_manager,
            telemetry_aggregator=self.telemetry_aggregator,
            traffic_data_recorder=self.traffic_data_recorder
        )
        
        self.request_processor = RequestProcessor(
            settings=settings,
            ai_pipe_conn=ai_pipe_conn,
            watchdog_q=watchdog_queue,
            health_monitor=self.health_monitor,
            sds_data_queue=sds_data_queue,
            sas_data_queue=sas_data_queue,
            ui_command_queue=ui_command_queue,
            locale_manager=self.locale_manager,
            override_manager=self.override_manager,
            failsafe_manager=self.failsafe_manager,
            topology_manager=self.topology_manager
        )
        
        # --- Two-Stage Readiness Latch ---
        self.is_ui_ready = False
        self.is_backend_ready = False
        self.request_processor.set_readiness_callbacks(self.set_ui_ready, self.set_backend_ready)
        
        # Try to restore previous state if available
        self.topology_manager.try_restore_state()
        
        # Pre-load topology for failsafe readiness
        self._preload_failsafe_topology()

    def _preload_failsafe_topology(self):
        """
        If a topology was restored, pre-load it into the FixedTimeController
        so failsafe can activate instantly with zero delay.
        """
        if self.topology_manager.net_file_path:
            self.failsafe_manager.load_topology(self.topology_manager.net_file_path)

    def set_ui_ready(self):
        self.is_ui_ready = True
        self.check_system_readiness()

    def set_backend_ready(self):
        self.is_backend_ready = True
        self.check_system_readiness()

    def check_system_readiness(self):
        if self.is_ui_ready and self.is_backend_ready:
            logging.info("✅ [LATCH] Fronte-end and API fully loaded. Unlocking AI Engine for decision making.")
            self.traffic_frame_processor.set_system_ready(True)
        else:
            if not self.is_ui_ready:
                logging.warning("⚠️ [LATCH] AI Engine paused: waiting for Front-End (UI) readiness ('carina_ready'). Frames will be dropped.")
            if not self.is_backend_ready:
                logging.warning("⚠️ [LATCH] AI Engine paused: waiting for Backend components to finish loading.")



    def run(self):
        lm = self.locale_manager
        logging.info(f"[DIAGNOSTICS] Starting HFT CentralController.")
        server_port = self.settings.get('SYNAPSE', 'port', fallback='50051')
        max_workers = self.settings.getint('SYNAPSE', 'max_workers', fallback=10)

        try:
            self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
            if pb2_grpc:
                # Import CarinaHFTImpl from communication module (delegated logic)
                pb2_grpc.add_HFTLinkServicer_to_server(CarinaHFTImpl(self), self.server) # type: ignore
            
            bind_address = f'[::]:{server_port}'
            self.server.add_insecure_port(bind_address)
            
            logging.info(lm.get_string("central_controller.grpc.starting", port=server_port, fallback=f"gRPC Server listening on {bind_address}"))
            self.server.start()
            
            # --- MAIN HFT LOOP ---
            logging.info("[CentralController] Entering main HFT processing loop...")
            while self.is_running:
                # Check for shutdown signal from launcher
                if self.ai_pipe_conn.poll():
                    try:
                        cmd = self.ai_pipe_conn.recv()
                        if isinstance(cmd, tuple) and len(cmd) >= 2 and cmd[0] == "system" and cmd[1] == "shutdown":
                            logging.info("[CentralController] Shutdown signal received. Exiting main loop gracefully...")
                            self.is_running = False
                            break
                    except Exception as e:
                        logging.error(f"[CentralController] Pipe poll error: {e}")

                # --- FAILSAFE MONITORING (In-Process Synapse Silence Detection) ---
                if not self.failsafe_manager.failsafe_active:
                    # Check if Synapse has gone silent beyond the 300ms threshold
                    if not self.failsafe_manager.check_synapse_health():
                        self.failsafe_manager.trigger_failsafe()
                else:
                    # FAILSAFE IS ACTIVE: Tick the Fixed-Time Controller
                    phase_changes = self.failsafe_manager.tick()
                    if phase_changes:
                        # Send fixed-time state changes to dashboard for visualization
                        try:
                            self.sds_data_queue.put(('failsafe_phase_update', {
                                'changes': phase_changes,
                                'status': self.failsafe_manager.get_status()
                            }))
                        except Exception as e:
                            logging.error(f"[CentralController] Error sending failsafe update to SDS: {e}")

                try:
                    # sumo_conn=None because there is no direct SUMO connection here.
                    self.request_processor.process_queues(sumo_conn=None, is_ai_healthy=not self.failsafe_manager.failsafe_active)
                except Exception as e_proc:
                    logging.error(f"[CentralController] Error in processing loop: {e_proc}")
                
                # Small sleep to relieve CPU while waiting for events
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            logging.info("Manual interruption received.")
        except Exception as e:
            logging.critical(f"Fatal error in gRPC server: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        logging.info("Stopping CentralController...")
        self.is_running = False
        
        # Deactivate fixed-time controller if running
        if self.failsafe_manager.failsafe_active:
            self.failsafe_manager.fixed_time_controller.deactivate()
        
        if self.server: self.server.stop(0)
        try: self.ai_pipe_conn.send(('system', 'shutdown', (), {}))
        except: pass
        if getattr(self, 'monitor_client', None):
            self.monitor_client.stop(shutdown_message="CARINA System Shutting Down...")

    # --- MAP LOGIC (Delegated to MapProcessor) ---

    def handle_new_map(self, map_path: str, maps_output_dir: str):
        self.topology_manager.handle_new_map(map_path, maps_output_dir, self.telemetry_aggregator)
        # Pre-load topology for failsafe readiness whenever a new map arrives
        self._preload_failsafe_topology()
        # Update TrafficDataRecorder with topology edge metadata
        self._update_recorder_topology(map_path)

    def start_ai_session(self):
        logging.info("AI Session started.")

    def stop_ai_session(self):
        logging.info("AI Session stopped.")

    def trigger_failsafe(self):
        """
        Forces the system into Fail-Safe (Watchdog) mode.
        Should be called when external Watchdog process detects silence.
        """
        self.failsafe_manager.trigger_failsafe()

    def process_traffic_frame(self, frame):
        """
        Processes a single Traffic Frame received from Synapse.
        This is the TRIGGER for the AI Decision Cycle.
        """
        self.traffic_frame_processor.process_traffic_frame(frame)

    def _update_recorder_topology(self, net_file_path: str):
        """
        Extracts edge topology (length, lanes, max_speed) from the SUMO net
        file and pushes it to the TrafficDataRecorder for sample enrichment.
        """
        if not self.traffic_data_recorder or not net_file_path:
            return
        try:
            from utils.network_topology_parser import NetworkTopologyParser
            parser = NetworkTopologyParser(self.locale_manager)
            _, junction_incoming_edges = parser.build(net_file_path)
            
            # Flatten all edges into a single dict of {edge_id: {length, lanes, max_speed}}
            topology_edges = {}
            for j_id, edges in junction_incoming_edges.items():
                for edge_id, edge_data in edges.items():
                    topology_edges[edge_id] = {
                        'length': edge_data.get('length', 0),
                        'lanes': edge_data.get('num_lanes', 1),
                        'max_speed': edge_data.get('speed_limit', 13.89),
                    }
            self.traffic_data_recorder.set_topology(topology_edges)
        except Exception as e:
            logging.warning(f"[CentralController] Failed to update recorder topology: {e}")