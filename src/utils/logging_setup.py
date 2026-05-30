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

# File: src/utils/logging_setup.py
# Author: Gabriel Moraes
# Date: September 17, 2025

"""
Configures a logging system that writes to the console and to a file
in real-time, with support for universal characters (UTF-8) and different log levels
for each output.
"""
import logging
import sys
import os

def setup_logging(log_dir: str):
    """
    Configures logging for the console and log file using UTF-8.
    The log file captures everything (DEBUG), while the console is cleaner (INFO).
    """
    log_file_path = os.path.join(log_dir, 'console_output.log')
    
    log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
    
    root_logger = logging.getLogger()
    # --- FIX (Part 1): Sets the lowest level in the main logger ---
    # This allows it to pass all messages to the handlers, which will do the filtering.
    root_logger.setLevel(logging.DEBUG)
    
    # Cleans up existing handlers to avoid log duplication
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    class FletAsyncShutdownFilter(logging.Filter):
        """Filtra mensagens de erro inofensivas geradas pelo asyncio no shutdown da UI Flet."""
        def filter(self, record):
            if record.exc_info:
                _, exc_value, _ = record.exc_info
                if exc_value and "cannot schedule new futures" in str(exc_value):
                    return False
            if isinstance(record.msg, str) and "cannot schedule new futures" in record.msg:
                return False
            return True

    # --- FIX (Part 2): Configure FileHandler to record EVERYTHING ---
    # 1. Handler to save the logs to a file, specifying UTF-8 encoding
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG) # Writes everything from DEBUG to CRITICAL to the file.
    file_handler.addFilter(FletAsyncShutdownFilter())
    root_logger.addHandler(file_handler)

    # --- FIX (Part 3): Configure ConsoleHandler to be less verbose ---
    # 2. Handler to show logs in console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO) # Shows only from INFO to CRITICAL on the console.
    console_handler.addFilter(FletAsyncShutdownFilter())
    root_logger.addHandler(console_handler)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        # The exception will be caught by both handlers
        root_logger.critical("Exceção não tratada:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    
    # This message will only appear in the console, as it is INFO.
    logging.info("Sistema de Logging (Modo Tempo Real, UTF-8) configurado.")
    # This message will only appear in the .txt file, as it is DEBUG.
    logging.debug("Logger configurado. FileHandler=DEBUG, StreamHandler=INFO.")
    
    # --- SILENCE VERBOSE THIRD-PARTY MODULES ---
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("websockets.server").setLevel(logging.WARNING)
    logging.getLogger("websockets.client").setLevel(logging.WARNING)