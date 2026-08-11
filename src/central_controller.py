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

from controller.system_readiness_latch import SystemReadinessLatch
from communication.grpc_server_manager import GrpcServerManager
from sas.topology_recorder_bridge import TopologyRecorderBridge
from core.hft_event_loop import HftEventLoop
from core.hft_system_facade import HftSystemFacade

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
                 ui_command_queue: Queue, locale_manager: 'LocaleManagerBackend', mfd_trigger_queue: Queue = None):
        self.settings = settings
        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_queue = watchdog_queue
        self.sds_data_queue = sds_data_queue
        self.ui_command_queue = ui_command_queue
        self.locale_manager = locale_manager
        
        self.override_manager = OverrideManager(locale_manager=self.locale_manager)
        
        # Telemetry Aggregator (Handles Visualization Logic). Decreased to 5.0s for realistic Heatmap rendering.
        self.telemetry_aggregator = TelemetryAggregator(update_interval=5.0)
        
        # Fallback 5.0s for realistic Synapse streaming heartbeat timeout
        heartbeat_timeout = settings.getfloat('WATCHDOG', 'heartbeat_timeout_seconds', fallback=5.0)
        self.health_monitor = AIHealthMonitor(
            heartbeat_timeout=heartbeat_timeout,
            locale_manager=self.locale_manager
        )
        

        
        # Monitor Integration
        self.monitor_client = MonitorClient(SettingsManager(), self.locale_manager)
        self.monitor_client.start()
        
        self.failsafe_manager = FailsafeManager(
            ai_pipe_conn=self.ai_pipe_conn,
            monitor_client=self.monitor_client,
            locale_manager=self.locale_manager
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
                batch_size=10,
                topology_manager=self.topology_manager
            )
        except Exception as e:
            logging.warning(self.locale_manager.get_string("central_controller.traffic_recorder_fail", default="[CentralController] Failed to initialize TrafficDataRecorder: {error}", error=e))
            self.db_manager = None
            self.traffic_data_recorder = None

        self.traffic_frame_processor = TrafficFrameProcessor(
            ai_pipe_conn=self.ai_pipe_conn,
            watchdog_queue=self.watchdog_queue,
            sds_data_queue=self.sds_data_queue,
            failsafe_manager=self.failsafe_manager,
            topology_manager=self.topology_manager,
            telemetry_aggregator=self.telemetry_aggregator,
            override_manager=self.override_manager,
            traffic_data_recorder=self.traffic_data_recorder
        )
        
        self.mfd_trigger_queue = mfd_trigger_queue
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
            topology_manager=self.topology_manager,
            mfd_trigger_queue=self.mfd_trigger_queue
        )
        
        # --- Two-Stage Readiness Latch ---
        self.readiness_latch = SystemReadinessLatch(self.traffic_frame_processor)
        self.request_processor.set_readiness_callbacks(
            self.readiness_latch.set_ui_ready, 
            self.readiness_latch.set_backend_ready
        )
        
        self.topology_recorder_bridge = TopologyRecorderBridge(
            traffic_data_recorder=self.traffic_data_recorder,
            locale_manager=self.locale_manager
        )
        
        # Try to restore previous state if available
        self.topology_manager.try_restore_state()
        
        # Pre-load topology for failsafe readiness
        self._preload_failsafe_topology()
        
        # Create the facade to shield the gRPC server from the rest of the system
        self.hft_system_facade = HftSystemFacade(
            topology_manager=self.topology_manager,
            topology_recorder_bridge=self.topology_recorder_bridge,
            telemetry_aggregator=self.telemetry_aggregator,
            watchdog_queue=self.watchdog_queue,
            ui_command_queue=self.ui_command_queue,
            traffic_frame_processor=self.traffic_frame_processor,
            failsafe_manager=self.failsafe_manager
        )

        self.grpc_server_manager = GrpcServerManager(
            settings=settings,
            locale_manager=locale_manager,
            implementation_instance=self.hft_system_facade
        )
        
        self.hft_event_loop = HftEventLoop(
            ai_pipe_conn=self.ai_pipe_conn,
            failsafe_manager=self.failsafe_manager,
            request_processor=self.request_processor,
            sds_data_queue=self.sds_data_queue
        )
        self.is_running = True

    def _preload_failsafe_topology(self):
        """
        If a topology was restored, pre-load it into the FixedTimeController
        so failsafe can activate instantly with zero delay.
        """
        if self.topology_manager.net_file_path:
            self.failsafe_manager.load_topology(self.topology_manager.net_file_path)

    def run(self):
        lm = self.locale_manager
        logging.info(lm.get_string("central_controller.starting", default="[DIAGNOSTICS] Starting HFT CentralController."))
        server_port = self.settings.get('SYNAPSE', 'port', fallback='50051')
        max_workers = self.settings.getint('SYNAPSE', 'max_workers', fallback=10)

        try:
            self.grpc_server_manager.start()
            # --- MAIN HFT LOOP ---
            self.hft_event_loop.run_loop()
                
        except KeyboardInterrupt:
            logging.info(lm.get_string("central_controller.manual_interrupt", default="Manual interruption received."))
        except Exception as e:
            logging.critical(lm.get_string("central_controller.grpc_fatal_error", default="Fatal error in gRPC server: {error}", error=e), exc_info=True)
        finally:
            self.stop()

    def stop(self):
        logging.info(self.locale_manager.get_string("central_controller.stopping", default="Stopping CentralController..."))
        self.is_running = False
        if hasattr(self, 'hft_event_loop'):
            self.hft_event_loop.stop()
        
        # We no longer deactivate local FixedTimeController here since CARINA is agnostic
        # and delegating it to Edge hardware.
        pass
        
        if self.grpc_server_manager: self.grpc_server_manager.stop()
        try: self.ai_pipe_conn.send(('system', 'shutdown', (), {}))
        except: pass
        if getattr(self, 'monitor_client', None):
            shutdown_msg = self.locale_manager.get_string("monitor.shutdown", default="CARINA System Shutting Down...")
            self.monitor_client.stop(shutdown_message=shutdown_msg)
