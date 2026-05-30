# CARINA Hardware Benchmark & Recommendation Generator
# Measures real VRAM, RAM, CPU, GPU usage per component
# Generates a hardware requirements report

import os
import sys
import time
import json
import gc
import psutil
import platform
import multiprocessing as mp
from datetime import datetime

# --- Path Setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except ImportError:
    torch = None
    HAS_CUDA = False

# ============================================================================
# UTILITIES
# ============================================================================

def get_ram_mb():
    """Current process RAM in MB."""
    return psutil.Process().memory_info().rss / (1024 ** 2)

def get_vram_mb():
    """Current CUDA VRAM allocated in MB."""
    if not HAS_CUDA:
        return 0.0
    return torch.cuda.memory_allocated() / (1024 ** 2)

def get_vram_reserved_mb():
    """Current CUDA VRAM reserved in MB."""
    if not HAS_CUDA:
        return 0.0
    return torch.cuda.memory_reserved() / (1024 ** 2)

def get_gpu_name():
    if not HAS_CUDA:
        return "N/A (CPU only)"
    return torch.cuda.get_device_name(0)

def get_total_vram_mb():
    if not HAS_CUDA:
        return 0
    return torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)

def measure_cpu_burst(func, duration=3.0):
    """Measures average CPU% of current process during func execution."""
    proc = psutil.Process()
    proc.cpu_percent()  # reset
    start = time.time()
    func()
    elapsed = time.time() - start
    cpu = proc.cpu_percent() / psutil.cpu_count()
    return cpu, elapsed

def clear_gpu():
    if HAS_CUDA:
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.synchronize()

# ============================================================================
# COMPONENT BENCHMARKS
# ============================================================================

class BenchmarkResult:
    def __init__(self, name):
        self.name = name
        self.ram_before = 0.0
        self.ram_after = 0.0
        self.vram_before = 0.0
        self.vram_after = 0.0
        self.cpu_percent = 0.0
        self.load_time = 0.0
        self.inference_time = 0.0
        self.notes = ""
        self.success = True
        self.error = ""

    @property
    def ram_delta(self):
        return max(0, self.ram_after - self.ram_before)

    @property
    def vram_delta(self):
        return max(0, self.vram_after - self.vram_before)

    def to_dict(self):
        return {
            "component": self.name,
            "ram_mb": round(self.ram_delta, 1),
            "vram_mb": round(self.vram_delta, 1),
            "cpu_percent": round(self.cpu_percent, 1),
            "load_time_s": round(self.load_time, 2),
            "inference_time_s": round(self.inference_time, 2),
            "success": self.success,
            "notes": self.notes,
            "error": self.error,
        }


def bench_actor_critic_tcn(device):
    """Benchmark PPO Actor-Critic TCN (LocalAgent network)."""
    r = BenchmarkResult("ActorCritic-TCN (PPO LocalAgent)")
    try:
        from models.actor_critic_tcn import ActorCriticNet

        n_obs, n_actions, hidden = 12, 4, 128
        seq_len, batch = 8, 64

        clear_gpu()
        r.ram_before = get_ram_mb()
        r.vram_before = get_vram_mb()
        t0 = time.time()

        net = ActorCriticNet(n_obs, n_actions, hidden_size=hidden).to(device)
        net.eval()

        r.load_time = time.time() - t0
        r.ram_after = get_ram_mb()
        r.vram_after = get_vram_mb()

        # Inference benchmark
        dummy = torch.randn(batch, seq_len, n_obs, device=device)
        times = []
        for _ in range(50):
            t1 = time.time()
            with torch.no_grad():
                net(dummy)
            if HAS_CUDA:
                torch.cuda.synchronize()
            times.append(time.time() - t1)
        r.inference_time = sum(times) / len(times)

        params = sum(p.numel() for p in net.parameters())
        r.notes = f"{params:,} params | batch={batch} seq={seq_len}"

        del net, dummy
        clear_gpu()
    except Exception as e:
        r.success = False
        r.error = str(e)
    return r


