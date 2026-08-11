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

# File: src/main.py (HFT Refactor - Modular Pure Orchestrator)
# Author: Gabriel Moraes
# Date: December 14, 2025

import sys
import os
from datetime import datetime
import logging
import traceback
from multiprocessing import Queue
from multiprocessing.connection import Connection

# Add 'src' directory to python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.paths import get_base_output_dir
from utils.logging_setup import setup_logging
from utils.locale_manager_backend import LocaleManagerBackend
from utils.settings_manager import SettingsManager
from utils.hardware_initializer import HardwareInitializer
from utils.process_monitor import ProcessMonitor


def run_ai_process(
    pipe_conn: Connection,
    guardian_state_queue: Queue,
    guardian_signal_queue: Queue,
    db_data_queue: Queue
):
    """
    Main orchestrator for the AI Process (HFT Mode).
    Coordinates environment logging, hardware setup, resource monitoring,
    and starts the continuous service loop of the Trainer engine.
    """
    # 1. Logging Initialization
    log_base_dir = get_base_output_dir()
    log_dir_ai = os.path.join(log_base_dir, "logs", "main_ai", datetime.now().strftime("%Y%m%d-%H%M%S"))
    log_configured = False
    try:
        os.makedirs(log_dir_ai, exist_ok=True)
        setup_logging(log_dir=log_dir_ai)
        log_configured = True
    except Exception as e:
        print(f"[AI Process ERROR] Failed to setup logging: {e}")

    def print_and_log(message: str, level: str = "info"):
        print(f"[AI Process] {message}")
        if log_configured:
            if level == "info": logging.info(message)
            elif level == "warning": logging.warning(message)
            elif level == "error": logging.error(message)
            elif level == "debug": logging.debug(message)

    # 2. Locale Backend Initialization
    try:
        lm = LocaleManagerBackend()
        lang_code = lm.current_lang_data.get('lang_code', lm.get_language())
        print_and_log(lm.get_string("main_ai.locale_init", default="LocaleManager initialized. Language: {lang}", lang=lang_code))
    except Exception as e:
        print_and_log(f"Failed to initialize LocaleManagerBackend: {e}", level="error")

        class DummyLM:
            def get_string(self, key, default=None, **kwargs):
                val = default if default is not None else key
                return val.format(**kwargs) if kwargs else val
            def get_language(self): return "pt_br"

        lm = DummyLM()

    print_and_log(lm.get_string("main_ai.bootstrapping", default="--- AI Process Bootstrapping (HFT Mode) ---"))
    print_and_log(lm.get_string("main_ai.loading_components", default="Loading AI Engine components..."))

    # 3. Hardware Acceleration & PyTorch Setup
    try:
        HardwareInitializer.setup_environment(logging_func=print_and_log)
        from engine.trainer import Trainer
        print_and_log(lm.get_string("main_ai.components_loaded", default="AI Engine components loaded successfully."))
    except ImportError as e_import:
        print_and_log(lm.get_string("main_ai.critical_import_error", default="CRITICAL IMPORT ERROR: {error}", error=e_import), level="error")
        return
    except Exception as e_gen:
        print_and_log(lm.get_string("main_ai.critical_load_error", default="CRITICAL ERROR during loading phase: {error}\n{traceback}", error=e_gen, traceback=traceback.format_exc()), level="error")
        return

    # 4. Background Resource Monitoring Daemon
    ProcessMonitor.start_background_monitor(process_name="AI_Process", port=8002)

    # 5. Load GPU Metadata & System Settings
    gpu_info = HardwareInitializer.detect_gpu(locale_manager=lm, logging_func=print_and_log)

    try:
        settings = SettingsManager().load_config()
    except Exception as e_cfg:
        print_and_log(f"Failed to load settings: {e_cfg}", level="error")
        return

    # 6. Instantiate Trainer and Start Continuous Service Loop
    try:
        print_and_log(lm.get_string("main_ai.initializing_trainer", default="[MAIN_AI] Initializing Trainer..."))
        trainer = Trainer(
            settings=settings,
            log_dir=log_dir_ai,
            gpu_info=gpu_info,
            pipe_conn=pipe_conn,
            guardian_state_queue=guardian_state_queue,
            guardian_signal_queue=guardian_signal_queue,
            db_data_queue=db_data_queue
        )

        print_and_log(lm.get_string("main_ai.trainer_ready", default="Trainer ready. Entering event loop..."))
        trainer.start_continuous_service()
        print_and_log(lm.get_string("main_ai.trainer_finished", default="Trainer service finished."), level="info")

    except (KeyboardInterrupt, SystemExit):
        print_and_log(lm.get_string("main_ai.trainer_finished", default="Trainer service interrupted."), level="info")
    except Exception as e_main:
        print_and_log(lm.get_string("main_ai.fatal_error", default="FATAL ERROR in AI Process: {error}", error=e_main), level="error")
        sys.exit(1)
    finally:
        print_and_log(lm.get_string("main_ai.process_exiting", default="--- AI Process Exiting ---"))
        os._exit(0)