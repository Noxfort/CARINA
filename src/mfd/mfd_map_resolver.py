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

# File: src/mfd/mfd_map_resolver.py
# Author: Gabriel Moraes
# Date: 2026

import os
import logging
from typing import List

class MFDMapResolver:
    """
    Responsibility: Resolve active SUMO network topology (.net.xml) and discover
    real signalized traffic light junction IDs under CARINA active control.
    Adheres strictly to Single Responsibility Principle (SRP).
    """

    @staticmethod
    def discover_signalized_ids() -> List[str]:
        """
        Dynamically inspects active results directories to discover junctions
        with type="traffic_light" from SUMO network XML file.
        Returns empty list if discovery fails or no signalized junctions are found.
        """
        try:
            from utils.paths import get_base_output_dir
            results_dir = os.path.join(get_base_output_dir(), "results")
            if os.path.exists(results_dir):
                for root, dirs, files in os.walk(results_dir):
                    for f in files:
                        if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                            net_file = os.path.join(root, f)
                            try:
                                import sumolib
                                net = sumolib.net.readNet(net_file, withInternal=False)
                                tls = [node.getID() for node in net.getNodes() if node.getType() == "traffic_light"]
                                if tls:
                                    logging.info(f"[MFDMapResolver] Dynamically discovered {len(tls)} signalized IDs from {net_file}: {tls}")
                                    return tls
                            except Exception as e:
                                logging.debug(f"[MFDMapResolver] sumolib read error on {net_file}: {e}")
        except Exception as e:
            logging.warning(f"[MFDMapResolver] Error discovering signalized IDs: {e}")

        logging.warning("[MFDMapResolver] No signalized junctions discovered in network map. Returning empty list.")
        return []
