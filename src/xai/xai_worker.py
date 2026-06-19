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

# File: src/xai/xai_worker.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import logging
import os
import json
import time
import sys
import re
import subprocess
import configparser
import torch

from typing import Dict, Any

from xai.request_scanner import RequestScanner
from xai.agent_reconstructor import AgentReconstructor
from xai.report_pipeline import ReportPipeline

class XAIOrchestrator:
    """
    Responsibility: Coordinate the Explanable AI pipeline by delegating 
    tasks to the Scanner (File I/O), Reconstructor (Memory), and Pipeline (Math/NLP).
    """
    def __init__(self, scenario_results_dir: str):
        self.scenario_results_dir = scenario_results_dir
        
        captum_base_dir = os.path.join(scenario_results_dir, "captum")
        requests_dir = os.path.join(captum_base_dir, "requests")
        responses_dir = os.path.join(captum_base_dir, "responses")
        reports_dir = os.path.join(captum_base_dir, "reports")
        checkpoints_dir = os.path.join(scenario_results_dir, "checkpoints")
        
        os.makedirs(reports_dir, exist_ok=True)
        
        # Inject Dependencies
        self.scanner = RequestScanner(requests_dir, responses_dir)
        self.reconstructor = AgentReconstructor(checkpoints_dir)
        self.pipeline = ReportPipeline(scenario_results_dir, reports_dir)

        # MFD Optimization Analysis IPC scanner
        mfd_base_dir = os.path.join(scenario_results_dir, "mfd_analysis")
        mfd_requests_dir = os.path.join(mfd_base_dir, "requests")
        mfd_responses_dir = os.path.join(mfd_base_dir, "responses")
        self.mfd_scanner = RequestScanner(mfd_requests_dir, mfd_responses_dir)

    def process_job(self, agent_id: str):
        """Executes a single end-to-end Explainability job."""
        logging.info(f"[XAI_ORCHESTRATOR] Processing request for Agent: {agent_id}")
        
        response_data = {"status": "error", "message": "Unknown error"}
        
        try:
            # 1. Reconstruct Blind Agent
            agent = self.reconstructor.reconstruct_agent(agent_id)
            
            # 2. Run Math & Transducer
            response_data = self.pipeline.generate_full_report(agent, agent_id)
            
        except Exception as e:
            logging.error(f"[XAI_ORCHESTRATOR] Pipeline error for {agent_id}: {e}", exc_info=True)
            response_data = {"status": "error", "message": str(e)}
        finally:
            # 3. Clean up and respond
            self.scanner.write_response(agent_id, response_data)
            self.scanner.clear_request(agent_id)
            logging.info(f"[XAI_ORCHESTRATOR] Job finished for {agent_id}.")

    def process_mfd_job(self, req_id: str):
        """Executes a single end-to-end MFD Optimization Analysis job."""
        logging.info(f"[XAI_ORCHESTRATOR] Processing MFD Optimization request: {req_id}")
        
        response_data = {"status": "error", "message": "Unknown error"}
        
        try:
            mfd_history_path = os.path.join(self.scenario_results_dir, "mfd_history.json")
            if not os.path.exists(mfd_history_path):
                raise FileNotFoundError("MFD simulation history not found. Ensure the simulation is running and has generated steps.")
            
            with open(mfd_history_path, "r", encoding="utf-8") as f:
                mfd_history_data = json.load(f)
                
            response_data = self.generate_mfd_report(mfd_history_data)
            
        except Exception as e:
            logging.error(f"[XAI_ORCHESTRATOR] MFD pipeline error for {req_id}: {e}", exc_info=True)
            response_data = {"status": "error", "message": str(e)}
        finally:
            self.mfd_scanner.write_response(req_id, response_data)
            self.mfd_scanner.clear_request(req_id)
            logging.info(f"[XAI_ORCHESTRATOR] MFD job finished: {req_id}.")

    def generate_mfd_report(self, mfd_history_data: dict) -> dict:
        import io
        import base64
        import matplotlib.pyplot as plt
        from utils.locale_manager_backend import LocaleManagerBackend
        
        locale_manager = LocaleManagerBackend()
        lang = locale_manager.get_language()
        
        # Localized graph text configuration from JSON
        title = locale_manager.get_string("xai.mfd_chart_title", default="Macroscopic Fundamental Diagram (MFD) - Optimization Curve")
        xlabel = locale_manager.get_string("xai.mfd_xlabel", default="Accumulation (veh)")
        ylabel = locale_manager.get_string("xai.mfd_ylabel", default="Production (veh·m/s)")
        cbar_label = locale_manager.get_string("xai.mfd_cbar_label", default="Simulation Steps")
        scatter_label = locale_manager.get_string("xai.mfd_scatter_label", default="Simulation State")
        peak_label = locale_manager.get_string("xai.mfd_peak_label", default="Optimal Capacity (MFD Peak)")
        
        history = mfd_history_data.get("history", [])
        peak_prod = mfd_history_data.get("peak_production", 0.0)
        peak_accum = mfd_history_data.get("peak_accumulation", 0.0)
        
        if not history:
            return {"status": "error", "message": "No MFD history data recorded yet. Wait for simulation steps."}
            
        accumulations = [pt.get("accumulation", 0.0) for pt in history]
        productions = [pt.get("production", 0.0) for pt in history]
        
        plt.close('all')
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sc = ax.scatter(
            accumulations, productions, 
            c=range(len(accumulations)), cmap='plasma', 
            alpha=0.7, edgecolors='none', s=25, label=scatter_label
        )
        
        cbar = plt.colorbar(sc, ax=ax)
        cbar.set_label(cbar_label)
        
        # Highlight peak
        ax.scatter([peak_accum], [peak_prod], color='#FF2E93', marker='*', s=250, zorder=10, label=peak_label)
        ax.axvline(peak_accum, color='#FF2E93', linestyle='--', alpha=0.5)
        ax.axhline(peak_prod, color='#FF2E93', linestyle='--', alpha=0.5)
        
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # Compute summary stats
        total_steps = len(history)
        sum_prod = sum(s.get("production", 0.0) for s in history)
        sum_accum = sum(s.get("accumulation", 0.0) for s in history)
        sum_speed = sum(s.get("mean_speed", 0.0) for s in history)
        sum_eff = sum(s.get("efficiency", 0.0) for s in history)
        
        avg_prod = sum_prod / total_steps
        avg_accum = sum_accum / total_steps
        avg_speed = sum_speed / total_steps
        avg_eff = sum_eff / total_steps
        
        max_eff = max(s.get("efficiency", 0.0) for s in history)
        min_eff = min(s.get("efficiency", 0.0) for s in history)
        
        from mfd.classifier import MFDClassifier
        state_counts = {}
        for s in history:
            c_ratio = s.get("congestion_ratio", 0.0)
            state, _ = MFDClassifier.classify(c_ratio, is_warmed_up=True)
            state_counts[state] = state_counts.get(state, 0) + 1
            
        state_pct = {state: round((count / total_steps) * 100, 2) for state, count in state_counts.items()}
        
        summary_stats = {
            "total_steps": total_steps,
            "peak_production_veh_m_s": round(peak_prod, 4),
            "critical_accumulation_veh": round(peak_accum, 4),
            "average_production_veh_m_s": round(avg_prod, 4),
            "average_accumulation_veh": round(avg_accum, 4),
            "average_speed_m_s": round(avg_speed, 2),
            "average_efficiency": round(avg_eff, 4),
            "max_efficiency": round(max_eff, 4),
            "min_efficiency": round(min_eff, 4),
            "network_state_percentages": state_pct
        }
        
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        transducer_script = os.path.join(project_root, 'src', 'xai', 'semantic_transducer.py')
        
        transducer_input = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "MFD_OPTIMIZATION",
            "attributions": summary_stats,
            "language": lang
        }
        
        final_report_text = ""
        try:
            logging.info(f"[XAI_ORCHESTRATOR] Invoking Semantic Transducer LLM for MFD report...")
            cmd = [sys.executable, transducer_script]
            proc = subprocess.run(
                cmd,
                input=json.dumps(transducer_input),
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if proc.returncode == 0:
                final_report_text = proc.stdout.strip()
            else:
                logging.warning(f"[XAI_ORCHESTRATOR] Transducer failed. STDERR: {proc.stderr}")
        except Exception as e:
            logging.error(f"[XAI_ORCHESTRATOR] LLM Pipeline crashed: {e}")
            
        if not final_report_text:
            fallback_fmt = locale_manager.get_string(
                "xai.mfd_fallback_report",
                default="MFD Performance Report:\n- Total Steps: {total_steps}\n- Avg Efficiency: {avg_eff:.2%}\n- Max Efficiency: {max_eff:.2%}\n- Peak Prod: {peak_prod:.2f}\n- State breakdown: {state_pct}"
            )
            final_report_text = fallback_fmt.format(
                total_steps=total_steps,
                avg_eff=avg_eff,
                max_eff=max_eff,
                peak_prod=peak_prod,
                state_pct=state_pct
            )
            
        return {
            "status": "complete",
            "image_base64": img_base64,
            "text_report": final_report_text
        }

    def run_forever(self):
        """Blocking event loop."""
        logging.info(f"[XAI_ORCHESTRATOR] Service started. Watching XAI: {self.scanner.requests_dir} and MFD: {self.mfd_scanner.requests_dir}")
        while True:
            try:
                # Poll XAI requests
                pending_jobs = self.scanner.get_pending_requests()
                for agent_id in pending_jobs:
                    self.process_job(agent_id)
                    
                # Poll MFD requests
                pending_mfd_jobs = self.mfd_scanner.get_pending_requests()
                for req_id in pending_mfd_jobs:
                    self.process_mfd_job(req_id)
                    
                if not pending_jobs and not pending_mfd_jobs:
                    time.sleep(2)
                    continue
                    
                time.sleep(1)
                
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                logging.error(f"[XAI_ORCHESTRATOR] Critical Loop Error: {e}", exc_info=True)
                time.sleep(5)
                
        logging.info("[XAI_ORCHESTRATOR] Shutdown.")


def run_xai_worker(settings: configparser.ConfigParser, scenario_results_dir: str):
    """Entry point for multiprocessing."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from utils.logging_setup import setup_logging
    
    from src.utils.paths import get_base_output_dir
    log_dir = os.path.join(get_base_output_dir(), "logs", "xai_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    orchestrator = XAIOrchestrator(scenario_results_dir)
    orchestrator.run_forever()