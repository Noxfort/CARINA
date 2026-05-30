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

# File: src/xai/semantic_transducer.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import os
import json
import torch
import argparse
import logging
from datetime import datetime
from xai.resource_manager import ResourceManager

# Configure basic logging to console (will be captured by the parent process)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [TRANSDUCER] - %(levelname)s - %(message)s')

class SemanticTransducer:
    """
    A specialized inference engine that translates Tensor Attributions into
    Natural Language Technical Reports (NTCIP style) using the frozen 'Jurist' LLM.
    
    This class is designed to run as a 'One-Shot' process:
    Load -> Generate -> Exit (to release VRAM).
    """

    def __init__(self, model_path: str, use_gpu: bool = False, offload_to_cpu: bool = True):
        # Forçar uso exclusivo da CPU
        self.model_path = model_path
        self.resource_manager = ResourceManager(model_path, use_gpu=False, offload_to_cpu=True)
        self.device = self.resource_manager.get_device()
        
        logging.info(f"Initializing Transducer on device: {self.device} (GPU desativada)")

    def load_resources(self):
        """Loads the frozen model and tokenizer from the Model Vault using ResourceManager."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model Vault not found at: {self.model_path}")

        success = self.resource_manager.load_resources()
        if not success:
            raise RuntimeError("Failed to load model resources.")
            
        self.model = self.resource_manager.get_model()
        
        if self.model is None:
            raise RuntimeError("Model or tokenizer failed to load.")

    def _build_prompt(self, input_data: dict) -> str:
        """
        Constructs a chat-template format prompt for Qwen3, implementing a thinking
        mode requirement with multilingual UI alignment.
        """
        # Extract metadata
        timestamp = input_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        mode = input_data.get("mode", "AUTO")
        language = input_data.get("language", "en")
        
        # Extract attribution map (The "Tensor" part)
        attributions = input_data.get("attributions", {})
        
        # Create the Context String
        input_str = (
            f"CTX: [{timestamp}] | "
            f"MODE: [{mode}] | "
            f"TENSOR: {json.dumps(attributions)}"
        )
        
        if language == "pt_br":
            instruction = "Você é um especialista em tráfego urbano. Analise o contexto operacional e o vetor de sensores para gerar um laudo técnico curto e objetivo em Português. Você DEVE pensar antes de responder, colocando seu raciocínio lógico envolto em tags <think> e </think>."
        else:
            instruction = "You are an urban traffic expert. Analyze the operational context and sensor vector to generate a short, objective technical report in English. You MUST think before responding by wrapping your logical reasoning within <think> and </think> tags."
        
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": input_str}
        ]
        
        return messages

    def generate_report(self, input_data: dict) -> str:
        """Runs the inference to generate the text."""
        import re
        messages = self._build_prompt(input_data)
        
        # Deterministic Generation using llama.cpp API
        outputs = self.model.create_chat_completion(
            messages=messages,
            max_tokens=600,
            temperature=0.0, # do_sample=False equivalent
            repeat_penalty=1.05
        )
        
        full_output = outputs["choices"][0]["message"]["content"]
        
        # Strip thinking tags using regex so the UI doesn't see it
        report_text = re.sub(r"<think>.*?</think>", "", full_output, flags=re.DOTALL).strip()
        
        return report_text

def main():
    """CLI Entry Point for the Subprocess."""
    parser = argparse.ArgumentParser(description="CARINA Semantic Transducer (XAI)")
    parser.add_argument("--input", required=True, help="Path to input JSON file containing attributions")
    parser.add_argument("--output", required=True, help="Path to save the generated text report")
    parser.add_argument("--vault", default=None, help="Path to the model vault")
    # Argumentos relacionados à GPU removidos para forçar uso exclusivo da CPU
    
    args = parser.parse_args()
    
    # Resolve absolute paths
    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    
    # Locate Model Vault automatically if not provided
    if args.vault:
        model_path = args.vault
    else:
        # Locate the specific Qwen3.5 2B GGUF file inside Model_Vault
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, "Model_Vault", "Qwen3.5-2B-UD-Q6_K_XL.gguf")

    try:
        logging.info("Starting Semantic Transducer Process...")
        logging.info(f"Target Vault: {model_path}")
        
        # 1. Load Input Data
        if not os.path.exists(input_path):
             raise FileNotFoundError(f"Input file not found: {input_path}")

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 2. Initialize Engine
        # Forçar uso exclusivo da CPU
        transducer = SemanticTransducer(model_path, use_gpu=False, offload_to_cpu=True)
        transducer.load_resources()
        
        # 3. Generate
        logging.info("Generating Report...")
        report = transducer.generate_report(data)
        
        # 4. Save Output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        logging.info(f"Report saved to: {output_path}")
        
    except Exception as e:
        logging.error(f"Transducer Failure: {e}", exc_info=True)
        # Write error to output file so UI can show it gracefully
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"ERROR: Failed to generate report. Details: {str(e)}")
        except:
            pass
        exit(1)

if __name__ == "__main__":
    main()