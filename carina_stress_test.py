import multiprocessing as mp
import time
import os
import psutil
import math

try:
    import torch
    HAS_GPU = torch.cuda.is_available()
except ImportError:
    HAS_GPU = False

# ==============================================================================
# WORKERS SIMULADOS (Cargas Artificiais)
# ==============================================================================

def cpu_burner(target_usage):
    """Simula carga de CPU fazendo matemática inútil"""
    start = time.time()
    while time.time() - start < target_usage:
        _ = math.sqrt(math.pi ** 2.5)
    time.sleep(1 - target_usage)

def xai_worker():
    """Simula o Worker do LLM (Qwen3 1.7B) - Alta VRAM, CPU leve, RAM moderada"""
    # Simula consumo de RAM (~2GB)
    _dummy_ram = bytearray(2 * 1024 * 1024 * 1024) 
    
    _dummy_vram = None
    if HAS_GPU:
        # Tenta alocar ~5.5GB de VRAM
        try:
            _dummy_vram = torch.empty((1024, 1024, 1400), dtype=torch.float32, device='cuda')
        except Exception:
            pass
            
    while True:
        cpu_burner(0.15) # 15% CPU

def ai_process():
    """Simula o Motor RL (PPO-TCN + PAE) - CPU Pesada, VRAM moderada"""
    _dummy_ram = bytearray(3 * 1024 * 1024 * 1024) # 3GB RAM
    
    _dummy_vram = None
    if HAS_GPU:
        # Tenta alocar ~2.5GB de VRAM
        try:
            _dummy_vram = torch.empty((1024, 1024, 600), dtype=torch.float32, device='cuda')
        except Exception:
            pass

    while True:
        cpu_burner(0.85) # 85% CPU

def guardian_worker():
    """Simula a Camada de Segurança - CPU Moderada, VRAM Baixa"""
    _dummy_ram = bytearray(2 * 1024 * 1024 * 1024) # 2GB RAM
    
    _dummy_vram = None
    if HAS_GPU:
        try:
            _dummy_vram = torch.empty((1024, 1024, 300), dtype=torch.float32, device='cuda')
        except Exception:
            pass

    while True:
        cpu_burner(0.70) # 70% CPU

def central_controller():
    """Simula Ingestão gRPC (HFTLink) - CPU Estourada, RAM Leve"""
    _dummy_ram = bytearray(1 * 1024 * 1024 * 1024) # 1GB RAM
    while True:
        cpu_burner(0.95) # 95% CPU

def database_worker():
    """Simula Inserções SQL / Pandas - RAM Alta, CPU Média"""
    _dummy_ram = bytearray(4 * 1024 * 1024 * 1024) # 4GB RAM
    while True:
        cpu_burner(0.50) # 50% CPU

def sds_worker():
    """Simula WebSockets UI (SDS) - Baixo uso geral"""
    _dummy_ram = bytearray(500 * 1024 * 1024) # 500MB RAM
    while True:
        cpu_burner(0.20) # 20% CPU

# ==============================================================================
# MONITORAMENTO E TABELA
# ==============================================================================

def get_gpu_vram():
    if not HAS_GPU:
        return "GPU não detectada"
    allocated = torch.cuda.memory_allocated() / (1024**3)
    reserved = torch.cuda.memory_reserved() / (1024**3)
    return f"{allocated:.1f}GB Aloc / {reserved:.1f}GB Reser"

def monitor_loop(processes):
    print("Iniciando simulação de carga máxima do ecossistema CARINA...")
    time.sleep(3) # Tempo para os workers alocarem memória
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("="*80)
            print(f"🚦 CARINA MAX CAPACITY SIMULATOR")
            print(f"GPU Status: {get_gpu_vram()}")
            print("="*80)
            print(f"{'PROCESSO':<20} | {'PID':<8} | {'CPU (%)':<8} | {'RAM (MB)':<10}")
            print("-" * 80)
            
            total_cpu = 0
            total_ram = 0
            
            for name, proc in processes.items():
                if proc.is_alive():
                    try:
                        p = psutil.Process(proc.pid)
                        cpu = p.cpu_percent(interval=0.1) / psutil.cpu_count()
                        ram_mb = p.memory_info().rss / (1024 * 1024)
                        
                        total_cpu += cpu
                        total_ram += ram_mb
                        
                        print(f"{name:<20} | {proc.pid:<8} | {cpu:>6.1f} % | {ram_mb:>8.1f} MB")
                    except psutil.NoSuchProcess:
                        print(f"{name:<20} | {proc.pid:<8} | DEAD   | DEAD")
            
            print("-" * 80)
            print(f"{'TOTAL ESTIMADO':<20} | {'-':<8} | {total_cpu:>6.1f} % | {total_ram:>8.1f} MB")
            print("="*80)
            print("Pressione CTRL+C para encerrar o Graceful Shutdown...")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nEncerrando processos de forma segura...")
        for name, proc in processes.items():
            proc.terminate()
            proc.join()
        print("Simulação encerrada.")

# ==============================================================================
# LAUNCHER PRINCIPAL
# ==============================================================================

if __name__ == '__main__':
    # Proteção nativa para Multiprocessing no Windows
    mp.freeze_support()
    
    # Mapeamento dos processos arquiteturais
    architecture = {
        "XAI_Worker": xai_worker,
        "AI_Process": ai_process,
        "GuardianWorker": guardian_worker,
        "CentralController": central_controller,
        "Database_SAS": database_worker,
        "Dashboard_SDS": sds_worker
    }
    
    active_processes = {}
    
    # Spawn dos processos contornando o GIL
    for name, func in architecture.items():
        p = mp.Process(target=func, name=name)
        p.start()
        active_processes[name] = p
        
    # Inicia a tabela do painel de monitoramento
    monitor_loop(active_processes)