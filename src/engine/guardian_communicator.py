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

# File: src/engine/guardian_communicator.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import logging
from multiprocessing import Queue
from queue import Empty, Full
from typing import Union

class GuardianCommunicator:
    """
    Abstrai o envio de pacotes de estado e leitura de sinais de veto
    do Guardião (Safety Checks da UI).
    """

    def __init__(self, guardian_state_queue: Union[Queue, None], guardian_signal_queue: Union[Queue, None]):
        self.state_queue = guardian_state_queue
        self.signal_queue = guardian_signal_queue

    def send_state(self, current_states_dict: dict, done: bool, mode: str = 'training'):
        if self.state_queue:
            try:
                state_package = (current_states_dict, {}, done, mode)
                self.state_queue.put_nowait(state_package)
            except Full:
                logging.warning("[EpisodeRunner] Fila do Guardião (estado) cheia.")
            except Exception as e:
                logging.error(f"[EpisodeRunner] Erro ao enviar estado para fila do Guardião: {e}")

    def receive_vetos(self) -> dict:
        latest_veto_map = {}
        if self.signal_queue:
            try:
                while True:
                    signal = self.signal_queue.get_nowait()
                    if 'type' in signal and signal['type'] == 'veto_map':
                        latest_veto_map = signal['map']
            except Empty:
                pass
            except Exception as e:
                logging.error(f"[EpisodeRunner] Erro ao receber sinal da fila do Guardião: {e}")
        return latest_veto_map
