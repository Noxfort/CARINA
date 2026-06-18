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

# File: src/engine/mfd/snapshot.py
# Author: Gabriel Moraes
# Date: June 15, 2026

"""
MFD Snapshot — Immutable Data Transfer Object.

Represents a single point-in-time measurement of network-wide
traffic performance metrics derived from the Macroscopic Fundamental Diagram.
"""


class MFDSnapshot:
    """Immutable record of a single MFD computation at a point in time."""
    __slots__ = (
        'timestamp', 'accumulation', 'production',
        'mean_speed', 'mean_density', 'mean_flow',
        'efficiency', 'congestion_ratio', 'active_edges'
    )

    def __init__(self, timestamp: float, accumulation: float, production: float,
                 mean_speed: float, mean_density: float, mean_flow: float,
                 efficiency: float, congestion_ratio: float, active_edges: int):
        self.timestamp = timestamp
        self.accumulation = accumulation
        self.production = production
        self.mean_speed = mean_speed
        self.mean_density = mean_density
        self.mean_flow = mean_flow
        self.efficiency = efficiency
        self.congestion_ratio = congestion_ratio
        self.active_edges = active_edges

    def to_dict(self) -> dict:
        """Serializes the snapshot into a JSON-safe dictionary."""
        return {
            'timestamp': round(self.timestamp, 2),
            'accumulation': round(self.accumulation, 4),
            'production': round(self.production, 4),
            'mean_speed': round(self.mean_speed, 2),
            'mean_density': round(self.mean_density, 4),
            'mean_flow': round(self.mean_flow, 4),
            'efficiency': round(self.efficiency, 4),
            'congestion_ratio': round(self.congestion_ratio, 4),
            'active_edges': self.active_edges
        }

    @staticmethod
    def empty(sim_time: float, assume_optimal: bool = True) -> 'MFDSnapshot':
        """Factory method for a zeroed snapshot when no data is available."""
        return MFDSnapshot(
            timestamp=sim_time,
            accumulation=0.0,
            production=0.0,
            mean_speed=0.0,
            mean_density=0.0,
            mean_flow=0.0,
            efficiency=1.0 if assume_optimal else 0.0,
            congestion_ratio=0.0,
            active_edges=0
        )