def bench_dueling_dqn(device):
    """Benchmark Dueling DQN-TCN (GuardianAgent network)."""
    r = BenchmarkResult("D3QN-TCN (Guardian)")
    try:
        from models.d3qn_tcn import D3QN_TCN

        n_obs, n_actions, pae_latent, hidden = 2, 2, 16, 64
        seq_len, batch = 8, 128

        clear_gpu()
        r.ram_before = get_ram_mb()
        r.vram_before = get_vram_mb()
        t0 = time.time()

        policy = D3QN_TCN(n_obs, n_actions, pae_latent, hidden).to(device)
        target = D3QN_TCN(n_obs, n_actions, pae_latent, hidden).to(device)
        target.load_state_dict(policy.state_dict())
        policy.eval()
        target.eval()

        r.load_time = time.time() - t0
        r.ram_after = get_ram_mb()
        r.vram_after = get_vram_mb()

        dummy_seq = torch.randn(batch, seq_len, n_obs, device=device)
        dummy_pae = torch.randn(batch, pae_latent, device=device)
        times = []
        for _ in range(50):
            t1 = time.time()
            with torch.no_grad():
                policy(dummy_seq, dummy_pae)
            if HAS_CUDA:
                torch.cuda.synchronize()
            times.append(time.time() - t1)
        r.inference_time = sum(times) / len(times)

        params = sum(p.numel() for p in policy.parameters()) + sum(p.numel() for p in target.parameters())
        r.notes = f"{params:,} params (policy+target) | batch={batch}"

        del policy, target, dummy_seq, dummy_pae
        clear_gpu()
    except Exception as e:
        r.success = False
        r.error = str(e)
    return r


def bench_pae(device):
    """Benchmark Predictive Autoencoder."""
    r = BenchmarkResult("PAE (Predictive Autoencoder)")
    try:
        from models.pae import PredictiveAutoencoder

        input_dim, latent_dim = 12, 16
        batch = 256

        clear_gpu()
        r.ram_before = get_ram_mb()
        r.vram_before = get_vram_mb()
        t0 = time.time()

        pae = PredictiveAutoencoder(input_dim, latent_dim).to(device)

        r.load_time = time.time() - t0
        r.ram_after = get_ram_mb()
        r.vram_after = get_vram_mb()

        state_t = torch.randn(batch, input_dim, device=device)
        state_t1 = torch.randn(batch, input_dim, device=device)

        # Encode benchmark
        times = []
        for _ in range(100):
            t1 = time.time()
            with torch.no_grad():
                pae.encode(state_t)
            if HAS_CUDA:
                torch.cuda.synchronize()
            times.append(time.time() - t1)
        r.inference_time = sum(times) / len(times)

        # Training step benchmark
        train_times = []
        for _ in range(20):
            t1 = time.time()
            pae.training_step(state_t, state_t1)
            if HAS_CUDA:
                torch.cuda.synchronize()
            train_times.append(time.time() - t1)
        avg_train = sum(train_times) / len(train_times)

        params = sum(p.numel() for p in pae.parameters())
        r.notes = f"{params:,} params | train_step={avg_train*1000:.1f}ms"

        del pae, state_t, state_t1
        clear_gpu()
    except Exception as e:
        r.success = False
        r.error = str(e)
    return r


def bench_gatv2(device):
    """Benchmark GATv2 Lite (Strategic Coordinator)."""
    r = BenchmarkResult("GATv2-Lite (Strategist)")
    try:
        from models.gatv2_lite import GATv2Lite

        input_dim, hidden_dim, output_dim, heads = 12, 64, 8, 4
        num_nodes, num_edges = 20, 60

        clear_gpu()
        r.ram_before = get_ram_mb()
        r.vram_before = get_vram_mb()
        t0 = time.time()

        gat = GATv2Lite(input_dim, hidden_dim, output_dim, heads).to(device)
        gat.eval()

        r.load_time = time.time() - t0
        r.ram_after = get_ram_mb()
        r.vram_after = get_vram_mb()

        x = torch.randn(num_nodes, input_dim, device=device)
        edge_index = torch.randint(0, num_nodes, (2, num_edges), device=device)

        times = []
        for _ in range(50):
            t1 = time.time()
            with torch.no_grad():
                gat(x, edge_index)
            if HAS_CUDA:
                torch.cuda.synchronize()
            times.append(time.time() - t1)
        r.inference_time = sum(times) / len(times)

        params = sum(p.numel() for p in gat.parameters())
        r.notes = f"{params:,} params | {num_nodes} nodes, {num_edges} edges"

        del gat, x, edge_index
        clear_gpu()
    except Exception as e:
        r.success = False
        r.error = str(e)
    return r


