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

# File: src/xai/resource_manager.py
# Author: Gabriel Moraes
# Date: April 25, 2026

import torch
import logging
import gc
from typing import Optional, Union
from transformers import AutoModelForCausalLM, AutoTokenizer

class ResourceManager:
    """
    Gerenciador de recursos que permite alternar entre GPU e CPU para modelos,
    com capacidade de offload para memória RAM quando a VRAM não for suficiente.
    """
    
    def __init__(self, model_path: str, use_gpu: bool = False, offload_to_cpu: bool = True):
        # Forçar uso exclusivo da CPU, ignorando GPU
        self.model_path = model_path
        self.use_gpu = False  # Forçar uso da CPU
        self.offload_to_cpu = offload_to_cpu
        self.device = "cpu"  # Forçar dispositivo como CPU
        self.model = None
        self.tokenizer = None
        
        logging.info(f"Inicializando ResourceManager com dispositivo: {self.device} (GPU desativada)")
        
    def load_resources(self) -> bool:
        """
        Carrega o modelo e tokenizer com estratégias de gerenciamento de memória.
        Retorna True se bem-sucedido, False caso contrário.
        """
        try:
            # Forçar uso exclusivo da CPU, ignorando completamente a GPU
            logging.info("Carregando Tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            
            logging.info(f"Carregando Modelo (FP32) exclusivamente na CPU: {self.device}")
            
            # Carregar na CPU com otimizações para memória limitada
            # Usar FP32 em vez de FP16 para maior compatibilidade com CPU
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float32,  # Usar FP32 para CPU
                device_map={"": "cpu"},  # Forçar carregamento na CPU
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self.model.eval()
            logging.info("Modelo carregado com sucesso exclusivamente na CPU.")
            return True
            
        except Exception as e:
            logging.error(f"Falha ao carregar recursos: {e}", exc_info=True)
            return False
    
    # Método removido: _check_vram_availability
    # Não é mais necessário já que estamos usando apenas CPU
    
    def move_model_to_device(self, target_device: str) -> bool:
        """
        Move o modelo para um dispositivo específico (GPU/CPU).
        Útil para offload dinâmico durante a execução.
        """
        if not self.model:
            logging.error("Modelo não carregado.")
            return False
            
        try:
            if target_device == "cuda" and not torch.cuda.is_available():
                logging.warning("CUDA não disponível. Mantendo modelo na CPU.")
                return False
                
            logging.info(f"Movendo modelo de {self.model.device} para {target_device}")
            
            # Liberar memória antes da mudança
            if self.model.device.type == "cuda":
                self._clear_gpu_cache()
                
            # Mover modelo
            self.model = self.model.to(target_device)
            self.device = target_device
            
            # Liberar memória após a mudança
            if target_device == "cpu":
                self._clear_gpu_cache()
                
            logging.info(f"Modelo movido com sucesso para {target_device}")
            return True
            
        except Exception as e:
            logging.error(f"Falha ao mover modelo: {e}", exc_info=True)
            return False
    
    def _clear_gpu_cache(self):
        """Libera cache da GPU."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
    
    def get_model(self) -> Optional[AutoModelForCausalLM]:
        """Retorna o modelo carregado."""
        return self.model
    
    def get_tokenizer(self) -> Optional[AutoTokenizer]:
        """Retorna o tokenizer carregado."""
        return self.tokenizer
    
    def get_device(self) -> str:
        """Retorna o dispositivo atual."""
        return self.device
    
    def cleanup(self):
        """Libera todos os recursos."""
        if self.model:
            del self.model
            self.model = None
            
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
            
        self._clear_gpu_cache()
        gc.collect()
        
        logging.info("Recursos liberados.")