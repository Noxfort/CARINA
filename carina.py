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

# File: carina.py (HFT Edition - Fixed XAI Worker)
# Author: Gabriel Moraes
# Date: December 16, 2025

import sys
import os
import time
import configparser
import logging
import multiprocessing
from multiprocessing import Process, Queue, Pipe, set_start_method
from multiprocessing.connection import Connection
import threading
import psutil
import traceback
import socket

# --- Paths and Variables Setup ---
IS_FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

if IS_FROZEN:
    # project_root = directory of the executable (for writable output dirs)
    project_root = os.path.dirname(sys.executable)
    # bundle_root = _internal/ directory where PyInstaller puts bundled data
    bundle_root = sys._MEIPASS
else:
    project_root = os.path.dirname(os.path.abspath(__file__))
    bundle_root = project_root

# Add critical paths to sys.path (src, proto, ui)
# In frozen mode, these are inside _internal/ (bundle_root), NOT next to the executable
paths_to_add = [
    os.path.join(bundle_root, 'src'),
    os.path.join(bundle_root, 'proto'),
    os.path.join(bundle_root, 'ui')
]

for p in paths_to_add:
    if p not in sys.path:
        sys.path.insert(0, p)

# --- Environment Settings ---
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul')
    except Exception: pass

# --- Conditional Imports ---
try:
    if IS_FROZEN:
        from utils.paths import resource_path, get_base_output_dir
        from central_controller import CentralController
        from main import run_ai_process
        from watchdog import run_watchdog
        from utils.logging_setup import setup_logging
        from sds.dashboard_worker import run_sds_worker
        from sas.analysis_worker import run_analysis_worker
        from database.database_worker import run_database_worker
        # --- CHANGE: Importing XAI Worker ---
        from xai.xai_worker import run_xai_worker
        # --------------------------------------
        from utils.metrics_manager import MetricsManager
        from utils.locale_manager_backend import LocaleManagerBackend
    else:
        # Direct imports thanks to tweaked sys.path
        from utils.paths import resource_path, get_base_output_dir
        from central_controller import CentralController
        from main import run_ai_process
        from watchdog.watchdog_process import run_watchdog
        from utils.logging_setup import setup_logging
        from sds.dashboard_worker import run_sds_worker
        from sas.analysis_worker import run_analysis_worker
        from database.database_worker import run_database_worker
        # --- CHANGE: Importing XAI Worker ---
        from xai.xai_worker import run_xai_worker
        # --------------------------------------
        from utils.metrics_manager import MetricsManager
        from utils.locale_manager_backend import LocaleManagerBackend
        
    import xxhash 
except ImportError as e:
    if __name__ == "__main__":
        print(f"CRITICAL IMPORT ERROR: {e}")
        traceback.print_exc()
    sys.exit(1)

# Try importing the UI
try:
    import ui.main_ui as ui_module
    import flet as ft
    UI_AVAILABLE = True
except ImportError as e:
    UI_AVAILABLE = False
    if __name__ == "__main__":
        print(f"[Launcher Warning] UI não disponível: {e}")

# Try importing the System Tray handler
try:
    from ui.handlers.tray_handler import TrayHandler
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    if __name__ == "__main__":
        print("[Launcher Warning] System tray não disponível (pystray ausente)")

# --- Definition of the Central Process (Controller) ---
def run_controller_process(settings, pipe_conn, wd_q, sds_q, sas_q, ui_q):
    log_base_dir = get_base_output_dir()
    log_dir = os.path.join(log_base_dir, "logs", "central_controller")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    logging.info("[CentralController Process] Starting...")
    locale_manager = LocaleManagerBackend()
    
    # Start metrics
    metrics_manager = MetricsManager(process_name="CentralController", port=8001)
    
    controller = CentralController(settings, pipe_conn, wd_q, sds_q, sas_q, ui_q, locale_manager)
    controller.run() # Blocks here on the gRPC server

