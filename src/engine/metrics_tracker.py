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

# File: src/engine/metrics_tracker.py
# Author: Gabriel Moraes
# Date: April 15, 2026

from collections import defaultdict
import numpy as np
from typing import Dict, Any
import os
import sys
import configparser
import logging

try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class MetricsTracker:
    """
    Tracks and aggregates PPO metrics (Rewards and Entropies) during an Episode.
    """

    def __init__(self):
        self.episode_metrics = defaultdict(lambda: {'reward': 0.0, 'entropies': []})
        
        self.config = configparser.ConfigParser()
        settings_path = os.path.join(project_root, "config", "settings.ini")
        if os.path.exists(settings_path):
            self.config.read(settings_path)
            
        self.tb_enabled = self.config.getboolean("TENSORBOARD", "tensorboard_enabled", fallback=False)
        self.tb_log_dir = self.config.get("TENSORBOARD", "tensorboard_log_dir", fallback="results/tensorboard")
        
        self.writer = None
        if self.tb_enabled and TENSORBOARD_AVAILABLE:
            full_log_dir = os.path.join(project_root, self.tb_log_dir)
            os.makedirs(full_log_dir, exist_ok=True)
            self.writer = SummaryWriter(log_dir=full_log_dir)
            logging.info(f"[MetricsTracker] TensorBoard habilitado em: {full_log_dir}")
        elif self.tb_enabled and not TENSORBOARD_AVAILABLE:
            logging.warning("[MetricsTracker] TensorBoard ativado via config, mas biblioteca não instalada (pip install tensorboard).")

    def record_step(self, rewards: Dict[str, float], entropies: Dict[str, float]):
        if rewards:
            for tl_id, reward in rewards.items():
                self.episode_metrics[tl_id]['reward'] += reward
                
        if entropies:
            for tl_id, entropy in entropies.items():
                self.episode_metrics[tl_id]['entropies'].append(entropy)

    def finalize_episode(self, episode_number: int = None) -> Dict[str, Dict[str, float]]:
        final_metrics: Dict[str, Dict[str, float]] = {}
        
        for tl_id, data in self.episode_metrics.items():
            mean_entropy = np.mean(data['entropies']) if data['entropies'] else 0.0
            final_metrics[tl_id] = {'reward': data['reward'], 'entropy': mean_entropy}
            
            if self.writer and episode_number is not None:
                self.writer.add_scalar(f'Reward/{tl_id}', data['reward'], episode_number)
                self.writer.add_scalar(f'Entropy/{tl_id}', mean_entropy, episode_number)
                
        return final_metrics
        
    def close(self):
        if self.writer:
            self.writer.close()
