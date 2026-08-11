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

# File: src/engine/mfd/mfd.py
# Author: Gabriel Moraes
# Date: June 15, 2026

"""
Macroscopic Fundamental Diagram (MFD) — Facade Orchestrator.

Coordinates the MFD subsystem components (Calculator, Tracker, Classifier)
to provide a single, clean API for the rest of the CARINA engine.

This class does NOT perform calculations, track state, or classify networks
itself. It delegates each responsibility to the appropriate specialist.
"""

import logging
import sumolib
from typing import Dict, Any, Optional, List

from mfd.snapshot import MFDSnapshot
from mfd.calculator import MFDCalculator
from mfd.tracker import MFDTracker
from mfd.classifier import MFDClassifier

logger = logging.getLogger(__name__)


class MacroscopicFundamentalDiagram:
    """
    Facade for the MFD subsystem.

    Provides the same public API that the rest of the system expects,
    while internally delegating to:
        - MFDCalculator: Pure fluidic math
        - MFDTracker: History, peaks, EMA
        - MFDClassifier: Network state classification

    Usage:
        mfd = MacroscopicFundamentalDiagram()
        mfd.load_topology("path/to/network.net.xml")
        ...
        snapshot = mfd.compute_step(edges_data, sim_time)
        print(f"Efficiency: {snapshot.efficiency:.1%}")
    """

    # Free-flow speed reference (m/s) — 50 km/h urban default
    DEFAULT_FREE_FLOW_SPEED = 13.89

    def __init__(self, free_flow_speed: float = DEFAULT_FREE_FLOW_SPEED):
        """
        Args:
            free_flow_speed: Reference free-flow speed in m/s (default: 13.89 ≈ 50 km/h).
        """
        self.free_flow_speed = free_flow_speed

        # Edge topology: edge_id -> length in meters
        self._edge_lengths: Dict[str, float] = {}
        self._total_network_length: float = 0.0
        self._topology_loaded: bool = False

        # Delegates
        self._tracker = MFDTracker()
        self._calculator = MFDCalculator
        self._classifier = MFDClassifier

        logger.info("[MFD] Macroscopic Fundamental Diagram engine initialized.")

    # ─────────────────────────────────────────────────────────
    # Topology Loading
    # ─────────────────────────────────────────────────────────

    def load_topology(self, net_file_path: str) -> None:
        """
        Extracts edge lengths from the SUMO .net.xml file.
        These lengths are essential for weighting flow and density
        into physically meaningful production and accumulation values.

        Args:
            net_file_path: Absolute path to the .net.xml network file.
        """
        self._edge_lengths.clear()

        try:
            net = sumolib.net.readNet(net_file_path, withInternal=False)

            for edge in net.getEdges():
                edge_id = edge.getID()
                length = edge.getLength()

                if length > 0:
                    self._edge_lengths[edge_id] = length

            self._total_network_length = sum(self._edge_lengths.values())
            self._topology_loaded = True

            logger.info(
                f"[MFD] Topology loaded: {len(self._edge_lengths)} edges, "
                f"total network length: {self._total_network_length:.1f}m"
            )

        except Exception as e:
            logger.error(f"[MFD] Failed to load topology from {net_file_path}: {e}", exc_info=True)
            self._topology_loaded = False

    # ─────────────────────────────────────────────────────────
    # Core Step Computation (Facade)
    # ─────────────────────────────────────────────────────────

    def compute_step(self, edges_data: Dict[str, Dict[str, Any]], sim_time: float, intersections: dict = None) -> MFDSnapshot:
        """
        Computes network-wide MFD metrics for the current simulation step.

        Args:
            edges_data: Dictionary of edge_id -> {occupancy, mean_speed, queue_length, density}.
            sim_time: Current simulation time in seconds.
            intersections: Optional dictionary of intersection metrics at this step.

        Returns:
            MFDSnapshot with all computed metrics for this instant.
        """
        if not edges_data:
            snapshot = MFDSnapshot.empty(sim_time, assume_optimal=not self._tracker.is_warmed_up)
            self._tracker.record(snapshot)
            return snapshot

        # 1. Delegate computation to the Calculator
        production, accumulation, mean_speed, mean_density, mean_flow, active_edges = (
            self._calculator.compute_network_metrics(
                edges_data, self._edge_lengths, self._topology_loaded
            )
        )

        # 2. Compute derived metrics using the Tracker's peak state
        if self._tracker.is_warmed_up:
            efficiency = self._calculator.compute_efficiency(
                production, self._tracker.peak_production
            )
            congestion_ratio = self._calculator.compute_congestion_ratio(
                accumulation, self._tracker.peak_accumulation
            )
        else:
            efficiency = 1.0  # During warmup, assume optimal
            congestion_ratio = 0.0

        # 3. Build the snapshot
        snapshot = MFDSnapshot(
            timestamp=sim_time,
            accumulation=accumulation,
            production=production,
            mean_speed=mean_speed,
            mean_density=mean_density,
            mean_flow=mean_flow,
            efficiency=efficiency,
            congestion_ratio=congestion_ratio,
            active_edges=active_edges,
            intersections=intersections
        )

        # 4. Delegate tracking to the Tracker
        self._tracker.record(snapshot)

        return snapshot

    # ─────────────────────────────────────────────────────────
    # Accessors (Delegate to Tracker / Classifier)
    # ─────────────────────────────────────────────────────────

    def get_latest(self) -> Optional[MFDSnapshot]:
        """Returns the most recent MFD computation, or None if no data."""
        return self._tracker.get_latest()

    def get_smoothed_metrics(self) -> Dict[str, float]:
        """Returns the EMA-smoothed production and accumulation for the UI."""
        return self._tracker.get_smoothed_metrics()

    def get_curve_data(self, last_n: int = 0) -> List[Dict[str, float]]:
        """Returns MFD curve data points (accumulation vs production) for plotting."""
        return self._tracker.get_curve_data(last_n)

    def get_network_report(self) -> Dict[str, Any]:
        """Generates a comprehensive network performance report."""
        return self._classifier.generate_report(self._tracker)

    def reset(self) -> None:
        """Resets all MFD state for a new session. Preserves topology."""
        self._tracker.reset()
        logger.info("[MFD] State reset. Topology preserved.")
