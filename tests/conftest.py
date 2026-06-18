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
#
# File: tests/conftest.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import os
import sys
import pytest

# Ensure we're running from CARINA_CORE root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MOCK HEAVY IMPORTS BEFORE THEY HAPPEN ---
# This prevents PyTorch, OpenCV, or PyQt from attempting to start heavy contexts 
# (like CUDA or X11) just because a file imported them at the top.
from unittest.mock import MagicMock

mock_nn = MagicMock()
class Module: pass
mock_nn.Module = Module

class DummyTensor:
    def __init__(self, data, shape=None):
        self._data = data
        if shape is not None:
            self.shape = shape
        else:
            try:
                if isinstance(data, list):
                    if len(data) > 0 and isinstance(data[0], list):
                        self.shape = (len(data), len(data[0]))
                    else:
                        self.shape = (len(data),)
                elif hasattr(data, 'shape'):
                    self.shape = data.shape
                else:
                    self.shape = ()
            except Exception:
                self.shape = ()

    def to(self, *args, **kwargs):
        return self

    def item(self):
        return self._data

    def max(self, *args, **kwargs):
        return DummyTensor(None, shape=()), DummyTensor(0, shape=())

    def __getitem__(self, idx):
        if isinstance(idx, tuple):
            return DummyTensor(0)
        try:
            sub = self._data[idx]
            return DummyTensor(sub)
        except Exception:
            return DummyTensor(0)

class DummyTorch:
    class cuda:
        @staticmethod
        def is_available(): return False
        @staticmethod
        def get_device_name(idx): return 'Mock CPU'
    
    nn = mock_nn
    optim = MagicMock()
    distributions = MagicMock()
    amp = MagicMock()
    
    float32 = 'float32'
    long = 'long'
    int64 = 'int64'
    bool = 'bool'
    float = 'float'
    double = 'double'
    int = 'int'
    
    @staticmethod
    def zeros(shape, *args, **kwargs):
        return DummyTensor(None, shape=shape)
        
    @staticmethod
    def tensor(data, *args, **kwargs):
        return DummyTensor(data)
        
    @staticmethod
    def cat(*args, **kwargs):
        return DummyTensor(None)
        
    @staticmethod
    def rand(shape, *args, **kwargs):
        return DummyTensor(None, shape=shape)
        
    @staticmethod
    def save(*args, **kwargs):
        return MagicMock()
        
    @staticmethod
    def load(*args, **kwargs):
        return MagicMock()
        
    class DeviceMock:
        def __init__(self, type_str):
            self.type = type_str
        def __str__(self):
            return self.type
            
    class Tensor: pass
    
    @staticmethod
    def device(name): 
        return DummyTorch.DeviceMock(name)
    
    @staticmethod
    def no_grad():
        class NoGradContext:
            def __enter__(self): pass
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        return NoGradContext()

sys.modules['torch'] = DummyTorch()
sys.modules['torch.nn'] = DummyTorch.nn
sys.modules['torch.nn.functional'] = MagicMock()
sys.modules['torch.nn.utils'] = MagicMock()
sys.modules['torch.optim'] = DummyTorch.optim
sys.modules['torch.distributions'] = DummyTorch.distributions
sys.modules['torch.amp'] = DummyTorch.amp
sys.modules['torch_geometric'] = MagicMock()
sys.modules['torch_geometric.nn'] = MagicMock()
sys.modules['torchvision'] = type('Mock', (object,), {})()
sys.modules['psutil'] = type('Mock', (object,), {'Process': lambda: type('P', (object,), {'cpu_percent': lambda self, *a, **k: 0, 'memory_percent': lambda self: 0})()})()
sys.modules['cv2'] = type('Mock', (object,), {})()

@pytest.fixture(autouse=True)
def setup_test_env():
    """
    Global fixture that runs before each test.
    Ensures that critical environment variables are configured for
    testing mode (avoiding real UI or production DB connections).
    """
    os.environ['CARINA_TEST_MODE'] = '1'
    # Prevents PyQt/PySide interfaces from attempting to use X11 if running in headless CI
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['QT_MAC_WANTS_LAYER'] = '1'
    # Prevents OpenCV from attempting to open windows or connect to GTK/Wayland
    os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'dummy'
    # Torch JIT often crashes on initialization in headless environments
    os.environ['PYTORCH_JIT'] = '0'
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    
    yield
    
    # Cleanup after test
    for key in ['CARINA_TEST_MODE', 'QT_QPA_PLATFORM', 'QT_MAC_WANTS_LAYER', 
                'OPENCV_VIDEOIO_PRIORITY_MSMF', 'OPENCV_FFMPEG_CAPTURE_OPTIONS',
                'PYTORCH_JIT', 'TF_ENABLE_ONEDNN_OPTS']:
        os.environ.pop(key, None)

from typing import Any

@pytest.fixture
def mock_snmp_hardware(monkeypatch):
    """
    Perfectly simulates SNMP Hardware without generating network traffic.
    Injects interceptions for snmp_get and snmp_set directly into the base class.
    """
    # Lazy import to avoid dependency cycles and hangs
    from src.drivers.base_driver import BaseTrafficDriver
    
    # RAM acting as OID registers of the Virtual Traffic Light
    hardware_memory = {}
    
    def fake_snmp_get(self, oid: str):
        if oid in hardware_memory:
            return True, hardware_memory[oid] # Success, Value
        return False, "TIMEOUT (Simulated Timeout)" # Failure
        
    def fake_snmp_set(self, oid: str, value: Any, value_type: Any):
        hardware_memory[oid] = value
        return True, "Success"
        
    monkeypatch.setattr(BaseTrafficDriver, 'snmp_get', fake_snmp_get)
    monkeypatch.setattr(BaseTrafficDriver, 'snmp_set', fake_snmp_set)
    
    return hardware_memory

@pytest.fixture
def mock_logger(mocker):
    """
    Simulates a generic log function for functions expecting 
    a 'log_callback' (like SignalRouter or AppState).
    """
    return mocker.MagicMock()