def bench_qwen3_llm():
    """Benchmark Qwen3.5 2B GGUF LLM (XAI Semantic Transducer) - CPU only as per ResourceManager."""
    r = BenchmarkResult("Qwen3.5 2B GGUF (XAI Transducer)")

    model_path = os.path.join(project_root, "Model_Vault", "Qwen3.5-2B-UD-Q6_K_XL.gguf")
    if not os.path.exists(model_path):
        r.success = False
        r.error = f"Model not found at {model_path}"
        r.notes = "Skipped - model files not present"
        return r

    try:
        from llama_cpp import Llama

        clear_gpu()
        r.ram_before = get_ram_mb()
        r.vram_before = get_vram_mb()
        t0 = time.time()

        model = Llama(
            model_path=model_path,
            n_gpu_layers=0,
            n_ctx=2048,
            verbose=False
        )

        r.load_time = time.time() - t0
        r.ram_after = get_ram_mb()
        r.vram_after = get_vram_mb()

        # Short inference benchmark
        messages = [
            {"role": "system", "content": "You are an expert."},
            {"role": "user", "content": "Analyze the traffic sensor data and provide a brief report."}
        ]

        t1 = time.time()
        outputs = model.create_chat_completion(
            messages=messages,
            max_tokens=50,
            temperature=0.0
        )
        r.inference_time = time.time() - t1

        r.notes = f"2B params (Q6_K) | CPU-only | {r.load_time:.1f}s load"

        # Measure CPU during inference
        proc = psutil.Process()
        proc.cpu_percent()
        model.create_chat_completion(messages=messages, max_tokens=30, temperature=0.0)
        r.cpu_percent = proc.cpu_percent() / psutil.cpu_count()

        del model
        gc.collect()
    except Exception as e:
        r.success = False
        r.error = str(e)
    return r


def bench_multi_agent_scenario(device, num_intersections=10):
    """Benchmark a realistic multi-agent scenario."""
    r = BenchmarkResult(f"Multi-Agent Scenario ({num_intersections} intersections)")
    try:
        from models.actor_critic_tcn import ActorCriticNet
        from models.d3qn_tcn import D3QN_TCN
        from models.pae import PredictiveAutoencoder
        from models.gatv2_lite import GATv2Lite

        n_obs, n_actions, hidden = 12, 4, 128
        pae_latent, seq_len = 16, 8

        clear_gpu()
        r.ram_before = get_ram_mb()
        r.vram_before = get_vram_mb()
        t0 = time.time()

        # Shared PAE
        pae = PredictiveAutoencoder(n_obs, pae_latent).to(device)

        # N LocalAgents
        agents = []
        for _ in range(num_intersections):
            net = ActorCriticNet(n_obs + pae_latent, n_actions, hidden).to(device)
            net.eval()
            agents.append(net)

        # 1 Guardian (policy + target)
        guardian_policy = D3QN_TCN(2, 2, pae_latent, 64).to(device)
        guardian_target = D3QN_TCN(2, 2, pae_latent, 64).to(device)
        guardian_policy.eval()
        guardian_target.eval()

        # 1 Strategist
        gat = GATv2Lite(n_obs, 64, 8, 4).to(device)
        gat.eval()

        r.load_time = time.time() - t0
        r.ram_after = get_ram_mb()
        r.vram_after = get_vram_mb()

        # Simulate one full step
        dummy_states = [torch.randn(1, seq_len, n_obs + pae_latent, device=device) for _ in range(num_intersections)]
        t1 = time.time()
        with torch.no_grad():
            for i, net in enumerate(agents):
                net(dummy_states[i])
            x = torch.randn(num_intersections, n_obs, device=device)
            ei = torch.randint(0, num_intersections, (2, num_intersections * 3), device=device)
            gat(x, ei)
            guardian_policy(torch.randn(1, 8, 2, device=device), torch.randn(1, pae_latent, device=device))
        if HAS_CUDA:
            torch.cuda.synchronize()
        r.inference_time = time.time() - t1

        total_params = sum(p.numel() for p in pae.parameters())
        for net in agents:
            total_params += sum(p.numel() for p in net.parameters())
        total_params += sum(p.numel() for p in guardian_policy.parameters())
        total_params += sum(p.numel() for p in guardian_target.parameters())
        total_params += sum(p.numel() for p in gat.parameters())
        r.notes = f"{total_params:,} total params | {num_intersections} agents"

        del pae, agents, guardian_policy, guardian_target, gat, dummy_states
        clear_gpu()
    except Exception as e:
        r.success = False
        r.error = str(e)
    return r


# ============================================================================
# REPORT GENERATOR
# ============================================================================

