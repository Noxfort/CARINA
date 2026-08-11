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

# File: src/slm/device_manager.py
# Author: Gabriel Moraes
# Date: July 29, 2026

import logging
from typing import Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SLM_DEVICE] - %(levelname)s - %(message)s')

class SLMDeviceManager:
    """
    Handles hardware capability detection, CUDA availability checks, 
    free VRAM evaluation, and offload layer calculations for GGUF model execution.
    """

    @staticmethod
    def resolve_device_settings(device: str = None, gpu_layers: int = 16) -> Tuple[str, int]:
        """
        Determines the device execution setting ("gpu" vs "cpu") and number of GPU offload layers.
        Returns: (resolved_device_setting, resolved_gpu_layers)
        """
        if device in ("gpu", "cpu", "mixed"):
            device_setting = device
            resolved_layers = gpu_layers if device == "mixed" else (-1 if device == "gpu" else 0)
            logging.info(f"[SLMDeviceManager] Using explicit setting: {device_setting} (gpu_layers={resolved_layers})")

            if device_setting in ("gpu", "mixed"):
                try:
                    import torch
                    if not torch.cuda.is_available():
                        logging.warning("[SLMDeviceManager] GPU requested but CUDA is not available. Falling back to CPU.")
                        return "cpu", 0
                except Exception as e:
                    logging.warning(f"[SLMDeviceManager] Failed CUDA check: {e}. Falling back to CPU.")
                    return "cpu", 0
            return device_setting, resolved_layers

        # Automatic detection based on available VRAM
        try:
            import torch
            if torch.cuda.is_available():
                try:
                    free_vram, total_vram = torch.cuda.mem_get_info()
                    free_vram_gb = free_vram / (1024 ** 3)
                    logging.info(f"[SLMDeviceManager] CUDA detected. Free VRAM: {free_vram_gb:.2f} GB / Total: {total_vram / (1024 ** 3):.2f} GB")
                    if free_vram_gb >= 3.0:
                        logging.info("[SLMDeviceManager] Sufficient VRAM detected (>=3GB). Offloading to GPU.")
                        return "gpu", -1
                    else:
                        logging.info("[SLMDeviceManager] Low VRAM detected (<3GB). Running on CPU.")
                        return "cpu", 0
                except Exception as e:
                    logging.warning(f"[SLMDeviceManager] Error checking VRAM: {e}. Using GPU fallback.")
                    return "gpu", -1
            else:
                logging.info("[SLMDeviceManager] CUDA not available. Running on CPU.")
                return "cpu", 0
        except Exception as e:
            logging.warning(f"[SLMDeviceManager] Torch check failed: {e}. Running on CPU.")
            return "cpu", 0
