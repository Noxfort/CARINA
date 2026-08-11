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

# File: src/sas/analysis_orchestrator.py
# Author: Gabriel Moraes
# Date: February 19, 2026

import logging
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

from sas.data_collector import DataCollector
from sas.analyzer_engine import AnalyzerEngine
from sas.analysis_handler import AnalysisHandler
from database.database_manager import DatabaseManager

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class AnalysisOrchestrator:
    """The maestro that manages the workflow of the SAS service, delegating processing to AnalysisHandler."""

    def __init__(self, sas_data_queue: Queue, settings: configparser.ConfigParser, db_data_queue: Queue, locale_manager: 'LocaleManagerBackend', sas_result_queue: Queue = None):
        self.data_queue = sas_data_queue
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        self.collector = DataCollector(self.locale_manager)
        self.engine = AnalyzerEngine(self.settings, db_data_queue, self.locale_manager, sas_result_queue)
        
        # DatabaseManager for V2 DB-based analysis (historical traffic samples)
        try:
            self.db_manager = DatabaseManager(self.locale_manager)
        except Exception as e:
            logging.warning(f"[SAS_ORCH] Failed to initialize DatabaseManager for V2 analysis: {e}")
            self.db_manager = None
        
        # --- Analysis Timing (from settings.ini [ANALYSIS_SCHEDULE]) ---
        self.frequency = self._load_analysis_interval_seconds()
        self.initial_delay = 60    # seconds before first analysis is eligible
        logging.info(lm.get_string("sas_orchestrator.init.analysis_frequency_set", freq=self.frequency))
            
        self.last_analysis_time = 0
        self.last_scenario_name = "hft_live_session"
        self.last_net_file_path = None
        self.current_run_id = None
        self.last_sim_time = None

        self.handler = AnalysisHandler(self)

        logging.info(lm.get_string("sas_orchestrator.init.orchestrator_created"))

    def _load_analysis_interval_seconds(self) -> int:
        """
        Reads the analysis schedule from [ANALYSIS_SCHEDULE] in settings.ini
        and converts it to seconds.
        
        Supports units: days, weeks, months, years.
        Falls back to 7 days (604800s) if the section is missing or invalid.
        """
        UNIT_TO_SECONDS = {
            'days': 86400,
            'weeks': 604800,
            'months': 2592000,   # 30 days
            'years': 31536000,   # 365 days
        }
        DEFAULT_SECONDS = 7 * 86400  # 7 days
        
        try:
            section = self.settings['ANALYSIS_SCHEDULE']
            value = section.getint('analysis_interval_value', 7)
            unit = section.get('analysis_interval_unit', 'days').strip().lower()
            
            multiplier = UNIT_TO_SECONDS.get(unit, 86400)
            result = max(value, 1) * multiplier
            
            logging.info(f"[SAS_ORCH] Analysis interval configured: {value} {unit} ({result}s)")
            return result
        except (KeyError, configparser.NoSectionError, ValueError) as e:
            logging.warning(f"[SAS_ORCH] Could not read [ANALYSIS_SCHEDULE]: {e}. Using default 7 days.")
            return DEFAULT_SECONDS

    def run(self):
        """
        Inicia o serviço e entra no loop principal de coleta e análise.
        """
        self.current_run_id = None
        lm = self.locale_manager
        try:
            logging.info(lm.get_string("sas_orchestrator.run.main_loop_start"))
            while True:
                raw_sim_data = self.data_queue.get()

                if raw_sim_data is None:
                    break

                self.handler.process_message(raw_sim_data)

        except KeyboardInterrupt:
            logging.info(lm.get_string("sas_orchestrator.run.interrupt_received"))
        except Exception as e:
            logging.error(lm.get_string("sas_orchestrator.run.fatal_error", error=e), exc_info=True)
        finally:
            logging.info(lm.get_string("sas_orchestrator.run.orchestrator_shutdown"))