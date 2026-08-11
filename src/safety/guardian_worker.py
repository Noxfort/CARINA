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

# File: src/safety/guardian_worker.py (FIXED)
# Author: Gabriel Moraes
# Date: October 5, 2025

"""
Defines the logic for the Asynchronous Guardian process.

This version contains the worker's main operation loop, which consumes
simulation states from a queue, executes GuardianAgent inference,
and sends veto signals back to the main process.
"""
import logging
import time
import os
import sys
from multiprocessing import Queue
from queue import Empty
import configparser

def run_guardian_worker(
    settings: configparser.ConfigParser,
    state_queue: Queue,
    signal_queue: Queue,
    scenario_checkpoint_dir: str,
    agent_ids: list,
    pae_state_dict: dict = None,
    pae_config: dict = None
):
    """
    The entry point and main loop for the Asynchronous Guardian process.
    """
    # Add 'src' directory to path to allow relative imports
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from utils.logging_setup import setup_logging
    from agents.guardian_agent import GuardianAgent
    # --- FIX 1: Import the LocaleManagerBackend ---
    from utils.locale_manager_backend import LocaleManagerBackend
    # --- PAE Universal (inference-only copy for subprocess) ---
    from models.pae import PredictiveAutoencoder
    from engine.dqn_optimizer import DQNOptimizer
    import torch
    
    # --- TensorCore (TF32) Hardware Acceleration Optimization (Process Independent) ---
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    try:
        torch.set_float32_matmul_precision('high')
    except AttributeError:
        pass # PyTorch versions < 1.12 might not have this, though CARINA requires >= 2.0
    # ------------------------------------------------------------

    # Configure a specific logger for this process
    from src.utils.paths import get_base_output_dir
    log_dir = os.path.join(get_base_output_dir(), "logs", "guardian_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir)

    # --- FIX 2: Create the LocaleManagerBackend instance ---
    lm = LocaleManagerBackend()

    logging.info(lm.get_string("guardian_worker.process_started", default="[GUARDIAN_WORKER] Asynchronous Guardian Process started."))

    # --- Reconstruct PAE in inference-only mode (process isolation) ---
    shared_pae_worker = None
    if pae_state_dict and pae_config:
        try:
            shared_pae_worker = PredictiveAutoencoder(**pae_config)
            shared_pae_worker.load_state_dict(pae_state_dict)
            shared_pae_worker.eval()  # Inference-only — no training in subprocess
            logging.info(lm.get_string("guardian_worker.pae_reconstructed", default="[GUARDIAN_WORKER] Universal PAE reconstructed (inference-only)"))
        except Exception as e:
            logging.error(lm.get_string("guardian_worker.pae_failed", default="[GUARDIAN_WORKER] Failed to reconstruct PAE: {error}", error=e), exc_info=True)
            shared_pae_worker = None

    # --- Initialization ---
    guardians = {}
    guardian_config = settings['GUARDIAN_AGENT']
    traffic_rules_config = settings['TRAFFIC_RULES'] if 'TRAFFIC_RULES' in settings else guardian_config
    for tl_id in agent_ids:
        guardians[tl_id] = GuardianAgent(
            aiconfig=guardian_config,
            traffic_rules_config=traffic_rules_config,
            locale_manager=lm,
            shared_pae=shared_pae_worker
        )
    
    # Global Strategy Optimizer for the Worker
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dqn_optimizer = DQNOptimizer(hyperparams=guardian_config, device=device)

    logging.info(lm.get_string("guardian_worker.guardians_ready", default="[GUARDIAN_WORKER] {count} guardians created and ready.", count=len(guardians)))
    
    # --- Main Loop ---
    while True:
        try:
            latest_state_package = None
            
            # 1. Empties the queue to only get the most recent state
            try:
                while True:
                    latest_state_package = state_queue.get_nowait()
            except Empty:
                pass # Queue is empty, normal.

            # 2. If a status has been received, process it
            if latest_state_package:
                # The package contains the status and rewards
                global_state, rewards, done, mode = latest_state_package
                
                # THINKING MODE: Generate the Preemptive Veto Map
                veto_map = {}
                for tl_id, guardian in guardians.items():
                    local_state = global_state.get(tl_id)
                    if not local_state:
                        continue
                    
                    # Background Neural Inference: Predict Spillback Risk
                    risk_score = guardian.evaluate_spillback_risk(local_state, tl_id)
                    veto_map[tl_id] = risk_score

                    # Guardian Learning (if in training mode)
                    if mode == 'training' and rewards:
                        # Reconstructed Strategy Invocation (SOLID)
                        # Assumes the transition gets pushed to memory somewhere else previously in the pipeline
                        if len(guardian.memory) >= getattr(guardian, 'batch_size', 128):
                            loss = dqn_optimizer.step(
                                policy_net=guardian.policy_net,
                                target_net=guardian.target_net,
                                optimizer=guardian.optimizer,
                                memory=guardian.memory,
                                forward_policy=guardian.forward_policy,
                                forward_target=guardian.forward_target
                            )
                            
                            # Soft Target Update heuristic
                            if getattr(guardian, 'steps_done', 0) % 1000 == 0:
                                dqn_optimizer.update_target_net(guardian.policy_net, guardian.target_net)

                # Broadcast Veto Map to Main Process (Zero-Latency check at inference time)
                if veto_map:
                    try:
                        signal_queue.put_nowait({'type': 'veto_map', 'map': veto_map})
                    except Full:
                        pass # If queue is full, drop the map, it will be updated in the next cycle

            # Pause to not consume 100% CPU if there is no work
            time.sleep(0.01) # Reduced sleep for faster thinking mode

        except (KeyboardInterrupt, SystemExit):
            logging.info(lm.get_string("guardian_worker.shutdown", default="[GUARDIAN_WORKER] Shutdown signal received."))
            break
        except Exception as e:
            logging.error(lm.get_string("guardian_worker.fatal_error", default="[GUARDIAN_WORKER] Fatal error in loop: {error}", error=e), exc_info=True)
            time.sleep(1)
    
    logging.info(lm.get_string("guardian_worker.process_finished", default="[GUARDIAN_WORKER] Process finished."))