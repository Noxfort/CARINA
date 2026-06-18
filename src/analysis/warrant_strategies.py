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

# File: src/analysis/warrant_strategies.py
# Author: Gabriel Moraes
# Date: 2026-06-10

from abc import ABC, abstractmethod
from analysis.warrant_math import compute_volume_q, compute_delay, compute_p95, compute_saturation_ratio

class BaseWarrant(ABC):
    @abstractmethod
    def evaluate(self, all_edges: dict, primary_edges: dict, secondary_edges: dict, params: dict) -> dict:
        pass

class VolumeWarrant(BaseWarrant):
    def evaluate(self, all_edges: dict, primary_edges: dict, secondary_edges: dict, params: dict) -> dict:
        min_primary = params.get('min_volume_primary', 500)
        min_secondary = params.get('min_volume_secondary', 150)
        
        vol_primary = self._compute_avg_volume(primary_edges)
        vol_secondary = self._compute_avg_volume(secondary_edges)

        met = (vol_primary >= min_primary and vol_secondary >= min_secondary)

        return {
            'met': met,
            'avg_volume_primary': round(vol_primary, 1),
            'avg_volume_secondary': round(vol_secondary, 1),
            'threshold_primary': min_primary,
            'threshold_secondary': min_secondary,
        }

    def _compute_avg_volume(self, edges: dict) -> float:
        all_volumes = []
        for edge_id, samples in edges.items():
            for s in samples:
                density = s.get('density', 0)
                speed = s.get('mean_speed', 0)
                q = compute_volume_q(density, speed)
                all_volumes.append(q)
        return sum(all_volumes) / len(all_volumes) if all_volumes else 0.0

class DelayWarrant(BaseWarrant):
    def evaluate(self, all_edges: dict, primary_edges: dict, secondary_edges: dict, params: dict) -> dict:
        unacceptable_delay = params.get('unacceptable_delay', 90.0)
        all_delays = []

        for edge_id, samples in secondary_edges.items():
            for s in samples:
                edge_length = s.get('edge_length', 0)
                v_real = s.get('mean_speed', 0)
                v_limit = s.get('speed_limit', 0)
                delay = compute_delay(edge_length, v_real, v_limit)
                if edge_length > 0 and v_real > 0.1: # Only track valid samples
                    all_delays.append(delay)

        avg_delay = sum(all_delays) / len(all_delays) if all_delays else 0.0
        met = avg_delay > unacceptable_delay

        return {
            'met': met,
            'avg_delay': round(avg_delay, 2),
            'threshold': unacceptable_delay,
            'sample_count': len(all_delays),
        }

class QueueWarrant(BaseWarrant):
    def evaluate(self, all_edges: dict, primary_edges: dict, secondary_edges: dict, params: dict) -> dict:
        max_queue_p95 = params.get('max_queue_p95', 15)
        all_queues = []

        for edge_id, samples in all_edges.items():
            for s in samples:
                all_queues.append(s.get('queue_length', 0))

        p95 = compute_p95(all_queues)
        met = p95 > max_queue_p95

        return {
            'met': met,
            'p95_value': p95,
            'threshold': max_queue_p95,
            'sample_count': len(all_queues),
            'avg_queue': round(sum(all_queues) / len(all_queues), 1) if all_queues else 0,
        }

class SaturationWarrant(BaseWarrant):
    def evaluate(self, all_edges: dict, primary_edges: dict, secondary_edges: dict, params: dict) -> dict:
        saturation_critical = params.get('saturation_critical', 0.85)
        f_ideal = params.get('ideal_flow_per_lane', 1800)
        edge_ratios = {}

        for edge_id, samples in all_edges.items():
            volumes = []
            num_lanes = 1
            for s in samples:
                density = s.get('density', 0)
                speed = s.get('mean_speed', 0)
                q = compute_volume_q(density, speed)
                volumes.append(q)
                nl = s.get('num_lanes')
                if nl and nl > 0:
                    num_lanes = nl

            avg_q = sum(volumes) / len(volumes) if volumes else 0.0
            x_ratio = compute_saturation_ratio(avg_q, num_lanes, f_ideal)
            edge_ratios[edge_id] = round(x_ratio, 4)

        max_x = max(edge_ratios.values()) if edge_ratios else 0.0
        met = max_x > saturation_critical

        return {
            'met': met,
            'max_x_ratio': round(max_x, 4),
            'threshold': saturation_critical,
            'edge_ratios': edge_ratios,
        }
