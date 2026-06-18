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

# File: src/analysis/warrant_math.py
# Author: Gabriel Moraes
# Date: 2026-06-10
#
# Pure traffic engineering mathematical functions.

MS_TO_KMH = 3.6
MIN_SPEED_THRESHOLD = 0.1

def compute_volume_q(density: float, speed_ms: float) -> float:
    """
    Computes volume (q) using the fundamental flow equation: q = k * v
    density (k) in veh/km, speed (v) in m/s converted to km/h.
    Returns: volume in veh/hour (vph).
    """
    return density * (speed_ms * MS_TO_KMH)

def compute_delay(edge_length: float, v_real: float, v_limit: float) -> float:
    """
    Computes delay per vehicle: D = L/v_real - L/v_limit
    Returns delay in seconds.
    """
    if edge_length > 0 and v_real > MIN_SPEED_THRESHOLD and v_limit > MIN_SPEED_THRESHOLD:
        return max(0.0, (edge_length / v_real) - (edge_length / v_limit))
    return 0.0

def compute_p95(values: list) -> float:
    """
    Computes the 95th percentile of a list of values.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * 0.95)
    return float(sorted_vals[min(idx, len(sorted_vals) - 1)])

def compute_saturation_ratio(volume_q: float, num_lanes: int, f_ideal: float) -> float:
    """
    Computes volume/capacity ratio (X = q / C).
    Capacity C = N * F_ideal.
    """
    if num_lanes <= 0:
        num_lanes = 1
    capacity = num_lanes * f_ideal
    if capacity > 0:
        return volume_q / capacity
    return 0.0
