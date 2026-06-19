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

# File: src/xai/feature_aggregator.py
# Author: Gabriel Moraes
# Date: June 19, 2026

import logging
import numpy as np
from typing import Optional, Dict, Any, List
from utils.locale_manager_backend import LocaleManagerBackend
from agents.local_agent import LocalAgent

class FeatureAggregator:
    """
    Responsibility: Resolve topology, expand feature glossary with PAE, 
    and group raw feature importances into semantic categories.
    """
    def __init__(self, agent: LocalAgent, locale_manager: LocaleManagerBackend, feature_glossary: Optional[Any] = None) -> None:
        self.agent = agent
        self.locale_manager = locale_manager
        self.feature_glossary = feature_glossary if feature_glossary is not None else {}
        self._expand_glossary_with_pae()

    def _expand_glossary_with_pae(self) -> None:
        shared_pae = getattr(self.agent, 'shared_pae', None)
        if shared_pae is None:
            return
        
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
        
        logging.info(f"[FeatureAggregator] Feature glossary expanded with {latent_dim} PAE latent features")

    def _resolve_topology_dims(self, n_obs: int) -> tuple:
        """
        Dynamically infers the number of incoming edges and active phases 
        for the given observation vector dimension of an agent.
        """
        for num_edges in range(12, 0, -1):
            num_phases = n_obs - 1 - 3 * num_edges
            if 2 <= num_phases <= 8:
                return num_edges, num_phases
        # Fallback default
        num_edges = (n_obs - 3) // 3
        num_phases = n_obs - 1 - 3 * num_edges
        return max(1, num_edges), max(1, num_phases)

    def aggregate(self, importances: np.ndarray) -> List[Dict[str, Any]]:
        # Mapping with Glossary
        analysis_data = []
        for i, importance in enumerate(importances):
            if isinstance(self.feature_glossary, list) and i < len(self.feature_glossary):
                f_info = self.feature_glossary[i]
                name = f_info.get("feature_name", f"Feature {i}")
                desc = f_info.get("description", "N/A")
            elif isinstance(self.feature_glossary, dict):
                f_info = self.feature_glossary.get(i, {"name": f"Feature {i}", "description": "N/A"})
                name = f_info.get("name", f"Feature {i}")
                desc = f_info.get("description", "N/A")
            else:
                name = f"Feature {i}"
                desc = "N/A"

            analysis_data.append({
                "name": name, 
                "importance": float(importance), 
                "description": desc,
                "index": i
            })

        # Grouping in blocks/categories per agent
        num_edges, num_phases = self._resolve_topology_dims(len(importances))
        
        categories = {
            "occupancy": {
                "name": self.locale_manager.get_string("xai_report.categories.occupancy.name", default="Lane Occupancy"),
                "desc": self.locale_manager.get_string("xai_report.categories.occupancy.description", default="Traffic volume occupancy rate on incoming lanes."),
                "val": 0.0
            },
            "speed": {
                "name": self.locale_manager.get_string("xai_report.categories.speed.name", default="Average Speed"),
                "desc": self.locale_manager.get_string("xai_report.categories.speed.description", default="Average speed of incoming vehicles."),
                "val": 0.0
            },
            "queue": {
                "name": self.locale_manager.get_string("xai_report.categories.queue.name", default="Queue Lengths"),
                "desc": self.locale_manager.get_string("xai_report.categories.queue.description", default="Physical length of vehicle queues on incoming lanes."),
                "val": 0.0
            },
            "phase": {
                "name": self.locale_manager.get_string("xai_report.categories.phase.name", default="Active Phase"),
                "desc": self.locale_manager.get_string("xai_report.categories.phase.description", default="Currently active traffic light phase configuration."),
                "val": 0.0
            },
            "pedestrian": {
                "name": self.locale_manager.get_string("xai_report.categories.pedestrian.name", default="Pedestrian Calls"),
                "desc": self.locale_manager.get_string("xai_report.categories.pedestrian.description", default="Pedestrian crossing requests registered at the intersection."),
                "val": 0.0
            },
            "pae": {
                "name": self.locale_manager.get_string("xai_report.categories.pae.name", default="AI Predictions (PAE Latent)"),
                "desc": self.locale_manager.get_string("xai_report.categories.pae.description", default="Predictive latent feature projections from the autoencoder."),
                "val": 0.0
            },
            "strategic": {
                "name": self.locale_manager.get_string("xai_report.categories.strategic.name", default="Strategic Coordination"),
                "desc": self.locale_manager.get_string("xai_report.categories.strategic.description", default="Coordination signals received from adjacent traffic controllers."),
                "val": 0.0
            },
            "other": {
                "name": self.locale_manager.get_string("xai_report.categories.other.name", default="Other / Padding"),
                "desc": self.locale_manager.get_string("xai_report.categories.other.description", default="Padding dimensions or other auxiliary variables."),
                "val": 0.0
            }
        }
        
        for item in analysis_data:
            name = item["name"]
            idx = item["index"]
            val = item["importance"]
            
            # Grouping rules
            if "PAE_latent_" in name or "PAE" in name:
                categories["pae"]["val"] += val
            elif "Strategic Vector" in name:
                categories["strategic"]["val"] += val
            elif "Padding" in name:
                categories["other"]["val"] += val
            else:
                # Index-based grouping
                if idx < 3 * num_edges:
                    sub_idx = idx % 3
                    if sub_idx == 0:
                        categories["occupancy"]["val"] += val
                    elif sub_idx == 1:
                        categories["speed"]["val"] += val
                    else:
                        categories["queue"]["val"] += val
                elif 3 * num_edges <= idx < 3 * num_edges + num_phases:
                    categories["phase"]["val"] += val
                elif idx == 3 * num_edges + num_phases:
                    categories["pedestrian"]["val"] += val
                else:
                    categories["other"]["val"] += val
        
        # Re-normalize/organize grouped data
        grouped_analysis = []
        for cat_key, cat_info in categories.items():
            if cat_info["val"] > 0 or cat_key in ["occupancy", "speed", "queue", "phase"]: # Keep main categories always
                grouped_analysis.append({
                    "name": cat_info["name"],
                    "importance": cat_info["val"],
                    "description": cat_info["desc"]
                })
        
        # Sort grouped analysis by importance
        total_grouped_importance = sum(x["importance"] for x in grouped_analysis)
        for item in grouped_analysis:
            item["normalized_importance"] = (item["importance"] / total_grouped_importance) if total_grouped_importance > 0 else 0
            
        return sorted(grouped_analysis, key=lambda x: x["importance"], reverse=True)
