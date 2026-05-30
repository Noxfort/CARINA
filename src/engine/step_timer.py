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

# File: src/engine/step_timer.py
# Author: Gabriel Moraes
# Date: April 15, 2026

import time
import logging

class StepTimer:
    """
    Componente dedicado (SRP) para cronometrar latências de operações
    críticas em tempo real (HFT) e exibir métricas uniformemente.
    
    Supports two usage modes:
    - HFT Mode (no args): Used by StepProcessor with start_phase/stop_phase API.
    - Episode Mode (with args): Used by EpisodeRunner with mark_*/log_if_needed API.
    """
    
    def __init__(self, log_step_progress: bool = True, freq: int = 1):
        self.log_step_progress = log_step_progress
        self.freq = freq
        
        # --- HFT Mode Accumulators (used by StepProcessor/AgentEvaluator) ---
        self.t_total_start = 0.0
        self.t_total_end = 0.0
        
        self.t_extraction = 0.0
        self.t_inference = 0.0
        self.t_reward = 0.0
        self.t_auth = 0.0
        self.t_guardian = 0.0
        
        self._current_phase_t0 = 0.0
        
        # --- Episode Mode Markers (used by EpisodeRunner) ---
        self.t_decision_start = 0.0
        self.t_decision_end = 0.0
        self.t_auth_start = 0.0
        self.t_auth_end = 0.0
        self.t_analysis_pre_start = 0.0
        self.t_analysis_pre_end = 0.0
        self.t_guardian_send_start = 0.0
        self.t_guardian_send_end = 0.0
        self.t_guardian_recv_start = 0.0
        self.t_guardian_recv_end = 0.0
        self.t_env_step_start = 0.0
        self.t_env_step_end = 0.0
        self.t_analysis_post_start = 0.0
        self.t_analysis_post_end = 0.0
        self.t_learning_start = 0.0
        self.t_learning_end = 0.0

    # ==========================================
    # HFT Mode API (StepProcessor / AgentEvaluator)
    # ==========================================

    def start_step(self):
        """Inicia o relógio geral do passo HFT."""
        self.t_total_start = time.perf_counter()
        
        self.t_extraction = 0.0
        self.t_inference = 0.0
        self.t_reward = 0.0
        self.t_auth = 0.0
        self.t_guardian = 0.0

    def start_phase(self):
        """Dispara cronômetro para uma fase específica."""
        self._current_phase_t0 = time.perf_counter()
        
    def stop_phase(self, phase_name: str):
        """Acumula o tempo processado sob o medidor nomeado."""
        delta = time.perf_counter() - self._current_phase_t0
        if phase_name == 'extraction':
            self.t_extraction += delta
        elif phase_name == 'inference':
            self.t_inference += delta
        elif phase_name == 'reward':
            self.t_reward += delta
        elif phase_name == 'auth':
            self.t_auth += delta
        elif phase_name == 'guardian':
            self.t_guardian += delta

    def log_and_finish_step(self, guardian_vetoed: bool, log_progress: bool):
        """Consolida os tempos e manda pro terminal caso o sistema requeira logs."""
        self.t_total_end = time.perf_counter()
        total_ms = (self.t_total_end - self.t_total_start) * 1000
        
        if log_progress:
            log_message = (
                f"[STEP_TIMER] Total: {total_ms:.2f}ms | "
                f"State_Extraction: {self.t_extraction * 1000:.2f}ms | "
                f"PPO_Decision: {self.t_inference * 1000:.2f}ms | "
                f"Reward_Compute: {self.t_reward * 1000:.2f}ms | "
                f"Authorization: {self.t_auth * 1000:.2f}ms | "
                f"Guardian_Time: {self.t_guardian * 1000:.2f}ms"
            )
            logging.info(log_message)

    # ==========================================
    # Episode Mode API (EpisodeRunner)
    # ==========================================

    def mark_total_start(self): self.t_total_start = time.perf_counter()
    def mark_analysis_pre_start(self): self.t_analysis_pre_start = time.perf_counter()
    def mark_analysis_pre_end(self): self.t_analysis_pre_end = time.perf_counter()
    def mark_decision_start(self): self.t_decision_start = time.perf_counter()
    def mark_decision_end(self): self.t_decision_end = time.perf_counter()
    def mark_auth_start(self): self.t_auth_start = time.perf_counter()
    def mark_auth_end(self): self.t_auth_end = time.perf_counter()
    def mark_guardian_send_start(self): self.t_guardian_send_start = time.perf_counter()
    def mark_guardian_send_end(self): self.t_guardian_send_end = time.perf_counter()
    def mark_guardian_recv_start(self): self.t_guardian_recv_start = time.perf_counter()
    def mark_guardian_recv_end(self): self.t_guardian_recv_end = time.perf_counter()
    def mark_env_step_start(self): self.t_env_step_start = time.perf_counter()
    def mark_env_step_end(self): self.t_env_step_end = time.perf_counter()
    def mark_analysis_post_start(self): self.t_analysis_post_start = time.perf_counter()
    def mark_analysis_post_end(self): self.t_analysis_post_end = time.perf_counter()
    def mark_learning_start(self): self.t_learning_start = time.perf_counter()
    def mark_learning_end(self): self.t_learning_end = time.perf_counter()

    def log_if_needed(self, step_count: int):
        if not self.log_step_progress:
            return

        if step_count == 1 or step_count % self.freq == 0:
            t_total_end = time.perf_counter()
            
            total_ms = (t_total_end - self.t_total_start) * 1000
            decision_ms = (self.t_decision_end - self.t_decision_start) * 1000
            auth_ms = (self.t_auth_end - self.t_auth_start) * 1000
            analysis_pre_ms = (self.t_analysis_pre_end - self.t_analysis_pre_start) * 1000
            guardian_send_ms = (self.t_guardian_send_end - self.t_guardian_send_start) * 1000
            guardian_recv_ms = (self.t_guardian_recv_end - self.t_guardian_recv_start) * 1000
            env_step_ms = (self.t_env_step_end - self.t_env_step_start) * 1000
            analysis_post_ms = (self.t_analysis_post_end - self.t_analysis_post_start) * 1000
            learning_ms = (self.t_learning_end - self.t_learning_start) * 1000
            
            log_message = (
                f"[STEP_TIMER] Total: {total_ms:.2f}ms | "
                f"PPO_Decision: {(decision_ms + auth_ms):.2f}ms | "
                f"Analysis_PreStep: {analysis_pre_ms:.2f}ms | "
                f"Guardian_SendState: {guardian_send_ms:.2f}ms | "
                f"Guardian_RecvSignal: {guardian_recv_ms:.2f}ms | "
                f"Environment_Step: {env_step_ms:.2f}ms | "
                f"Analysis_PostStep: {analysis_post_ms:.2f}ms | "
                f"PPO_Learning: {learning_ms:.2f}ms"
            )
            logging.info(log_message)
