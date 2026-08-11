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

# File: src/sas/sas_helpers.py
# Author: Gabriel Moraes
# Date: July 18, 2026

from typing import Optional, Tuple, Dict, List, Set, Any

class EdgeClassifier:
    """Classifies incoming edges of a junction into primary or secondary lanes based on layout and volumes."""
    
    @staticmethod
    def classify(incoming_edges: Dict[str, Dict[str, Any]], edge_volumes: Dict[str, float]) -> Tuple[List[Tuple[str, Dict[str, Any]]], bool, int, Set[str]]:
        lane_counts = [data['num_lanes'] for data in incoming_edges.values()]
        has_different_lanes = len(set(lane_counts)) > 1
        
        sorted_edges = sorted(incoming_edges.items(), key=lambda item: item[1]['num_lanes'], reverse=True)
        max_lanes = sorted_edges[0][1]['num_lanes'] if sorted_edges else 0
        
        primary_ids = set()
        if not has_different_lanes:
            # If all edges have the same number of lanes, classify by average volume
            # For 3 or more edges, top 2 are primary. Otherwise top 1.
            sorted_by_vol = sorted(incoming_edges.keys(), key=lambda eid: edge_volumes.get(eid, 0.0), reverse=True)
            num_primary = 2 if len(sorted_by_vol) >= 3 else 1
            primary_ids = set(sorted_by_vol[:num_primary])
            
        return sorted_edges, has_different_lanes, max_lanes, primary_ids


class TrafficMetricsCalculator:
    """Performs mathematical calculations for volume, delay, and percentiles."""

    @staticmethod
    def compute_volume(density: float, mean_speed: float) -> float:
        """Calculates volume (flow rate q) from density and speed."""
        return density * (mean_speed * 3.6)

    @staticmethod
    def compute_delay(edge_length: float, mean_speed: float, speed_limit: float) -> float:
        """Calculates accumulated delay relative to speed limit free flow."""
        if edge_length > 0.0 and mean_speed > 0.1:
            return max(0.0, (edge_length / mean_speed) - (edge_length / speed_limit))
        return 0.0

    @staticmethod
    def compute_adjusted_speed(edge_length: float, avg_delay: float, speed_limit: float) -> float:
        """Computes average speed adjusted by delay."""
        if edge_length > 0.0 and (avg_delay + edge_length / speed_limit) > 0.0:
            return edge_length / (avg_delay + edge_length / speed_limit)
        return speed_limit

    @staticmethod
    def get_percentile(freq_map: Dict[int, int], p: float) -> int:
        """Gets the p-th percentile from a frequency distribution mapping."""
        tot = sum(freq_map.values())
        if tot == 0:
            return 0
        target = tot * p
        acc = 0
        for val in sorted(freq_map.keys()):
            acc += freq_map[val]
            if acc >= target:
                return val
        return max(freq_map.keys())


class SyntheticSampleGenerator:
    """Generates lists of synthetic samples for compatibility downstream."""

    @staticmethod
    def generate_historical(edge_id: str, avg_volume: float, adjusted_speed_ms: float, rep_queues: List[int], edge_len: Optional[float], num_lanes: Optional[int], speed_limit: Optional[float]) -> List[Dict[str, Any]]:
        rep_samples = []
        density = avg_volume / (adjusted_speed_ms * 3.6) if adjusted_speed_ms > 0.1 else 0.0
        for q_len in rep_queues:
            rep_samples.append({
                'edge_id': edge_id,
                'density': density,
                'mean_speed': adjusted_speed_ms,
                'queue_length': q_len,
                'occupancy': 0.0,
                'edge_length': edge_len,
                'num_lanes': num_lanes,
                'speed_limit': speed_limit,
                'collected_at': None
            })
        return rep_samples

    @staticmethod
    def generate_accumulated(edge_id: str, density: float, adjusted_speed_ms: float, edge_len: float, num_lanes: int, speed_limit: float) -> List[Dict[str, Any]]:
        rep_samples = []
        for _ in range(100):
            rep_samples.append({
                'edge_id': edge_id,
                'density': density,
                'mean_speed': adjusted_speed_ms,
                'queue_length': 0,
                'occupancy': 0.0,
                'edge_length': edge_len,
                'num_lanes': num_lanes,
                'speed_limit': speed_limit,
                'collected_at': None
            })
        return rep_samples


def formatar_br(val: float, decimals: int = 2) -> str:
    """
    Formats a numeric float/int into Brazilian standard string representation:
    Dot (.) for thousands separator, Comma (,) for decimal separator.
    Example: formatar_br(2241.86) -> "2.241,86"
             formatar_br(450.0, 1) -> "450,0"
    """
    if val is None:
        return "0,00"
    try:
        fmt_str = f"{{:,.{decimals}f}}"
        formatted = fmt_str.format(float(val))
        return formatted.replace(",", "TMP").replace(".", ",").replace("TMP", ".")
    except Exception:
        return str(val)
