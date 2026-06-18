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

# File: src/engine/episode_reporter.py
# Author: Gabriel Moraes
# Date: 2026-06-15

"""
Component responsible for generating episode reports, such as the School Bulletin,
and managing episode-level tracking.
"""

from collections import Counter
from typing import Dict, Any

from core.enums import Maturity
from core.system_reporter import SystemReporter

class EpisodeReporter:
    """
    Component specialized in logging detailed reports at the end of each training episode.
    """
    def __init__(self, locale_manager: Any, maturity_manager: Any):
        self.lm = locale_manager
        self.maturity_manager = maturity_manager

    def report_episode_bulletin(self, agents: Dict[str, Any], episode_counter: int, episode_total_reward: float) -> None:
        """
        Logs the detailed 'School Bulletin' at the end of each episode.
        
        Legacy format:
        ────────────────────────────────────────────────────────────
        END OF EPISODE {N} | SCHOOL BULLETIN
          - Episode Performance: Total Reward = {R}
          - Class Status: {A} Adults | {T} Teens | {C} Children
          - Confidence Calibration Status: Ongoing
        ────────────────────────────────────────────────────────────
        """
        maturity_counts = Counter()
        for tl_id in agents:
            phase = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
            maturity_counts[phase] += 1
        
        calibration_status = self.lm.get_string("reporter.calib_status_done") if self.maturity_manager.is_calibrated else self.lm.get_string("reporter.calib_status_ongoing")
        
        SystemReporter.report_school_bulletin(
            lm=self.lm,
            episode_count=episode_counter,
            total_reward=episode_total_reward,
            maturity_counts=maturity_counts,
            calibration_status=calibration_status
        )
