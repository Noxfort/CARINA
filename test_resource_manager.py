#!/usr/bin/env python3
# Script de teste para o ResourceManager

import os
import sys
import torch
import logging

# Adicionar o diretório src ao path para importar os módulos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)

from xai.resource_manager import ResourceManager

def test_resource_manager():
    """Testa o ResourceManager com uso exclusivo da CPU."""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Caminho para o modelo Qwen3-1.7B
    model_path = os.path.join(BASE_DIR, "Model_Vault", "qwen3_1.7B")
    
    if not os.path.exists(model_path):
        print(f"Modelo não encontrado em: {model_path}")
        print("Por favor, verifique se o modelo está na pasta Model_Vault/qwen3_1.7B")
        return False
    
    print("=== Teste: Carregamento exclusivo na CPU ===")
    try:
        # Forçar uso exclusivo da CPU
        rm_cpu = ResourceManager(model_path, use_gpu=False, offload_to_cpu=True)
        success = rm_cpu.load_resources()
        if success:
            print(f"✓ Modelo carregado com sucesso na CPU ({rm_cpu.get_device()})")
            print(f"✓ Verificação: CUDA disponível = {torch.cuda.is_available()}")
            print(f"✓ Verificação: Dispositivo do modelo = {next(rm_cpu.get_model().parameters()).device}")
            
            # Verificar que o modelo está realmente na CPU
            model_device = next(rm_cpu.get_model().parameters()).device
            if model_device.type == "cpu":
                print("✓ Confirmação: Modelo está realmente na CPU")
            else:
                print(f"✗ Erro: Modelo não está na CPU (está em {model_device})")
            
            rm_cpu.cleanup()
        else:
            print("✗ Falha ao carregar modelo na CPU")
    except Exception as e:
        print(f"✗ Erro ao carregar modelo na CPU: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Teste: Tentativa de forçar uso da GPU (deve ser ignorada) ===")
    try:
        # Tentar forçar uso da GPU (deve ser ignorado)
        rm_gpu = ResourceManager(model_path, use_gpu=True, offload_to_cpu=True)
        success = rm_gpu.load_resources()
        if success:
            print(f"✓ Modelo carregado com sucesso ({rm_gpu.get_device()})")
            
            # Verificar que o modelo está realmente na CPU mesmo com use_gpu=True
            model_device = next(rm_gpu.get_model().parameters()).device
            if model_device.type == "cpu":
                print("✓ Confirmação: Modelo está na CPU mesmo com use_gpu=True")
            else:
                print(f"✗ Erro: Modelo não está na CPU (está em {model_device})")
            
            rm_gpu.cleanup()
        else:
            print("✗ Falha ao carregar modelo")
    except Exception as e:
        print(f"✗ Erro ao carregar modelo: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Testes concluídos ===")
    return True

if __name__ == "__main__":
    test_resource_manager()