import sys
import os
import time
import importlib

print("[SANITY] Preparing to trace imports...")

# Fake the UI so it doesn't even try to load PyQt or PySide
sys.modules['PyQt5'] = type('Mock', (object,), {})()
sys.modules['PyQt6'] = type('Mock', (object,), {})()
sys.modules['PySide6'] = type('Mock', (object,), {})()

# Fake heavy libraries
sys.modules['torch'] = type('MockTorch', (object,), {'cuda': type('MockCuda', (object,), {'is_available': lambda: False}), 'Tensor': type('MockTensor', (object,), {}), 'nn': type('MockNN', (object,), {'Module': object})})()
sys.modules['torchvision'] = type('Mock', (object,), {})()
sys.modules['psutil'] = type('Mock', (object,), {})()

print("[SANITY] Fakes injected. Now trying to import CentralController...")

try:
    # Add root to path as done in carina.py
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)
    sys.path.insert(0, os.path.join(project_root, 'src'))

    from src.central_controller import CentralController
    print("[SANITY] SUCCESSFULLY IMPORTED CENTRAL CONTROLLER!")
except Exception as e:
    print(f"[SANITY] Import failed with exception: {e}")
    import traceback
    traceback.print_exc()

print("[SANITY] Done.")