def generate_report(results: list, output_dir: str):
    """Generates the hardware recommendation report."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(output_dir, exist_ok=True)

    # --- System Info ---
    sys_info = {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor() or "Unknown",
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "cpu_cores_logical": psutil.cpu_count(logical=True),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 1),
        "gpu": get_gpu_name(),
        "vram_total_mb": round(get_total_vram_mb(), 0) if HAS_CUDA else 0,
        "cuda_available": HAS_CUDA,
        "torch_version": torch.__version__ if torch else "N/A",
        "python_version": platform.python_version(),
        "timestamp": timestamp,
    }

    # --- Compute Totals ---
    total_ram = sum(r.ram_delta for r in results if r.success)
    total_vram = sum(r.vram_delta for r in results if r.success and "Multi-Agent" not in r.name)

    # Find multi-agent result for realistic totals
    multi = next((r for r in results if "Multi-Agent" in r.name and r.success), None)
    if multi:
        total_ram_realistic = multi.ram_delta
        total_vram_realistic = multi.vram_delta
    else:
        total_ram_realistic = total_ram
        total_vram_realistic = total_vram

    # XAI LLM result
    xai = next((r for r in results if "Qwen3" in r.name and r.success), None)
    xai_ram = xai.ram_delta if xai else 7000  # estimate 7GB FP32

    # --- Recommendations ---
    total_system_ram = total_ram_realistic + xai_ram + 2048  # +2GB OS/overhead
    rec_ram = max(16, (int(total_system_ram / 1024) + 1) * 2)  # round up to even GB

    rec = {
        "minimum": {
            "ram_gb": max(16, rec_ram),
            "cpu_cores": max(6, psutil.cpu_count(logical=False) or 4),
            "gpu": "Not required (CPU-only mode supported)",
            "vram_gb": 0,
            "storage_gb": 15,
            "notes": "CPU-only mode. XAI Qwen3 runs on CPU (FP32). Slower inference."
        },
        "recommended": {
            "ram_gb": max(32, rec_ram + 16),
            "cpu_cores": max(8, (psutil.cpu_count(logical=False) or 4) + 2),
            "gpu": "NVIDIA RTX 3060 12GB or better",
            "vram_gb": 8,
            "storage_gb": 25,
            "notes": "GPU accelerated RL models. XAI LLM on CPU. Good for 10-20 intersections."
        },
        "optimal": {
            "ram_gb": 64,
            "cpu_cores": 16,
            "gpu": "NVIDIA RTX 4070 12GB+ or A4000",
            "vram_gb": 12,
            "storage_gb": 50,
            "notes": "Full GPU acceleration including FP16 XAI. Supports 50+ intersections."
        }
    }

    # --- JSON Report ---
    report_data = {
        "system_info": sys_info,
        "benchmark_results": [r.to_dict() for r in results],
        "totals": {
            "rl_models_ram_mb": round(total_ram_realistic, 1),
            "rl_models_vram_mb": round(total_vram_realistic, 1),
            "xai_llm_ram_mb": round(xai_ram, 1),
            "estimated_total_ram_mb": round(total_system_ram, 1),
        },
        "hardware_recommendations": rec,
    }

    json_path = os.path.join(output_dir, f"hardware_benchmark_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    # --- Markdown Report ---
    md_path = os.path.join(output_dir, f"hardware_benchmark_{timestamp}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# 🖥️ CARINA — Hardware Benchmark Report\n\n")
        f.write(f"**Generated:** {timestamp}  \n")
        f.write(f"**Host:** {sys_info['hostname']}  \n")
        f.write(f"**OS:** {sys_info['os']}  \n")
        f.write(f"**CPU:** {sys_info['cpu']} ({sys_info['cpu_cores_physical']}C/{sys_info['cpu_cores_logical']}T)  \n")
        f.write(f"**RAM:** {sys_info['ram_total_gb']} GB  \n")
        f.write(f"**GPU:** {sys_info['gpu']}  \n")
        if HAS_CUDA:
            f.write(f"**VRAM:** {sys_info['vram_total_mb']:.0f} MB  \n")
        f.write(f"**PyTorch:** {sys_info['torch_version']}  \n\n")

        f.write("---\n\n## 📊 Component Benchmark Results\n\n")
        f.write("| Component | RAM (MB) | VRAM (MB) | Load (s) | Inference (ms) | Status |\n")
        f.write("|-----------|----------|-----------|----------|----------------|--------|\n")
        for r in results:
            status = "✅" if r.success else "❌"
            inf_ms = f"{r.inference_time*1000:.1f}" if r.success else "N/A"
            f.write(f"| {r.name} | {r.ram_delta:.1f} | {r.vram_delta:.1f} | {r.load_time:.2f} | {inf_ms} | {status} |\n")

        f.write("\n### Notes\n\n")
        for r in results:
            if r.notes:
                f.write(f"- **{r.name}**: {r.notes}\n")
            if r.error:
                f.write(f"- **{r.name}** ⚠️: {r.error}\n")

        f.write("\n---\n\n## 🔧 Hardware Recommendations\n\n")
        for tier, spec in rec.items():
            emoji = {"minimum": "🟡", "recommended": "🟢", "optimal": "🔵"}
            f.write(f"### {emoji.get(tier, '⚪')} {tier.capitalize()}\n\n")
            f.write(f"| Resource | Specification |\n")
            f.write(f"|----------|---------------|\n")
            f.write(f"| RAM | {spec['ram_gb']} GB |\n")
            f.write(f"| CPU Cores | {spec['cpu_cores']}+ physical cores |\n")
            f.write(f"| GPU | {spec['gpu']} |\n")
            f.write(f"| VRAM | {spec['vram_gb']} GB |\n")
            f.write(f"| Storage | {spec['storage_gb']} GB SSD |\n")
            f.write(f"\n> {spec['notes']}\n\n")

        f.write("---\n\n## 📐 Resource Breakdown\n\n")
        f.write(f"- **RL Models Total RAM**: {total_ram_realistic:.0f} MB\n")
        f.write(f"- **RL Models Total VRAM**: {total_vram_realistic:.0f} MB\n")
        f.write(f"- **XAI LLM RAM (FP32)**: ~{xai_ram:.0f} MB\n")
        f.write(f"- **Estimated System Total**: ~{total_system_ram:.0f} MB ({total_system_ram/1024:.1f} GB)\n")

    print(f"\n📄 Reports saved to:")
    print(f"   JSON: {json_path}")
    print(f"   MD:   {md_path}")
    return json_path, md_path


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("🚦 CARINA HARDWARE BENCHMARK")
    print("=" * 70)
    print(f"CPU: {platform.processor()} ({psutil.cpu_count(logical=False)}C/{psutil.cpu_count()}T)")
    print(f"RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    print(f"GPU: {get_gpu_name()}")
    if HAS_CUDA:
        print(f"VRAM: {get_total_vram_mb():.0f} MB")
    print(f"Device: {'CUDA' if HAS_CUDA else 'CPU'}")
    print("=" * 70)

    device = torch.device("cuda" if HAS_CUDA else "cpu") if torch else "cpu"
    results = []

    # 1. Individual RL models
    benchmarks = [
        ("ActorCritic-TCN", lambda: bench_actor_critic_tcn(device)),
        ("D3QN-TCN", lambda: bench_dueling_dqn(device)),
        ("PAE", lambda: bench_pae(device)),
        ("GATv2-Lite", lambda: bench_gatv2(device)),
    ]

    for name, bench_fn in benchmarks:
        print(f"\n⏳ Benchmarking {name}...")
        r = bench_fn()
        results.append(r)
        if r.success:
            print(f"   ✅ RAM: +{r.ram_delta:.1f}MB | VRAM: +{r.vram_delta:.1f}MB | Inf: {r.inference_time*1000:.2f}ms")
        else:
            print(f"   ❌ Failed: {r.error}")

    # 2. Multi-agent scenario
    for n in [10, 30]:
        print(f"\n⏳ Benchmarking Multi-Agent ({n} intersections)...")
        r = bench_multi_agent_scenario(device, n)
        results.append(r)
        if r.success:
            print(f"   ✅ RAM: +{r.ram_delta:.1f}MB | VRAM: +{r.vram_delta:.1f}MB | Step: {r.inference_time*1000:.2f}ms")
        else:
            print(f"   ❌ Failed: {r.error}")

    # 3. XAI LLM (heaviest component)
    print(f"\n⏳ Benchmarking Qwen3 1.7B LLM (this may take a while)...")
    r = bench_qwen3_llm()
    results.append(r)
    if r.success:
        print(f"   ✅ RAM: +{r.ram_delta:.1f}MB | Load: {r.load_time:.1f}s | Inf: {r.inference_time:.1f}s")
    else:
        print(f"   ⚠️ Skipped/Failed: {r.error}")

    # 4. Generate report
    print("\n" + "=" * 70)
    print("📝 Generating Hardware Recommendation Report...")
    output_dir = os.path.join(project_root, "results", "hardware_benchmark")
    generate_report(results, output_dir)
    print("=" * 70)
    print("✅ Benchmark complete!")


if __name__ == "__main__":
    mp.freeze_support()
    main()
