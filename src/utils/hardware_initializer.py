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

# File: src/utils/hardware_initializer.py
# Author: Gabriel Moraes
# Date: August 10, 2026

import os
import logging
from typing import Any, Optional


class HardwareInitializer:
    """
    Utility component responsible for configuring Deep Learning hardware settings,
    PyTorch CPU thread bounds, PyInstaller PyTorch JIT compatibility shims,
    and CUDA GPU acceleration parameters.
    """

    @staticmethod
    def setup_environment(logging_func: Optional[Any] = None) -> None:
        """
        Configures CPU thread limits, PyTorch JIT shims for frozen builds,
        and TensorCore (TF32) precision settings.

        Args:
            logging_func (Optional[Any]): Optional logger callback function.
        """
        import torch

        # Bound CPU threads to prevent CPU contention during multi-process execution
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['MKL_NUM_THREADS'] = '1'
        os.environ['OPENBLAS_NUM_THREADS'] = '1'
        if hasattr(torch, 'set_num_threads'):
            torch.set_num_threads(1)

        # PyInstaller + TorchScript compatibility shim for frozen builds
        def _jit_script_shim(obj, *args, **kwargs):
            return obj

        if hasattr(torch, 'jit'):
            torch.jit.script = _jit_script_shim

        # Hardware Acceleration: TensorCore (TF32) precision optimization
        if hasattr(torch, 'backends') and hasattr(torch.backends, 'cuda'):
            torch.backends.cuda.matmul.allow_tf32 = True
            if hasattr(torch.backends, 'cudnn'):
                torch.backends.cudnn.allow_tf32 = True
        if hasattr(torch, 'set_float32_matmul_precision'):
            torch.set_float32_matmul_precision('high')

        log_msg = "⚡ Hardware Acceleration (TensorCores/TF32) enabled strictly (CPU Threads bounded to 1)."
        if logging_func:
            logging_func(log_msg, level="info")
        else:
            logging.info(log_msg)

    @staticmethod
    def detect_gpu(locale_manager: Optional[Any] = None, logging_func: Optional[Any] = None) -> str:
        """
        Detects CUDA GPU availability and returns device metadata string.

        Args:
            locale_manager (Optional[Any]): Optional LocaleManagerBackend instance for i18n logging.
            logging_func (Optional[Any]): Optional logger callback function.

        Returns:
            str: GPU device name or 'N/A' if GPU is unavailable.
        """
        import torch

        gpu_info = "N/A"
        if hasattr(torch, 'cuda') and torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_info = gpu_name
            msg = (
                locale_manager.get_string("main_ai.gpu_detected", default="✅ GPU Detected: {gpu_name}", gpu_name=gpu_name)
                if locale_manager and hasattr(locale_manager, "get_string")
                else f"✅ GPU Detected: {gpu_name}"
            )
            if logging_func:
                logging_func(msg, level="info")
            else:
                logging.info(msg)
        else:
            msg = (
                locale_manager.get_string("main_ai.no_gpu", default="⚠️ No GPU detected. Running on CPU.")
                if locale_manager and hasattr(locale_manager, "get_string")
                else "⚠️ No GPU detected. Running on CPU."
            )
            if logging_func:
                logging_func(msg, level="warning")
            else:
                logging.warning(msg)

        return gpu_info
