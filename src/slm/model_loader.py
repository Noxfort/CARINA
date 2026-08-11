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

# File: src/slm/model_loader.py
# Author: Gabriel Moraes
# Date: July 29, 2026

import os
import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SLM_LOADER] - %(levelname)s - %(message)s')

class SLMModelLoader:
    """
    Encapsulates loading and initialization of GGUF model files using llama-cpp-python,
    handling GPU acceleration and automatic CPU fallback.
    """

    @staticmethod
    def load_model(model_path: str, device_setting: str, gpu_layers: int) -> Any:
        """
        Loads the GGUF model file. Raises FileNotFoundError or RuntimeError if loading fails.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model Vault file not found at: {model_path}")

        from llama_cpp import Llama

        n_gpu_layers = gpu_layers if device_setting != "cpu" else 0
        model = None

        if n_gpu_layers != 0:
            try:
                logging.info(f"[SLMModelLoader] Loading GGUF model with GPU acceleration (gpu_layers={n_gpu_layers}): {model_path}")
                model = Llama(
                    model_path=model_path,
                    n_ctx=8192,
                    n_gpu_layers=n_gpu_layers,
                    verbose=False
                )
                logging.info("[SLMModelLoader] GGUF model loaded successfully on GPU.")
                return model
            except Exception as e:
                logging.warning(f"[SLMModelLoader] GPU load failed (gpu_layers={n_gpu_layers}): {e}. Attempting CPU fallback...")

        if model is None:
            try:
                logging.info(f"[SLMModelLoader] Loading GGUF model on CPU (gpu_layers=0): {model_path}")
                model = Llama(
                    model_path=model_path,
                    n_ctx=8192,
                    n_gpu_layers=0,
                    verbose=False
                )
                logging.info("[SLMModelLoader] GGUF model loaded successfully on CPU.")
                return model
            except ImportError:
                raise RuntimeError("llama-cpp-python is not installed. Please install it to use GGUF models.")
            except Exception as e:
                logging.error(f"[SLMModelLoader] CPU model loading failed: {e}")
                raise RuntimeError(f"Failed to load model resources: {e}")