# --- MAIN FUNCTION ---
def main():
    log_base_dir = get_base_output_dir()
    launcher_log_dir = os.path.join(log_base_dir, "logs", "launcher")
    os.makedirs(launcher_log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [LAUNCHER] %(message)s',
        handlers=[logging.FileHandler(os.path.join(launcher_log_dir, "launcher.log"), mode='w'), logging.StreamHandler(sys.stdout)]
    )
    
    logging.info("--- CARINA SYSTEM STARTING (HFT) ---")
    
    settings = configparser.ConfigParser()
    settings_path = resource_path(os.path.join("config", "settings.ini"))
    if not settings.read(settings_path, encoding='utf-8'):
        logging.critical(f"Settings not found at: {settings_path}")
        sys.exit(1)

    controller_conn, ai_conn = Pipe()
    queues = {
        'wd': Queue(), 'sds': Queue(), 'sas': Queue(), 
        'ui': Queue(), 'db': Queue(), 
        'g_state': Queue(), 'g_signal': Queue()
    }
    
    processes = []
    
    try:
        logging.info("Iniciando processos de BACKEND...")
        
        # 1. Central Controller
        p_cc = Process(target=run_controller_process, 
                       args=(settings, controller_conn, queues['wd'], queues['sds'], queues['sas'], queues['ui']), 
                       name="CentralController")
        processes.append(p_cc)
        
        # 2. AI Engine
        p_ai = Process(target=run_ai_process, 
                       args=(ai_conn, queues['g_state'], queues['g_signal'], queues['db']), 
                       name="AI_Process")
        processes.append(p_ai)
        
        # 3. Auxiliary Workers
        lm = LocaleManagerBackend()
        
        # Results directory for XAI Worker to find checkpoints
        hft_results_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session")
        os.makedirs(hft_results_dir, exist_ok=True)

        processes.append(Process(target=run_watchdog, args=(queues['wd'], lm), name="Watchdog"))
        processes.append(Process(target=run_sds_worker, args=(queues['sds'], settings, queues['ui']), name="DashboardService"))
        processes.append(Process(target=run_analysis_worker, args=(queues['sas'], settings, queues['db']), name="AnalysisService"))
        processes.append(Process(target=run_database_worker, args=(queues['db'],), name="DatabaseWorker"))
        
        # --- CHANGE: Start XAI Worker ---
        logging.info("Iniciando Worker XAI...")
        processes.append(Process(target=run_xai_worker, args=(settings, hft_results_dir), name="XAI_Worker"))
        # -----------------------------------
        
        for p in processes:
            p.start()
            time.sleep(0.5)
            
        logging.info("Backend iniciado.")
        
        # --- System Tray Setup ---
        tray_handler = None
        shutdown_requested = threading.Event()
        restore_requested = threading.Event()
        icon_path = os.path.join(bundle_root, "ui", "assets", "images", "logo.png")
        
        def on_tray_restore():
            """Re-launch the Flet UI window when user clicks tray icon."""
            logging.info("[Tray] Restaurando janela da UI agendado...")
            restore_requested.set()
        
        def on_tray_quit():
            """Full shutdown requested from tray menu."""
            logging.info("[Tray] Encerramento solicitado via bandeja do sistema.")
            shutdown_requested.set()
        
        # Start single instance listener thread to catch restore requests
        def run_single_instance_listener():
            while not shutdown_requested.is_set():
                try:
                    _single_instance_socket.settimeout(1.0)
                    try:
                        conn, addr = _single_instance_socket.accept()
                    except socket.timeout:
                        continue
                    data = conn.recv(1024)
                    if data == b"restore_ui":
                        logging.info("[Launcher] Recebida solicitação de restauração de outra instância.")
                        restore_requested.set()
                    conn.close()
                except Exception as e:
                    if not shutdown_requested.is_set():
                        logging.error(f"[Launcher] Erro no listener de instância única: {e}")
                    time.sleep(0.5)

        t_listener = threading.Thread(target=run_single_instance_listener, name="SingleInstanceListenerThread", daemon=True)
        t_listener.start()

        def _launch_flet_ui():
            """Launch or re-launch the Flet UI window."""
            assets_dir = os.path.join(bundle_root, "ui", "assets")
            ui_module.restore_event = restore_requested
            ui_module.shutdown_event = shutdown_requested
            try:
                ft.app(target=ui_module.main, assets_dir=assets_dir)
            except RuntimeError as e:
                if "cannot schedule new futures after shutdown" not in str(e):
                    logging.error(f"[Flet Runtime] {e}")
            except Exception as e:
                logging.error(f"[UI Launcher] Falha ao iniciar ou encerrar interface: {e}")
        
        if UI_AVAILABLE:
            # Start the tray icon (runs on a daemon thread)
            if TRAY_AVAILABLE and os.path.exists(icon_path):
                tray_handler = TrayHandler(
                    icon_path=icon_path,
                    on_restore=on_tray_restore,
                    on_quit=on_tray_quit,
                )
                tray_started = tray_handler.start()
                if tray_started:
                    logging.info("[Launcher] System tray ativo. Fechar janela → minimiza para bandeja.")
                else:
                    logging.warning("[Launcher] System tray não disponível, fechar janela encerra o programa.")
            
            # Launch loop to keep it strictly on main thread
            while not shutdown_requested.is_set():
                logging.info("Iniciando UI (Thread Principal)...")
                _launch_flet_ui()
                
                # Flet fell through (window closed/crashed)
                if not shutdown_requested.is_set():
                    logging.info("[Launcher] Janela fechada. Aguardando wake/quit ou restauração...")
                    while not shutdown_requested.is_set():
                        if restore_requested.is_set():
                            restore_requested.clear()
                            break
                        time.sleep(0.1)
                else:
                    break
        else:
            p_cc.join()
        
        # Cleanup tray
        if tray_handler:
            tray_handler.stop()

    except KeyboardInterrupt:
        logging.info("Interrupção (Ctrl+C).")
    finally:
        logging.info("Iniciando desligamento gracioso (Graceful Shutdown)...")
        
        # 1. Avisar o CentralController e a AI_Process para finalizar serviços (ex: MonitorClient)
        try:
            controller_conn.send(("system", "shutdown", (), {}))
            ai_conn.send(("system", "shutdown", (), {}))
            logging.info("Sinal de desligamento enviado ao CentralController e AI_Process.")
            
            # Dar um breve momento para o MQTT enviar a mensagem de morte (QoS 1)
            p_cc.join(timeout=2.0)
        except Exception as e:
            logging.error(f"Erro ao desligar: {e}")
            
        logging.info("Encerrando filas e processos secundários...")
        try: queues['db'].put(None)
        except: pass
        
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(1)
                
        logging.info("Sistema encerrado.")

if __name__ == "__main__":
    # --- 1. Critical Protection for Multiprocessing (Windows/Frozen) ---
    # MUST be the absolute first thing called to prevent infinite process spawning in Flet/PyInstaller.
    multiprocessing.freeze_support()
    try:
        if multiprocessing.get_start_method(allow_none=True) != 'spawn':
            set_start_method('spawn', force=True)
    except Exception as e: 
        print(f"Error setting multiprocessing start method: {e}")
        pass
        
    # --- 2. Single-Instance Lock & UI Restore Trigger ---
    import socket
    _single_instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _single_instance_socket.bind(('127.0.0.1', 42123))
        _single_instance_socket.listen(5)
    except socket.error:
        try:
            # We are the second instance. Connect to the first instance to restore its UI.
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 42123))
            s.sendall(b"restore_ui")
            s.close()
        except Exception as e:
            print(f"Erro ao comunicar restauração: {e}")
        print("Outra instância da CARINA já está em execução! Solicitando restauração...")
        sys.exit(0)
        
    print(f"[LAUNCHER STARTING] Project Root: {project_root}")
    main()