import os
import sys
import time
import platform
import subprocess

try:
    import psutil
except ImportError:
    print("Instalando a biblioteca 'psutil'...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_gpu_info():
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            encoding='utf-8'
        )
        lines = result.strip().split('\n')
        vram_used = sum(int(line.split(',')[0].strip()) for line in lines)
        vram_total = sum(int(line.split(',')[1].strip()) for line in lines)
        return {"vram_used_mb": vram_used, "vram_total_mb": vram_total, "has_gpu": True}
    except Exception:
        return {"vram_used_mb": 0, "vram_total_mb": 0, "has_gpu": False}

def run_benchmark(num_junctions, duration=60):
    print("\n==================================================")
    print("       INICIANDO BENCHMARK CARINA CORE")
    print(f"       Mockando: {num_junctions} Cruzamentos | Tempo: {duration}s")
    print("==================================================")
    
    os_info = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
    
    mock_script = os.path.join(os.path.dirname(__file__), "mock_junctions.py")
    if not os.path.exists(mock_script):
        print(f"Erro: '{mock_script}' não encontrado.")
        return
        
    print(f"-> Passo 1/2: Levantando Mock de {num_junctions} cruzamentos em background...")
    mock_process = subprocess.Popen([sys.executable, mock_script, str(num_junctions)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(2) # Dar tempo para portas abrirem
    
    core_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "carina.py"))
    print("-> Passo 2/2: Iniciando a inteligência central (CARINA CORE)...")
    
    env = os.environ.copy()
    env["CARINA_TEST_MODE"] = "1"
    
    core_process = subprocess.Popen([sys.executable, core_script], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    peak_cpu_percent = 0.0
    peak_ram_mb = 0.0
    peak_vram_mb = 0.0
    
    start_time = time.time()
    
    try:
        core_ps = psutil.Process(core_process.pid)
        print("\nMonitorando recursos de IA (SLM, Dashboards, Workers)...\n")
        
        while time.time() - start_time < duration:
            if core_process.poll() is not None:
                print("\nO processo do CARINA_CORE terminou prematuramente.")
                break
                
            total_cpu = 0.0
            total_ram = 0
            
            children = core_ps.children(recursive=True)
            for p in [core_ps] + children:
                try:
                    total_cpu += p.cpu_percent(interval=None)
                    total_ram += p.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            
            if total_cpu > peak_cpu_percent:
                peak_cpu_percent = total_cpu
                
            ram_mb = total_ram / (1024 * 1024)
            if ram_mb > peak_ram_mb:
                peak_ram_mb = ram_mb
                
            gpu_info = get_gpu_info()
            if gpu_info["has_gpu"] and gpu_info["vram_used_mb"] > peak_vram_mb:
                peak_vram_mb = gpu_info["vram_used_mb"]
                
            time.sleep(1)
            sys.stdout.write(f"\rRestante: {int(duration - (time.time() - start_time))}s | CPU Pico: {peak_cpu_percent:.1f}% | RAM Pico: {peak_ram_mb:.0f} MB")
            sys.stdout.flush()
            
    except KeyboardInterrupt:
        print("\nBenchmark interrompido pelo usuário.")
    finally:
        print("\n\nEncerrando Motores Neurais, Interfaces e Mocks (Hardkill)...")
        # Hardkill em todos os subprocessos para garantir que a UI não fique aberta "zumbi"
        for proc in [core_process, mock_process]:
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    child.kill()
            except psutil.NoSuchProcess:
                pass
            proc.kill()

    folder_size_mb = get_folder_size(os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) / (1024 * 1024)
    cores_utilizados = max(1, int(peak_cpu_percent / 100) + 1)
    
    gerar_relatorio(os_info, cores_utilizados, peak_ram_mb, peak_vram_mb, folder_size_mb, peak_cpu_percent, num_junctions)

def format_gb(mb):
    if mb < 1024:
        return f"{mb:.0f} MB"
    return f"{mb / 1024:.2f} GB"

def get_next_tier(value, tiers):
    for t in tiers:
        if value <= t:
            return t
    return int(value) + (1 if value % 1 > 0 else 0) # Se passar do máximo tabelado, apenas arredonda para cima

def gerar_relatorio(os_info, base_cores, base_ram_mb, base_vram_mb, folder_size_mb, peak_cpu_percent, num_junctions):
    os_ram_reserve_mb = 2048 
    
    # =========================================================
    # SIMULAÇÃO DE PICO MÁXIMO (WORST-CASE STRESS TEST)
    # Garante que o hardware recomendado suportará o sistema 
    # utilizando 100% da CARINA (Infernência contínua, XAI, 
    # Watchdog e tráfego intenso em todos os semáforos ao mesmo tempo).
    # =========================================================
    stress_ram_factor = 2.5  # O pico de tráfego inunda filas MQTT e alocações de IA
    stress_cpu_factor = 2.0  # Múltiplas threads do Motor Simbólico trabalhando sem parar
    stress_vram_factor = 1.8 # Aceleradores trabalhando em capacidade máxima
    
    # Cálculos brutos convertidos para GB
    ram_raw_gb = max(4096, (base_ram_mb * stress_ram_factor) + os_ram_reserve_mb + 2048) / 1024.0
    cpu_cores_raw = int(base_cores * stress_cpu_factor) + 2
    disk_raw_gb = (folder_size_mb + (10.0 * num_junctions) + 5120) / 1024.0
    
    # Arredondamento para "Padrões de Mercado" (2, 4, 8, 16, 32...)
    ram_recomendada = get_next_tier(ram_raw_gb, [4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 256, 512])
    cpu_cores_recomendado = get_next_tier(cpu_cores_raw, [2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 128])
    disk_recomendado = get_next_tier(disk_raw_gb, [16, 32, 64, 128, 256, 512, 1024, 2048])
    
    if base_vram_mb > 0:
        vram_raw_gb = (base_vram_mb * stress_vram_factor) / 1024.0
        vram_recomendada = get_next_tier(vram_raw_gb, [2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 80])
    else:
        vram_recomendada = 0

    if vram_recomendada == 0:
        if num_junctions <= 50:
            vram_text = "Integrada (Onboard) é suficiente"
        elif num_junctions <= 300:
            vram_text = "Placa de vídeo dedicada (Mínimo 4 GB VRAM) recomendada para processamento local"
        elif num_junctions <= 1500:
            vram_text = "Placa de vídeo nível Enterprise exigida para essa escala de IA"
        else:
            vram_text = "Cluster CUDA multi-GPU (Ex: NVIDIA A100 / H100) estritamente obrigatório"
    else:
        vram_text = f"Dedicada com {vram_recomendada} GB VRAM"

    if num_junctions <= 100:
        disk_text = f"(HDD Suportado, SSD Recomendado)"
    else:
        disk_text = f"(SSD Obrigatório para fluxo massivo de dados)"

    if num_junctions <= 50:
        porte = "Porte: Cidade Pequena"
    elif num_junctions <= 300:
        porte = "Porte: Cidade Média"
    elif num_junctions <= 1500:
        porte = "Porte: Cidade Grande"
    else:
        porte = "Porte: Metrópole"

    report = f"""==================================================
RELATÓRIO DE REQUISITOS DE HARDWARE - CARINA CORE
==================================================

1. INFORMAÇÕES TÉCNICAS GERAIS
--------------------------------------------------
Sistema Operacional : Suporta {os_info} ou superior.
Arquitetura         : Exige 64-bit obrigatoriamente.
Conexão c/ Internet : Requer banda larga (Estimativa: {max(1, num_junctions // 100)} Mbps).
Dependências        : Python 3.8+, bibliotecas do requirements.txt.

2. MÉTRICAS BRUTAS OBTIDAS (TESTE COM {num_junctions} SEMÁFOROS MOCK)
--------------------------------------------------
- RAM Utilizada (S/ SO): {base_ram_mb:.1f} MB
- VRAM (GPU) Utilizada: {base_vram_mb:.1f} MB
- Uso Máximo de CPU (Threads): {peak_cpu_percent:.1f}%

3. REQUISITOS DE HARDWARE RECOMENDADOS ({porte})
--------------------------------------------------
Processador (CPU)   : {cpu_cores_recomendado} Núcleos reais (ou threads lógicas)
Memória (RAM)       : {ram_recomendada} GB (Já inclui folga e uso do sistema operacional)
Armazenamento       : {disk_recomendado} GB {disk_text}
Placa de Vídeo (GPU): {vram_text}

==================================================
"""

    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "benchmark.txt"))
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\nRelatório focado gerado com sucesso em: {report_path}")

if __name__ == "__main__":
    print("==================================================")
    print("        CARINA - CONFIGURAÇÃO DE BENCHMARK        ")
    print("==================================================")
    
    try:
        user_input = input("Quantos semáforos (cruzamentos) deseja simular no teste base? [Padrão: 20]: ").strip()
        num_junctions = int(user_input) if user_input else 20
        
        duracao_teste = 60 # Tempo tabelado fixado
    except ValueError:
        print("Entrada inválida. Usando valores padrão (20 cruzamentos, 60 segundos).")
        num_junctions = 20
        duracao_teste = 60
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(0)

    run_benchmark(num_junctions, duracao_teste)
