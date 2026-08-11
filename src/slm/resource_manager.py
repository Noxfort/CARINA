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

# File: src/slm/resource_manager.py
# Author: Gabriel Moraes
# Date: July 29, 2026

import torch
import logging
import gc
from typing import Optional, Union
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SLM_RESOURCE] - %(levelname)s - %(message)s')

class ResourceManager:
    """
    Resource manager allowing switching between GPU and CPU for neural models,
    with dynamic RAM offload capabilities when GPU VRAM is insufficient.
    """
    
    def __init__(self, model_path: str, use_gpu: bool = False, offload_to_cpu: bool = True):
        self.model_path = model_path
        self.use_gpu = False  # Force CPU use
        self.offload_to_cpu = offload_to_cpu
        self.device = "cpu"  # Force device as CPU
        self.model = None
        self.tokenizer = None
        
        logging.info(f"[ResourceManager] Initializing ResourceManager on device: {self.device} (GPU disabled)")
        
    def load_resources(self) -> bool:
        """
        Loads model and tokenizer applying memory management strategies.
        Returns True if successful, False otherwise.
        """
        try:
            logging.info("[ResourceManager] Loading Tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            
            logging.info(f"[ResourceManager] Loading Model (FP32) exclusively on CPU: {self.device}")
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float32,
                device_map={"": "cpu"},
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self.model.eval()
            logging.info("[ResourceManager] Model loaded successfully exclusively on CPU.")
            return True
            
        except Exception as e:
            logging.error(f"[ResourceManager] Failed to load resources: {e}", exc_info=True)
            return False
    
    def move_model_to_device(self, target_device: str) -> bool:
        """
        Moves the model to a specific device (GPU/CPU).
        Useful for dynamic offload during heavy inference.
        """
        if not self.model:
            logging.error("[ResourceManager] Model not loaded in memory.")
            return False
            
        try:
            if target_device == "cuda" and not torch.cuda.is_available():
                logging.warning("[ResourceManager] CUDA not available. Keeping model on CPU.")
                return False
                
            logging.info(f"[ResourceManager] Moving model from {self.model.device} to {target_device}")
            
            if self.model.device.type == "cuda":
                self._clear_gpu_cache()
                
            self.model = self.model.to(target_device)
            self.device = target_device
            
            if target_device == "cpu":
                self._clear_gpu_cache()
                
            logging.info(f"[ResourceManager] Model moved successfully to {target_device}")
            return True
            
        except Exception as e:
            logging.error(f"[ResourceManager] Failed to move model to target device: {e}", exc_info=True)
            return False
    
    def _clear_gpu_cache(self):
        """Frees GPU cache memory."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
    
    def get_model(self) -> Optional[AutoModelForCausalLM]:
        """Returns the loaded model instance."""
        return self.model
    
    def get_tokenizer(self) -> Optional[AutoTokenizer]:
        """Returns the loaded tokenizer instance."""
        return self.tokenizer
    
    def get_device(self) -> str:
        """Returns the current execution device identifier."""
        return self.device
    
    def cleanup(self):
        """Frees all allocated GPU and RAM resources."""
        if self.model:
            del self.model
            self.model = None
            
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
            
        self._clear_gpu_cache()
        gc.collect()
        
        logging.info("[ResourceManager] All SLM resources released successfully.")
