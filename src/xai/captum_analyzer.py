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

# File: src/xai/captum_analyzer.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
import os
import logging
import time
from datetime import datetime
from captum.attr import IntegratedGradients
from typing import Optional, Dict, Any

from utils.locale_manager_backend import LocaleManagerBackend
from agents.local_agent import LocalAgent
from models.pae import PredictiveAutoencoder

# Ensure matplotlib does not try to open windows (headless mode)
plt.switch_backend('Agg')

class CaptumModelWrapper(nn.Module):
    """
    Wrapper that encapsulates the agent's model for Captum compatibility.
    If the agent has a PAE, the wrapper applies the PAE augmentation internally
    so that the attribution covers the augmented input space.
    """
    def __init__(self, model: nn.Module, shared_pae: Optional[PredictiveAutoencoder] = None) -> None:
        super(CaptumModelWrapper, self).__init__()
        self.model = model
        self.shared_pae = shared_pae

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # If we have PAE, augment the input with the latent vector
        if self.shared_pae is not None:
            with torch.no_grad():
                last_frame = x[:, -1, :]  # [batch, n_obs]
                # Extract only the original features (without latent) for the encode
                original_dim = self.shared_pae.input_dim
                original_frame = last_frame[:, :original_dim]
                latent = self.shared_pae.encode(original_frame)
                latent_expanded = latent.unsqueeze(1).expand(-1, x.size(1), -1)
                x = torch.cat([x, latent_expanded], dim=-1)
        else:
            # Fallback: if model expects more features than x provides, pad with zeros
            # This happens when the agent was trained with PAE but PAE is lost.
            expected_dim = self.model.tcn.network[0].conv1.in_channels
            if x.shape[-1] < expected_dim:
                padding_dim = expected_dim - x.shape[-1]
                zeros = torch.zeros(*x.shape[:-1], padding_dim, device=x.device, dtype=x.dtype)
                x = torch.cat([x, zeros], dim=-1)
                
        return self.model(x)[0]

