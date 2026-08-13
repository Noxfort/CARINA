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

# File: src/database/step_decision_worker.py
# Author: Gabriel Moraes
# Date: August 2026

import time
import queue
import logging
import threading
from typing import TYPE_CHECKING, List, Tuple, Dict, Any, Optional

if TYPE_CHECKING:
    from src.repositories.step_decision_repo import StepDecisionRepository

class StepDecisionWorker:
    """
    Non-blocking async background worker for real-time step decisions.
    Pushes telemetry into an in-memory Queue in < 0.001 ms without locking
    the real-time simulation step. Flushes compressed batches to PostgreSQL.
    """
    def __init__(self, repository: 'StepDecisionRepository', flush_interval_sec: float = 3.0, batch_threshold: int = 50):
        self.repository = repository
        self.flush_interval_sec = flush_interval_sec
        self.batch_threshold = batch_threshold
        
        self.decision_queue: queue.Queue = queue.Queue(maxsize=10000)
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Delta Compression State Cache (agent_id -> last_state_tuple)
        self._last_agent_states: Dict[str, Tuple] = {}
        self._last_agent_counts: Dict[str, int] = {}

    def start(self):
        """Starts the background flushing thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="StepDecisionWorkerThread")
            self._thread.start()
            logging.info("[StepDecisionWorker] Async background telemetry worker started.")

    def stop(self):
        """Stops the worker thread and flushes remaining queue items."""
        if self._running:
            self._running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._flush_queue_batch()
            logging.info("[StepDecisionWorker] Async background worker stopped and flushed.")

    def push_decision(self, sim_time: float, step_num: int, agent_id: str, 
                      maturity: str, suggested_action: str, final_decision: str, 
                      veto_reason: str, total_time_ms: float = 0.0, guardian_time_ms: float = 0.0):
        """
        Non-blocking telemetry push (< 0.001 ms).
        Applies Delta Compression (aggregates consecutive identical steps per agent).
        """
        state_key = (maturity, suggested_action, final_decision, veto_reason)
        
        if agent_id in self._last_agent_states:
            last_key = self._last_agent_states[agent_id]
            if last_key == state_key:
                # Increment delta count for consecutive identical state
                self._last_agent_counts[agent_id] = self._last_agent_counts.get(agent_id, 1) + 1
                return

        # Flush previous aggregated state for this agent if state changed
        if agent_id in self._last_agent_states:
            prev_key = self._last_agent_states[agent_id]
            prev_count = self._last_agent_counts.get(agent_id, 1)
            rec_tuple = self.repository.encode_decision(
                sim_time, step_num, agent_id,
                prev_key[0], prev_key[1], prev_key[2], prev_key[3],
                step_count=prev_count, total_time_ms=total_time_ms, guardian_time_ms=guardian_time_ms
            )
            try:
                self.decision_queue.put_nowait(rec_tuple)
            except queue.Full:
                pass

        # Update cache to new state
        self._last_agent_states[agent_id] = state_key
        self._last_agent_counts[agent_id] = 1

    def _flush_queue_batch(self):
        """Flushes buffered queue items to PostgreSQL via execute_values."""
        # First flush any pending delta cached states
        pending_tuples = []
        for agent_id, state_key in list(self._last_agent_states.items()):
            count = self._last_agent_counts.get(agent_id, 1)
            rec_tuple = self.repository.encode_decision(
                0.0, 0, agent_id,
                state_key[0], state_key[1], state_key[2], state_key[3],
                step_count=count
            )
            pending_tuples.append(rec_tuple)
        self._last_agent_states.clear()
        self._last_agent_counts.clear()

        # Drain items from queue
        batch = list(pending_tuples)
        while not self.decision_queue.empty():
            try:
                batch.append(self.decision_queue.get_nowait())
            except queue.Empty:
                break

        if batch:
            self.repository.insert_batch(batch)

    def _worker_loop(self):
        """Background thread loop."""
        last_flush = time.time()
        while self._running:
            try:
                time.sleep(0.5)
                now = time.time()
                if (now - last_flush) >= self.flush_interval_sec or self.decision_queue.qsize() >= self.batch_threshold:
                    self._flush_queue_batch()
                    last_flush = now
            except Exception as e:
                logging.error(f"[StepDecisionWorker] Error in worker loop: {e}")
