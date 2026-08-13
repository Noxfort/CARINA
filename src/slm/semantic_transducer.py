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

# File: src/slm/semantic_transducer.py
# Author: Gabriel Moraes
# Date: July 29, 2026

import sys
import os
import json
import argparse
import logging
from typing import Dict, Any, List

# Ensure project 'src' directory is in sys.path when executed directly as a script
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from slm.device_manager import SLMDeviceManager
from slm.model_loader import SLMModelLoader
from slm.prompt_builder import SLMPromptBuilder
from slm.output_sanitizer import SLMOutputSanitizer
from slm.revision_engine import SLMRevisionEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [TRANSDUCER] - %(levelname)s - %(message)s')

class SemanticTransducer:
    """
    Orchestrates SLM inference and text transduction for CARINA v1.0.
    Acts as a clean Facade coordinating device resolution, model loading,
    prompt building, output sanitization, and 2nd pass neural proofreading.
    """

    def __init__(self, model_path: str = None, use_gpu: bool = None, offload_to_cpu: bool = True, device: str = None, gpu_layers: int = 16) -> None:
        if not model_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(base_dir, "Model_Vault", "Qwen3.5-2B-UD-Q6_K_XL.gguf")
        self.model_path = model_path
        self.model = None

        if device is None:
            try:
                from utils.settings_manager import SettingsManager
                sm = SettingsManager()
                st = sm.load_settings()
                device = st.get("xai_slm_device") or st.get("report_slm_device") or "auto"
                gpu_layers_val = st.get("xai_slm_gpu_layers") or st.get("report_slm_gpu_layers") or "16"
                try:
                    gpu_layers = int(gpu_layers_val)
                except ValueError:
                    gpu_layers = 16
            except Exception:
                device = "auto"

        self.device_setting, self.gpu_layers = SLMDeviceManager.resolve_device_settings(device, gpu_layers)

    def load_resources(self) -> None:
        """Loads the GGUF model resource."""
        self.model = SLMModelLoader.load_model(self.model_path, self.device_setting, self.gpu_layers)

    def _build_prompt(self, input_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Constructs chat-template prompt messages."""
        return SLMPromptBuilder.build_chat_messages(input_data)

    def generate_report(self, input_data: Dict[str, Any]) -> str:
        """Runs inference to generate report narrative text."""
        if hasattr(self.model, "generate_report"):
            res = self.model.generate_report(input_data)
            if isinstance(res, str):
                return res
            return str(res)

        messages = self._build_prompt(input_data)

        # Estimate prompt tokens and dynamically scale max_tokens
        prompt_str = ""
        for m in messages:
            prompt_str += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"

        try:
            prompt_tokens = len(self.model.tokenize(prompt_str.encode('utf-8')))
        except Exception:
            prompt_tokens = int(len(prompt_str) / 3.5)

        n_ctx = 8192
        safety_buffer = 128
        max_gen_tokens = n_ctx - prompt_tokens - safety_buffer
        max_tokens = max(512, min(4096, max_gen_tokens))

        logging.info(f"[SemanticTransducer] Prompt tokens: {prompt_tokens}, Dynamic max_tokens: {max_tokens}")

        outputs = self.model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.0,
            repeat_penalty=1.05
        )

        raw_output = outputs["choices"][0]["message"]["content"]
        return SLMOutputSanitizer.sanitize(raw_output)

    def review_text(self, draft_text: str, language: str = "pt_br") -> str:
        """Executes 2nd Pass Neural Proofreading in clean memory context."""
        return SLMRevisionEngine.review_text(self.model, draft_text, language)


def main() -> None:
    """CLI Entry Point for subprocess calls."""
    parser = argparse.ArgumentParser(description="CARINA v1.0 SLM Semantic Transducer CLI")
    parser.add_argument("--input", type=str, help="Path to input JSON file")
    parser.add_argument("--output", type=str, help="Path to output markdown file")
    parser.add_argument("--vault", type=str, help="Path to GGUF model file in Model_Vault")
    parser.add_argument("--use_gpu", type=str, default="auto", choices=["auto", "true", "false"], help="Use GPU acceleration")
    parser.add_argument("--device", type=str, default=None, choices=["cpu", "gpu", "mixed", "auto"], help="Execution device")
    parser.add_argument("--gpu_layers", type=int, default=16, help="Number of GPU layers to offload")

    args = parser.parse_args()

    input_path = os.path.abspath(args.input) if args.input else None
    output_path = os.path.abspath(args.output) if args.output else None

    if args.vault:
        model_path = args.vault
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, "Model_Vault", "Qwen3.5-2B-UD-Q6_K_XL.gguf")

    try:
        logging.info("Starting SLM Semantic Transducer Process...")
        logging.info(f"Target Vault: {model_path}")

        if input_path:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            import sys
            data = json.loads(sys.stdin.read())

        device_arg = args.device
        if device_arg is None:
            if args.use_gpu == "true":
                device_arg = "gpu"
            elif args.use_gpu == "false":
                device_arg = "cpu"
            else:
                device_arg = "auto"

        transducer = SemanticTransducer(
            model_path,
            device=device_arg,
            gpu_layers=args.gpu_layers,
            offload_to_cpu=True
        )
        transducer.load_resources()

        logging.info("Generating Report...")
        report = transducer.generate_report(data)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"Report saved to: {output_path}")
        else:
            import sys
            sys.stdout.write(report)

    except Exception as e:
        logging.error(f"Transducer Failure: {e}", exc_info=True)
        try:
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"ERROR: Failed to generate report. Details: {str(e)}")
            else:
                import sys
                sys.stdout.write(f"ERROR: Failed to generate report. Details: {str(e)}")
        except:
            pass
        exit(1)

if __name__ == "__main__":
    main()
