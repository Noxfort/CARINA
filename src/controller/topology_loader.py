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

# File: src/controller/topology_loader.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Topology Loader
---------------
Handles loading and processing of SUMO network topology files for the fixed-time controller.
"""

import logging
from typing import List, Tuple
from dataclasses import dataclass

from src.controller.common_types import PhaseDefinition
from src.controller.phase_extractor import extract_green_phases
from src.controller.phase_derivator import derive_yellow_state
from src.controller.phase_validator import validate_phases

logger = logging.getLogger(__name__)


@dataclass
class IntersectionData:
    """Data structure for intersection information."""
    tls_id: str
    phase_definitions: List[PhaseDefinition]


class TopologyLoader:
    """
    Handles loading and processing of SUMO network topology files.
    
    This class is responsible for:
    - Parsing SUMO .net.xml files
    - Extracting traffic light programs
    - Processing phases for fixed-time control
    """
    
    def __init__(self, green_chars: frozenset = frozenset({'G', 'g'})):
        """
        Args:
            green_chars: Set of characters considered as green signals in SUMO
        """
        self._green_chars = green_chars

    def load_topology(self, net_file_path: str) -> Tuple[List[IntersectionData], bool]:
        """
        Extract TLS programs from the SUMO .net.xml network file.
        
        Args:
            net_file_path: Absolute path to the .net.xml file.
            
        Returns:
            Tuple of (list of intersection data, success flag)
        """
        try:
            import sumolib  # type: ignore
            net = sumolib.net.readNet(net_file_path, withInternal=False)
        except ImportError:
            logger.error("[TopologyLoader] sumolib not available. Cannot load topology.")
            return [], False
        except Exception as e:
            logger.error(f"[TopologyLoader] Failed to parse network file '{net_file_path}': {e}")
            return [], False

        tls_list = net.getTrafficLights()
        if not tls_list:
            logger.warning("[TopologyLoader] No traffic lights found in topology.")
            return [], False

        intersections = []
        loaded_count = 0
        for tls in tls_list:
            tls_id = tls.getID()
            programs = tls.getPrograms()

            if not programs:
                logger.warning(f"[TopologyLoader] TLS '{tls_id}' has no programs. Skipping.")
                continue

            # Use the first (default) program — program ID "0" in SUMO convention
            program = list(programs.values())[0]
            original_phases = program.getPhases()

            # Extract GREEN phases (phases that have actual green movement)
            # Filter out pure-yellow and pure-red transitional phases
            green_phases = extract_green_phases(tls_id, original_phases, self._green_chars)

            if not green_phases:
                logger.warning(
                    f"[TopologyLoader] TLS '{tls_id}' has no usable green phases. "
                    f"Will remain ALL_RED during failsafe."
                )
                continue

            # Build PhaseDefinitions with derived yellow and all-red strings
            phase_definitions = []
            for state_str in green_phases:
                yellow_str = derive_yellow_state(state_str)
                all_red_str = 'r' * len(state_str)
                phase_definitions.append(PhaseDefinition(
                    state_string=state_str,
                    yellow_string=yellow_str,
                    all_red_string=all_red_str
                ))

            # SAFETY VALIDATION: verify each phase's internal consistency
            if not validate_phases(tls_id, phase_definitions):
                logger.critical(
                    f"[TopologyLoader] ⚠️  VALIDATION FAILED for TLS '{tls_id}'! "
                    f"This intersection will remain ALL_RED permanently during failsafe."
                )
                # Force permanent ALL_RED for this intersection
                signal_len = len(green_phases[0])
                all_red = 'r' * signal_len
                phase_definitions = [PhaseDefinition(
                    state_string=all_red,
                    yellow_string=all_red,
                    all_red_string=all_red
                )]

            intersections.append(IntersectionData(
                tls_id=tls_id,
                phase_definitions=phase_definitions
            ))
            loaded_count += 1

            cycle_length = (2.0 + 4.0 + 15.0) * len(phase_definitions)  # Default timings
            logger.info(
                f"[TopologyLoader] TLS '{tls_id}': {len(phase_definitions)} phases, "
                f"cycle = {cycle_length:.0f}s"
            )

        logger.info(
            f"[TopologyLoader] Topology loaded: {loaded_count} intersections ready "
            f"({len(tls_list) - loaded_count} skipped)."
        )
        return intersections, loaded_count > 0