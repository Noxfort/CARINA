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

# File: src/utils/hardware_logging_setup.py
# Author: Gabriel Moraes
# Date: August 10, 2026

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Tuple

from src.utils.paths import get_base_output_dir
from src.utils.logging_setup import gzip_namer, gzip_rotator


def setup_hardware_loggers() -> Tuple[logging.Logger, logging.Logger]:
    """
    Initializes dedicated hardware connection loggers and command loggers
    with rotating file handlers and GZIP compression.

    Returns:
        Tuple[logging.Logger, logging.Logger]: (logger, cmd_logger)
    """
    log_dir = os.path.join(get_base_output_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # 1. Setup dedicated hardware connections log file
    hw_log_path = os.path.abspath(os.path.join(log_dir, "hardware_connections.log"))
    logger = logging.getLogger("src.controller.connection_manager")

    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == hw_log_path for h in logger.handlers):
        hw_handler = RotatingFileHandler(
            hw_log_path, maxBytes=10 * 1024 * 1024, backupCount=100, encoding='utf-8'
        )
        hw_handler.namer = gzip_namer
        hw_handler.rotator = gzip_rotator
        hw_handler.setFormatter(logging.Formatter('%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s'))
        logger.addHandler(hw_handler)
    else:
        hw_handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler) and h.baseFilename == hw_log_path)

    # 2. Setup dedicated commands logger
    cmd_log_path = os.path.abspath(os.path.join(log_dir, "commands.log"))
    cmd_logger = logging.getLogger("carina_commands")
    cmd_logger.setLevel(logging.INFO)
    cmd_logger.propagate = False

    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == cmd_log_path for h in cmd_logger.handlers):
        cmd_handler = RotatingFileHandler(
            cmd_log_path, maxBytes=10 * 1024 * 1024, backupCount=100, encoding='utf-8'
        )
        cmd_handler.namer = gzip_namer
        cmd_handler.rotator = gzip_rotator
        cmd_handler.setFormatter(logging.Formatter('%(asctime)s - [CARINA_CORE] - %(message)s'))
        cmd_logger.addHandler(cmd_handler)

    # 3. Bind hardware handlers to driver modules
    try:
        import src.drivers.traffic_light_driver
        if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == hw_log_path for h in src.drivers.traffic_light_driver.logger.handlers):
            src.drivers.traffic_light_driver.logger.addHandler(hw_handler)
        src.drivers.traffic_light_driver.cmd_logger = cmd_logger
    except Exception as e:
        logger.warning(f"[HARDWARE_LOGGING] Warning binding handlers to traffic_light_driver: {e}")

    try:
        import src.drivers.driver_factory
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == hw_log_path for h in src.drivers.driver_factory.logger.handlers):
            src.drivers.driver_factory.logger.addHandler(hw_handler)
    except Exception as e:
        logger.warning(f"[HARDWARE_LOGGING] Warning binding handlers to driver_factory: {e}")

    return logger, cmd_logger
