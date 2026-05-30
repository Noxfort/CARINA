# -*- mode: python ; coding: utf-8 -*-
# ==============================================================================
# CARINA PyInstaller Spec — Full GPU Build (all deps, no NVIDIA kernel drivers)
# Generated: 2026-03-21
#
# Usage (inside Docker container):
#   pyinstaller --noconfirm carina.spec
# ==============================================================================

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# ─────────────────────────────────────────────────────────────────────────────
# 1. PACKAGES TO FULLY COLLECT (collect_all — gets binaries, data, hiddenimports)
# ─────────────────────────────────────────────────────────────────────────────
packages_to_collect = [
    # --- AI & Deep Learning ---
    'torch',
    'torch_geometric',
    'captum',
    'transformers',
    'accelerate',
    'safetensors',
    'huggingface_hub',
    'tokenizers',
    'tensorboard',
    'sympy',

    # --- Data Science ---
    'pandas',
    'numpy',
    'scipy',
    'sklearn',
    'matplotlib',

    # --- NVIDIA CUDA Runtime Libraries ---
    'nvidia',
    'triton',
    'cuda',

    # --- Communication ---
    'grpc',
    'grpcio',
    'websockets',
    'google.protobuf',

    # --- UI ---
    'flet',
    'flet_core',
    'flet_runtime',

    # --- Database & Messaging ---
    'psycopg2',
    'paho',

    # --- Hardware & Monitoring ---
    'pysnmp',
    'pyasn1',
    'prometheus_client',
    'psutil',

    # --- Simulation ---
    'sumolib',
    'traci',

    # --- Networking / HTTP ---
    'httpx',
    'httpcore',
    'h2',
    'aiohttp',
    'requests',
    'certifi',

    # --- Hashing & Utilities ---
    'xxhash',
    'yaml',
    'rich',
    'tqdm',
    'Pillow',
    'PIL',

    # --- System Tray ---
    'pystray',
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. COLLECT ALL — accumulate datas, binaries, hiddenimports from each package
# ─────────────────────────────────────────────────────────────────────────────
all_datas = []
all_binaries = []
all_hiddenimports = []

for pkg in packages_to_collect:
    try:
        d, b, h = collect_all(pkg)
        all_datas += d
        all_binaries += b
        all_hiddenimports += h
    except Exception as e:
        print(f'[carina.spec] WARNING: collect_all("{pkg}") failed: {e}')

# ─────────────────────────────────────────────────────────────────────────────
# 3. EXPLICIT HIDDEN IMPORTS (submodules that collect_all might miss)
# ─────────────────────────────────────────────────────────────────────────────
all_hiddenimports.extend([
    # --- gRPC core ---
    'grpc',
    'grpc._cython',
    'grpc._cython.cygrpc',
    'grpc.experimental',
    'grpc.framework',
    'grpc.framework.foundation',

    # --- Protobuf ---
    'google',
    'google.protobuf',
    'google.protobuf.descriptor',
    'google.protobuf.descriptor_pool',
    'google.protobuf.reflection',
    'google.protobuf.symbol_database',
    'google.protobuf.internal',
    'google.protobuf.internal.containers',
    'google.protobuf.internal.enum_type_wrapper',

    # --- Flet ---
    'flet',
    'flet.app',
    'flet_core',
    'flet_runtime',
    'flet.core',

    # --- Database & Messaging ---
    'psycopg2',
    'psycopg2._psycopg',
    'psycopg2.extensions',
    'psycopg2.extras',
    'paho.mqtt',
    'paho.mqtt.client',
    'paho.mqtt.publish',
    'paho.mqtt.subscribe',

    # --- Monitoring ---
    'prometheus_client',
    'prometheus_client.core',
    'prometheus_client.exposition',
    'prometheus_client.metrics',
    'prometheus_client.metrics_core',

    # --- PySnmp ---
    'pysnmp',
    'pysnmp.hlapi',
    'pysnmp.hlapi.v3arch',
    'pysnmp.hlapi.v3arch.asyncio',
    'pyasn1',
    'pyasn1.type',
    'pyasn1.type.univ',

    # --- AI / ML ---
    'torch',
    'torch.nn',
    'torch.optim',
    'torch.utils',
    'torch.utils.data',
    'torch.multiprocessing',
    'torch.distributed',
    'torch_geometric',
    'torch_geometric.nn',
    'torch_geometric.data',
    'torch_geometric.utils',
    'captum',
    'captum.attr',
    'transformers',
    'transformers.models',
    'transformers.tokenization_utils',
    'accelerate',
    'safetensors',
    'safetensors.torch',
    'tokenizers',

    # --- Data Science ---
    'sklearn',
    'sklearn.utils',
    'sklearn.utils._cython_blas',
    'sklearn.neighbors._typedefs',
    'sklearn.neighbors._quad_tree',
    'sklearn.tree._utils',
    'sklearn.preprocessing',
    'scipy',
    'scipy.special',
    'scipy.linalg',
    'scipy.sparse',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'pandas',
    'pandas.core',

    # --- Plotting ---
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.backends',
    'matplotlib.backends.backend_agg',

    # --- Networking ---
    'websockets',
    'websockets.legacy',
    'websockets.legacy.server',
    'httpx',
    'httpcore',
    'aiohttp',
    'requests',

    # --- Simulation ---
    'sumolib',
    'sumolib.net',
    'traci',
    'traci.constants',

    # --- Utilities ---
    'xxhash',
    'psutil',
    'configparser',
    'yaml',
    'rich',
    'rich.console',
    'tqdm',
    'tqdm.auto',
    'PIL',
    'PIL.Image',
    'pillow',
    'json',
    'logging',
    'multiprocessing',
    'multiprocessing.spawn',
    'multiprocessing.popen_spawn_posix',

    # --- System Tray ---
    'pystray',
    'pystray._xorg',

    # --- Deep Translator ---
    'deep_translator',
    'deep_translator.google',

    # --- CARINA internal modules ---
    'central_controller',
    'main',
    'watchdog',
    'utils.paths',
    'utils.logging_setup',
    'utils.metrics_manager',
    'utils.locale_manager_backend',
    'utils.settings_manager',
    'utils.network_parser',
    'utils.network_topology_parser',
    'utils.map_data_parser',
    'utils.map_generator',
    'utils.map_processor',
    'sds.dashboard_worker',
    'sds.dashboard_orchestrator',
    'sds.websocket_server',
    'sds.data_processor',
    'sds.telemetry_aggregator',
    'sds.street_metrics_calculator',
    'sds.tls_state_formatter',
    'sds.tls_state_provider',
    'sds.tls_map_extractor',
    'sds.weights_manager',
    'sas.analysis_worker',
    'database.database_worker',
    'database.database_manager',
    'database.worker_monitor',
    'xai.xai_worker',
    'xai.captum_analyzer',
    'xai.report_pipeline',
    'xai.request_scanner',
    'xai.agent_reconstructor',
    'xai.semantic_transducer',
    'xai.xai_watcher',
    'core.inference_engine',
    'core.observation_builder',
    'core.decision_coordinator',
    'core.strategic_coordinator',
    'core.population_manager',
    'core.lifecycle_manager',
    'core.maturity_manager',
    'core.maturity_reporter',
    'core.childhood_analyzer',
    'core.threshold_calibrator',
    'core.safety_auditor',
    'core.system_reporter',
    'core.action_authorizer',
    'core.traci_proxy',
    'core.enums',
    'controller.traffic_frame_processor',
    'drivers.driver_factory',
    'drivers.base_driver',
    'drivers.ntcip_driver',
    'drivers.utmc_driver',
    'drivers.traffic_light_driver',
    'agents',
    'communication',
    'rendering',
    'safety.guardian_worker',
    'memory',
    'models',
    'manager',
    'simulation',
    'hooks',
])

# ─────────────────────────────────────────────────────────────────────────────
# 4. PROJECT DATA — bundled into _internal/
# ─────────────────────────────────────────────────────────────────────────────
project_datas = [
    ('src',         'src'),
    ('proto',       'proto'),
    ('ui',          'ui'),
    ('config',      'config'),
    ('Model_Vault', 'Model_Vault'),
]

all_datas += project_datas

# ─────────────────────────────────────────────────────────────────────────────
# 5. EXCLUSIONS (reduce size — do NOT exclude nvidia CUDA libs)
# ─────────────────────────────────────────────────────────────────────────────
excludes_list = [
    # Dev tools — not needed at runtime
    'pytest',
    'pytest_cov',
    'pytest_mock',
    'coverage',
    'ipython',
    'jupyter_client',
    'jupyter_core',
    'jupyterlab_pygments',
    'nbclient',
    'nbconvert',
    'nbformat',
    'pipreqs',
    'iniconfig',

    # Tk — not used (Flet-based UI)
    'tkinter',
    '_tkinter',
]

# ─────────────────────────────────────────────────────────────────────────────
# 6. ANALYSIS + EXE + COLLECT
# ─────────────────────────────────────────────────────────────────────────────
a = Analysis(
    ['carina.py'],
    pathex=['src', 'proto', 'ui'],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=list(set(all_hiddenimports)),  # deduplicate
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/hooks/pyi_runtime_hooks.py'],
    excludes=excludes_list,
    noarchive=False,
    optimize=0,
)

# ─────────────────────────────────────────────────────────────────────────────
# 6b. EXCLUDE system libs that must come from the host (avoid GLIBCXX mismatch)
# ─────────────────────────────────────────────────────────────────────────────
# The Docker build env (Ubuntu 22.04) has older libstdc++/libgcc than the
# target host (Ubuntu 24.04). Bundling them causes GLIBCXX_3.4.32 errors.
# By removing them, the system's native versions are used at runtime.
import re
_exclude_libs = re.compile(r'libstdc\+\+\.so|libgcc_s\.so')
a.binaries = [b for b in a.binaries if not _exclude_libs.search(b[0])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='carina',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,  # UPX breaks torch/CUDA shared libs
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ui/assets/images/logo.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name='carina',
)
