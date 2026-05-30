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

# File: src/main.py (HFT Refactor - Removed TraCI Proxy)
# Author: Gabriel Moraes
# Date: December 14, 2025

import sys
import os
import configparser
from datetime import datetime
import logging
import traceback
from multiprocessing import Queue
from multiprocessing.connection import Connection
import threading
import time

# Add 'src' directory to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Essential Light Imports ---
from utils.paths import resource_path, get_base_output_dir
from utils.logging_setup import setup_logging
from utils.locale_manager_backend import LocaleManagerBackend
from utils.metrics_manager import MetricsManager
# --- End ---

def run_ai_process(pipe_conn: Connection, guardian_state_queue: Queue,
                   guardian_signal_queue: Queue, db_data_queue: Queue):
    """
    The main entry point for the AI process (HFT Edition).
    Now operates independently of the TraCI/SUMO protocol.
    """
    # --- Initial Configuration (Logging, Locale) ---
    log_base_dir = get_base_output_dir()
    log_dir_ai = os.path.join(log_base_dir, "logs", "main_ai", datetime.now().strftime("%Y%m%d-%H%M%S"))
    try:
        os.makedirs(log_dir_ai, exist_ok=True)
        setup_logging(log_dir=log_dir_ai)
        log_configured = True
    except Exception as e:
        print(f"[AI Process ERROR] Failed to setup logging: {e}")
        log_configured = False

    def print_and_log(message, level="info"):
        print(f"[AI Process] {message}")
        if log_configured:
            if level == "info": logging.info(message)
            elif level == "warning": logging.warning(message)
            elif level == "error": logging.error(message)
            elif level == "debug": logging.debug(message)

    print_and_log("--- AI Process Bootstrapping (HFT Mode) ---")

    # --- Initialize Locale ---
    try:
        lm = LocaleManagerBackend()
        print_and_log(f"LocaleManager initialized. Language: {lm.current_lang_data.get('lang_code', 'N/A')}")
    except Exception as e:
        print_and_log(f"Failed to initialize LocaleManagerBackend: {e}", level="error")
        # Simple fallback
        class DummyLM:
             def get_string(self, key, fallback=None, **kwargs): return fallback if fallback else key
        lm = DummyLM()

    # --- LATE IMPORTS (Lazy Imports) ---
    print_and_log("Loading AI Engine components...")
    try:
        import psutil
        import torch
        
        # --- Patch for PyInstaller + TorchScript ---
        # We maintain the patch to ensure compatibility on frozen builds
        def _jit_script_shim(obj, *args, **kwargs):
            return obj
        torch.jit.script = _jit_script_shim
        # --------------------------------------------
        
        # --- TensorCore (TF32) Hardware Acceleration Optimization ---
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.set_float32_matmul_precision('high')
        print_and_log("⚡ Hardware Acceleration (TensorCores/TF32) enabled strictly.", level="info")
        # ------------------------------------------------------------

        # CHANGE: We no longer import 'traci_proxy'.
        # The AI ​​is now simulator agnostic.
        
        from engine.trainer import Trainer
        print_and_log("AI Engine components loaded successfully.")

    except ImportError as e_import:
        print_and_log(f"CRITICAL IMPORT ERROR: {e_import}", level="error")
        return
    except Exception as e_gen:
         print_and_log(f"CRITICAL ERROR during loading phase: {e_gen}\n{traceback.format_exc()}", level="error")
         return

    # --- Monitor Thread ---
    metrics_manager = MetricsManager(process_name="AI_Process", port=8002)
    metrics_manager.register_metric('process_cpu_usage_percent', 'CPU %')
    metrics_manager.register_metric('process_memory_usage_percent', 'Mem %')

    current_process = psutil.Process()

    def monitor_loop(metrics: MetricsManager, process: psutil.Process, queues: dict, interval: int = 5):
        while True:
            try:
                cpu = process.cpu_percent(interval=None)
                mem = process.memory_percent()
                metrics.update_metric('process_cpu_usage_percent', cpu if cpu is not None else 0.0)
                metrics.update_metric('process_memory_usage_percent', mem)
                # Queue metrics can be added here
            except Exception:
                break
            time.sleep(interval)

    monitor_thread = threading.Thread(
        target=monitor_loop,
        args=(metrics_manager, current_process, {}),
        daemon=True
    )
    monitor_thread.start()

    # --- Main Logic ---
    try:
        # Check GPU
        gpu_info = "N/A"
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_info = gpu_name
            print_and_log(f"✅ GPU Detected: {gpu_name}")
        else:
            print_and_log("⚠️ No GPU detected. Running on CPU.", level="warning")

        # Load Settings
        def load_settings():
             config_path = resource_path(os.path.join("config", "settings.ini"))
             config = configparser.ConfigParser()
             if not config.read(config_path, encoding='utf-8'):
                  raise FileNotFoundError(f"Settings not found at {config_path}")
             return config
        
        settings = load_settings()

        # Instantiates the Trainer (The brain of the operation)
        print_and_log("[MAIN_AI] Initializing Trainer...")
        trainer = Trainer(
            settings=settings,
            log_dir=log_dir_ai,
            gpu_info=gpu_info,
            pipe_conn=pipe_conn,
            guardian_state_queue=guardian_state_queue,
            guardian_signal_queue=guardian_signal_queue,
            db_data_queue=db_data_queue
        )
        
        print_and_log("Trainer ready. Entering event loop...")
        
        # Starts continuous service (Pipe Message Loop)
        trainer.start_continuous_service()

        print_and_log("Trainer service finished.", level="info")

    except Exception as e_main:
         print_and_log(f"FATAL ERROR in AI Process: {e_main}", level="error")
         sys.exit(1)

    finally:
        print_and_log("--- AI Process Exiting ---")