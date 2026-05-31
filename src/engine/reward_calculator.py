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

# File: src/engine/reward_calculator.py (ALREADY COMPLIANT)
# Author: Gabriel Moraes
# Date: October 1, 2025

import logging
import configparser
from typing import TYPE_CHECKING, Dict, List, Any

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class RewardCalculator:
    """The environment 'Judge': specialist in calculating the reward from pre-collected data."""

    def __init__(self, settings: configparser.ConfigParser, locale_manager: 'LocaleManagerBackend') -> None:
        """
        Inicializa o RewardCalculator.
        """
        self.locale_manager = locale_manager
        lm = self.locale_manager
        self.last_step_total_flow = 0

        try:
            reward_weights_section = settings['REWARD_WEIGHTS']
            self.reward_weights = {
                'waiting_time': reward_weights_section.getfloat('weight_waiting_time'),
                'flow': reward_weights_section.getfloat('weight_flow'),
                'emergency_brake': reward_weights_section.getfloat('weight_emergency_brake'),
                'teleport': reward_weights_section.getfloat('weight_teleport')
            }
        except (configparser.NoSectionError, KeyError):
            logging.error(lm.get_string("reward_calculator.init.config_error"))
            self.reward_weights = {'waiting_time': -1.0, 'flow': 1.0, 'emergency_brake': -10.0, 'teleport': -10.0}

        logging.info(lm.get_string("reward_calculator.init.judge_created"))
        logging.info(lm.get_string("reward_calculator.init.weights_loaded", weights=self.reward_weights))


    def calculate_rewards_from_batch(self, traffic_light_ids: List[str], current_batch: Dict[str, Any], last_batch: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculates the reward for each traffic light using pre-collected data packets.
        """
        rewards = {}
        if not current_batch:
            return rewards

        total_flow_this_step = 0

        teleport_penalty = current_batch.get('sim_starting_teleports_len', 0) * self.reward_weights['teleport']
        emergency_penalty = current_batch.get('sim_emergency_stops_len', 0) * self.reward_weights['emergency_brake']
        global_penalty = teleport_penalty + emergency_penalty

        if global_penalty < 0:
            logging.debug(self.locale_manager.get_string("reward_calculator.batch.global_penalties", penalty=f"{global_penalty:.2f}"))

        for tl_id in traffic_light_ids:
            controlled_lanes = current_batch.get('tls_controlled_lanes', {}).get(tl_id, [])
            waiting_time = sum(current_batch.get('lane_waiting_time', {}).get(lane_id, 0.0) for lane_id in controlled_lanes)
            flow_bonus = 0
            if last_batch:
                for lane_id in controlled_lanes:
                    vehicles_before = set(last_batch.get('lane_vehicle_ids', {}).get(lane_id, []))
                    vehicles_after = set(current_batch.get('lane_vehicle_ids', {}).get(lane_id, []))
                    flow_bonus += len(vehicles_before - vehicles_after)

            total_flow_this_step += flow_bonus

            rewards[tl_id] = (waiting_time * self.reward_weights['waiting_time']) + \
                             (flow_bonus * self.reward_weights['flow']) + \
                             global_penalty
        
        self.last_step_total_flow = total_flow_this_step
        return rewards