class CaptumAnalyzer:
    def __init__(self, agent: LocalAgent, scenario_results_dir: str, locale_manager: LocaleManagerBackend, feature_glossary: Optional[Dict[int, Dict[str, str]]] = None) -> None:
        """
        Initializes the Captum Analyzer with PAE-aware feature glossary.
        """
        self.agent = agent
        self.locale_manager = locale_manager
        
        # --- MEMORY OPTIMIZATION ---
        self.device = torch.device("cpu")
        
        # Move the model wrapper to CPU (with PAE awareness)
        self.wrapped_model = CaptumModelWrapper(
            self.agent.policy_net, 
            shared_pae=getattr(self.agent, 'shared_pae', None)
        ).to(self.device)
        self.ig = IntegratedGradients(self.wrapped_model)
        
        # --- Expand feature glossary with PAE latent features ---
        self.feature_glossary = feature_glossary if feature_glossary else {}
        self._expand_glossary_with_pae()
        
        self.output_dir = os.path.join(scenario_results_dir, "captum", "reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.output_path_png = os.path.join(self.output_dir, f"xai_report_{agent.id}_{timestamp}.png")
        self.output_path_txt = os.path.join(self.output_dir, f"xai_report_{agent.id}_{timestamp}.txt")
    
    def _expand_glossary_with_pae(self) -> None:
        """
        Expands the feature glossary with the PAE latent dimensions.
        The latent features are named PAE_latent_0..PAE_latent_N and
        represent compressed projections of urban fluid dynamics.
        """
        shared_pae = getattr(self.agent, 'shared_pae', None)
        if shared_pae is None:
            return
        
        # Determine the starting index (after the original features)
        base_idx = self.agent.n_observations
        latent_dim = shared_pae.latent_dim
        
        pae_descriptions = {
            0: "Latent component of flow intensity",
            1: "Latent component of occupancy gradient",
            2: "Latent component of average speed",
            3: "Latent component of queue pressure",
        }
        
        if isinstance(self.feature_glossary, dict):
            for i in range(latent_dim):
                desc = pae_descriptions.get(i, f"PAE predictive projection dim {i}")
                self.feature_glossary[base_idx + i] = {
                    "name": f"PAE_latent_{i}",
                    "description": desc
                }
        elif isinstance(self.feature_glossary, list):
            for i in range(latent_dim):
                desc = pae_descriptions.get(i, f"PAE predictive projection dim {i}")
                self.feature_glossary.append({
                    "feature_name": f"PAE_latent_{i}",
                    "description": desc
                })
        
        logging.info(f"[CaptumAnalyzer] Feature glossary expanded with {latent_dim} PAE latent features")
        
    def _get_feature_glossary(self) -> Any:
        return self.feature_glossary

    def generate_analysis(self) -> Optional[Dict[str, str]]:
        lm = self.locale_manager
        original_mode_is_training = self.agent.policy_net.training
        
        try:
            self.agent.policy_net.eval()
            
            # Retrieve recent experiences
            if self.agent.xai_memory.size == 0:
                logging.warning(lm.get_string("captum_analyzer.run.empty_memory_warning", default="Memory empty for agent {agent_id}", agent_id=self.agent.id))
                return None

            # Get valid states directly from the pre-allocated tensor and move to CPU
            input_tensors = self.agent.xai_memory.states[:self.agent.xai_memory.size].to(self.device)

            baselines = torch.zeros_like(input_tensors)
            
            # Run Integrated Gradients
            # n_steps=25 is sufficient for TCN and saves computation time/memory compared to default 50
            attributions, _ = self.ig.attribute(input_tensors, baselines, target=0, return_convergence_delta=True, n_steps=25)
            
            # Aggregation for TCN
            attributions = attributions.abs().sum(dim=0).sum(dim=0)

            # Normalization
            if torch.norm(attributions) > 0:
                attributions = attributions / torch.norm(attributions)
            
            importances = attributions.cpu().detach().numpy()
            
            # Mapping with Glossary
            feature_glossary = self._get_feature_glossary()
            analysis_data = []
            
            for i, importance in enumerate(importances):
                if isinstance(feature_glossary, list) and i < len(feature_glossary):
                    f_info = feature_glossary[i]
                    name = f_info.get("feature_name", f"Feature {i}")
                    desc = f_info.get("description", "N/A")
                elif isinstance(feature_glossary, dict):
                    f_info = feature_glossary.get(i, {"name": f"Feature {i}", "description": "N/A"})
                    name = f_info.get("name", f"Feature {i}")
                    desc = f_info.get("description", "N/A")
                else:
                    name = f"Feature {i}"
                    desc = "N/A"

                analysis_data.append({
                    "name": name, 
                    "importance": float(importance), 
                    "description": desc
                })

            # Ordering
            total_importance = sum(item['importance'] for item in analysis_data)
            for item in analysis_data:
                item['normalized_importance'] = (item['importance'] / total_importance) if total_importance > 0 else 0
            
            sorted_analysis = sorted(analysis_data, key=lambda x: x['importance'], reverse=True)

            # 1. Generate Chart (PNG) - Using Object-Oriented Approach
            names = [x['name'] for x in sorted_analysis[:15]]
            values = [x['importance'] for x in sorted_analysis[:15]]
            
            plt.close('all')
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(names, values, color='skyblue')
            
            xlabel_text = lm.get_string("xai_report.chart_xlabel", default="Importance")
            title_text = lm.get_string("xai_report.chart_title", default="Feature Importance Analysis - Agent {agent_id}", agent_id=self.agent.id)
            
            ax.set_xlabel(xlabel_text)
            ax.set_title(title_text)
            ax.invert_yaxis()
            
            plt.tight_layout()
            
            fig.savefig(self.output_path_png)
            plt.close(fig)

            # 2. Generate Text Report (TXT)
            with open(self.output_path_txt, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                
                title = lm.get_string("xai_report.title", default="XAI Analysis Report - Agent {agent_id}", agent_id=self.agent.id)
                f.write(title + "\n")
                
                subtitle = lm.get_string("xai_report.subtitle", default="Generated on: {timestamp}", timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                f.write(subtitle + "\n")
                
                f.write("=" * 60 + "\n\n")
                
                header_desc = lm.get_string("xai_report.header_description", default="This report presents the importance of each sensor (feature) for the agent's decision making, based on the Integrated Gradients method.")
                f.write(header_desc + "\n\n")

                lbl_sensor = lm.get_string('xai_report.section_sensor', default="Sensor")
                lbl_importance = lm.get_string('xai_report.section_importance', default="Importance")
                lbl_desc = lm.get_string('xai_report.section_description', default="Description")

                for item in sorted_analysis:
                    bar_length = 20
                    filled_length = int(item['normalized_importance'] * bar_length)
                    bar = '█' * filled_length + '─' * (bar_length - filled_length)
                    
                    f.write(f"● {lbl_sensor}: {item['name']}\n")
                    f.write(f"  {lbl_importance}: {bar} ({item['importance']:.4f})\n")
                    f.write(f"  {lbl_desc}: {item['description']}\n")
                    f.write("-" * 60 + "\n")
            
            logging.info(lm.get_string("captum_analyzer.run.text_report_success", default="Text report saved to {path}", path=self.output_path_txt))

            return {
                "image_path": os.path.abspath(self.output_path_png),
                "text_path": os.path.abspath(self.output_path_txt)
            }

        except Exception as e:
            logging.error(lm.get_string("captum_analyzer.run.analysis_error", default="Analysis failed: {error}", error=e), exc_info=True)
            return None
        finally:
            if original_mode_is_training: 
                self.agent.policy_net.train()