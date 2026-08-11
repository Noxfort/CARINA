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

# File: src/mfd/mfd_subprocess_fallback.py
# Author: Gabriel Moraes
# Date: August 9, 2026

import sys
import json
import logging
import subprocess
from typing import Dict, Any

class MFDSubprocessFallback:
    """
    Responsibility (SRP): Run SLM transducer CLI in an isolated subprocess
    when mock or subprocess fallback is required for memory isolation.
    """

    @staticmethod
    def try_subprocess_transducer(payload: Dict[str, Any], device: str = "auto", gpu_layers: str = "16") -> str:
        """
        Executes isolated GGUF transducer inference in a separate process.

        :param payload: JSON payload dictionary for SLM inference
        :param device: Target compute device ("auto", "cpu", "cuda")
        :param gpu_layers: String specifying GPU layers to offload
        :return: Generated report text string
        """
        try:
            cmd = [
                sys.executable,
                "-m", "slm.semantic_transducer",
                "--payload", json.dumps(payload),
                "--device", device,
                "--gpu_layers", str(gpu_layers)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                resp = json.loads(result.stdout)
                return resp.get("report_text", "")
            else:
                logging.warning(f"[MFD_SUBPROCESS_FALLBACK] Isolated process error: {result.stderr}")
                return ""
        except Exception as e:
            logging.error(f"[MFD_SUBPROCESS_FALLBACK] Failed to execute isolated SLM transducer process: {e}")
            return ""
