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
# Date: June 19, 2026

import os
import json
import torch
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure basic logging to console (will be captured by the parent process)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [TRANSDUCER] - %(levelname)s - %(message)s')

class SemanticTransducer:
    """
    A specialized inference engine that translates Tensor Attributions into
    Natural Language Technical Reports (NTCIP style) using the frozen 'Jurist' LLM.
    
    This class is designed to run as a 'One-Shot' process:
    Load -> Generate -> Exit (to release VRAM).
    """

    def __init__(self, model_path: str, use_gpu: bool = None, offload_to_cpu: bool = True) -> None:
        if use_gpu is None:
            try:
                import torch
                use_gpu = torch.cuda.is_available()
            except ImportError:
                use_gpu = False
                
        self.model_path = model_path
        self.use_gpu = use_gpu
        self.device = "cuda" if use_gpu else "cpu"
        self.model = None
        
        logging.info(f"Initializing Transducer on device: {self.device} (GPU {'enabled' if use_gpu else 'disabled'})")

    def load_resources(self) -> None:
        """Loads the frozen model and tokenizer from the Model Vault."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model Vault not found at: {self.model_path}")

        from llama_cpp import Llama

        # 1. Try loading with GPU if enabled
        if self.use_gpu:
            try:
                logging.info(f"Carregando modelo GGUF via llama.cpp com aceleração de GPU (n_gpu_layers=-1): {self.model_path}")
                self.model = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,
                    n_threads=4,
                    n_gpu_layers=-1,
                    verbose=False
                )
                logging.info("Modelo GGUF carregado com sucesso na GPU.")
                return
            except Exception as e:
                logging.warning(f"Falha ao carregar modelo na GPU: {e}. Tentando fallback para CPU...")
                self.use_gpu = False
                self.device = "cpu"

        # 2. CPU / Fallback loading
        try:
            logging.info(f"Carregando modelo GGUF via llama.cpp no CPU (n_gpu_layers=0): {self.model_path}")
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0,
                verbose=False
            )
            logging.info("Modelo GGUF carregado com sucesso no CPU.")
        except ImportError:
            raise RuntimeError("llama-cpp-python is not installed. Please install it to use GGUF models.")
        except Exception as e:
            logging.error(f"Falha ao carregar modelo no CPU: {e}")
            raise RuntimeError("Failed to load model resources.")

    def _build_prompt(self, input_data: Dict[str, Any]) -> List[Dict[str, str]]:
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
        
        # Load external prompts (OCP Compliance)
        prompts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "slm_prompts.json")
        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts_db = json.load(f)
        except Exception as e:
            logging.error(f"[XAI] Erro ao carregar slm_prompts.json: {e}")
            prompts_db = {}
            
        # Fallback resolution
        mode_prompts = prompts_db.get(mode, prompts_db.get("AUTO", {}))
        instruction = mode_prompts.get(language, mode_prompts.get("en", "You are an AI assistant analyzing traffic data."))
        
        # Append conciseness and truthfulness guidelines to prevent truncation and feature hallucination
        concise_suffix_pt = (
            "\n\nATENÇÃO DE DIRETRIZES DE GERAÇÃO:\n"
            "1. Analise APENAS as variáveis que estão explicitamente listadas no dicionário 'TENSOR' do JSON de entrada. "
            "NÃO mencione, NÃO explique e NÃO invente nenhuma variável (como botões de pedestre, variáveis latentes PAE ou outros sensores) "
            "se elas não estiverem presentes no JSON.\n"
            "2. Seja objetivo e conciso. O laudo deve ser completo, cobrindo as variáveis fornecidas, mas curto e direto (máximo de 300 palavras), "
            "garantindo que toda a resposta caiba no limite de tokens sem ser truncada."
        )
        
        concise_suffix_en = (
            "\n\nATTENTION GENERATION GUIDELINES:\n"
            "1. Analyze ONLY the variables that are explicitly listed in the 'TENSOR' dictionary of the input JSON. "
            "DO NOT mention, DO NOT explain, and DO NOT hallucinate any variables (such as pedestrian buttons, PAE latent variables, or other sensors) "
            "if they are not present in the JSON.\n"
            "2. Be objective and concise. The report must be complete, covering the provided variables, but short and direct (maximum of 300 words), "
            "ensuring the entire response fits within the token limit without being truncated."
        )

        if language in ["pt", "pt_br"]:
            instruction += concise_suffix_pt
        else:
            instruction += concise_suffix_en
        
        # Create the Context String
        input_str = (
            f"CTX: [{timestamp}] | "
            f"MODE: [{mode}] | "
            f"TENSOR: {json.dumps(attributions)}"
        )
        
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": input_str}
        ]
        
        return messages

    def generate_report(self, input_data: Dict[str, Any]) -> str:
        """Runs the inference to generate the text."""
        import re
        messages = self._build_prompt(input_data)
        
        # Deterministic Generation using llama.cpp API
        outputs = self.model.create_chat_completion(
            messages=messages,
            max_tokens=1024, # Increased to prevent text truncation
            temperature=0.0, # do_sample=False equivalent
            repeat_penalty=1.05
        )
        
        full_output = outputs["choices"][0]["message"]["content"]
        
        # Strip thinking tags using regex so the UI doesn't see it
        report_text = re.sub(r"<think>.*?</think>", "", full_output, flags=re.DOTALL).strip()
        
        return report_text

def main() -> None:
    """CLI Entry Point for the Subprocess."""
    parser = argparse.ArgumentParser(description="CARINA Semantic Transducer (XAI)")
    parser.add_argument("--input", default=None, help="Path to input JSON file containing attributions")
    parser.add_argument("--output", default=None, help="Path to save the generated text report")
    parser.add_argument("--vault", default=None, help="Path to the model vault")
    parser.add_argument("--use_gpu", type=str, default="auto", choices=["auto", "true", "false"], help="Use GPU acceleration (auto/true/false)")
    
    args = parser.parse_args()
    
    # Resolve absolute paths
    input_path = os.path.abspath(args.input) if args.input else None
    output_path = os.path.abspath(args.output) if args.output else None
    
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
        if input_path:
            if not os.path.exists(input_path):
                 raise FileNotFoundError(f"Input file not found: {input_path}")
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            import sys
            data = json.loads(sys.stdin.read())
            
        # 2. Initialize Engine
        if args.use_gpu == "true":
            use_gpu = True
        elif args.use_gpu == "false":
            use_gpu = False
        else: # auto
            try:
                import torch
                use_gpu = torch.cuda.is_available()
            except:
                use_gpu = False
                
        transducer = SemanticTransducer(model_path, use_gpu=use_gpu, offload_to_cpu=True)
        transducer.load_resources()
        
        # 3. Generate
        logging.info("Generating Report...")
        report = transducer.generate_report(data)
        
        # 4. Save Output
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"Report saved to: {output_path}")
        else:
            import sys
            sys.stdout.write(report)
        
    except Exception as e:
        logging.error(f"Transducer Failure: {e}", exc_info=True)
        # Write error to output file or stdout so UI can show it gracefully
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