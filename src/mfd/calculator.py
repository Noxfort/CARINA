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

# File: src/engine/mfd/calculator.py
# Author: Gabriel Moraes
# Date: June 15, 2026

"""
MFD Calculator — Pure Fluidic Computation Engine.

Implements the core mathematical equations of the Macroscopic Fundamental
Diagram (Geroliminis & Daganzo, 2008) without any state or side effects.

Core Equations (Traffic Flow Theory):
    q = k × v           (Flow = Density × Speed)
    Production   = Σ (q_i × L_i)   for each edge i
    Accumulation = Σ (k_i × L_i)   for each edge i

Where:
    q_i = flow on edge i (veh/s)
    k_i = density on edge i (veh/m)
    v_i = mean speed on edge i (m/s)
    L_i = length of edge i (m)
"""

from typing import Dict, Any, Tuple


class MFDCalculator:
    """
    Stateless calculator that transforms raw edge-level fluidic data
    into network-wide MFD metrics. Contains no history or tracking logic.

    All methods are pure functions: same input always produces the same output.
    """

    # Default edge length fallback when topology is not loaded (meters)
    DEFAULT_EDGE_LENGTH = 100.0

    @staticmethod
    def compute_network_metrics(
        edges_data: Dict[str, Dict[str, Any]],
        edge_lengths: Dict[str, float],
        topology_loaded: bool = False
    ) -> Tuple[float, float, float, float, float, int]:
        """
        Computes network-wide MFD metrics from per-edge fluidic data.

        Args:
            edges_data: Dictionary of edge_id -> {occupancy, mean_speed, queue_length, density}.
            edge_lengths: Dictionary of edge_id -> length in meters.
            topology_loaded: Whether the topology has been loaded (affects fallback behavior).

        Returns:
            Tuple of:
                - total_production (float): Network production in veh·m/s.
                - total_accumulation (float): Network accumulation in veh.
                - mean_speed (float): Length-weighted average speed in m/s.
                - mean_density (float): Length-weighted average density.
                - mean_flow (float): Length-weighted average flow.
                - active_edges (int): Number of edges with data.
        """
        total_production = 0.0
        total_accumulation = 0.0
        total_weighted_speed = 0.0
        total_weighted_density = 0.0
        total_weighted_flow = 0.0
        total_weight = 0.0
        active_edges = 0

        default_length = MFDCalculator.DEFAULT_EDGE_LENGTH

        for edge_id, data in edges_data.items():
            # Get edge length (fallback to default if topology not loaded)
            length = edge_lengths.get(edge_id, default_length) if topology_loaded else default_length

            # Extract fluidic variables
            density = data.get('density', 0.0)      # veh/m (or normalized)
            speed = data.get('mean_speed', 0.0)      # m/s
            occupancy = data.get('occupancy', 0.0)   # 0.0 to 1.0

            # If density is not available, estimate from occupancy
            # Occupancy ≈ density × average_vehicle_length / lane_length
            # For normalized values, we use occupancy directly as a density proxy
            if density <= 0 and occupancy > 0:
                density = occupancy

            # Fundamental equation: Flow = Density × Speed
            flow = density * speed  # veh/s (per unit length)

            # Network Production: Σ(flow_i × length_i) — veh·m/s
            total_production += flow * length

            # Network Accumulation: Σ(density_i × length_i) — veh
            total_accumulation += density * length

            # Weighted averages (by edge length)
            total_weighted_speed += speed * length
            total_weighted_density += density * length
            total_weighted_flow += flow * length
            total_weight += length
            active_edges += 1

        # Compute network-wide averages
        if total_weight > 0:
            mean_speed = total_weighted_speed / total_weight
            mean_density = total_weighted_density / total_weight
            mean_flow = total_weighted_flow / total_weight
        else:
            mean_speed = 0.0
            mean_density = 0.0
            mean_flow = 0.0

        return (
            total_production,
            total_accumulation,
            mean_speed,
            mean_density,
            mean_flow,
            active_edges
        )

    @staticmethod
    def compute_efficiency(current_production: float, peak_production: float) -> float:
        """
        Computes the production efficiency ratio (0.0 to 1.0).

        Args:
            current_production: Current step's network production.
            peak_production: Maximum observed network production (MFD peak).

        Returns:
            Efficiency ratio, clamped to [0.0, 1.0].
        """
        if peak_production <= 0:
            return 1.0
        return min(current_production / peak_production, 1.0)

    @staticmethod
    def compute_congestion_ratio(current_accumulation: float, peak_accumulation: float) -> float:
        """
        Computes how far the network is past the critical density.

        Args:
            current_accumulation: Current step's network accumulation.
            peak_accumulation: Accumulation at peak production (critical density).

        Returns:
            Congestion ratio. < 1.0 = free flow, > 1.0 = congested.
        """
        if peak_accumulation <= 0:
            return 0.0
        return current_accumulation / peak_accumulation
