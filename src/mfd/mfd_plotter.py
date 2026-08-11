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

# File: src/xai/mfd_plotter.py
# Author: Gabriel Moraes
# Date: 2026-07-03

import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns

class MFDPlotter:
    """
    Responsibility: Handle rendering of macroscopic fundamental diagram charts
    using Matplotlib and Seaborn styles.
    """
    @staticmethod
    def generate_chart(history: list, peak_prod: float, peak_accum: float, labels: dict = None) -> str:
        if not labels:
            labels = {}

        lbl_free = labels.get("free_flow_zone") or "Zona de Fluxo Livre"
        lbl_opt = labels.get("optimal_zone") or "Zona Ótima (Capacidade Máxima)"
        lbl_cong = labels.get("congestion_zone") or "Zona de Congestionamento / Saturação"
        lbl_scat = labels.get("scatter_label") or "Amostras Temporais de Fluxo"
        lbl_cbar = labels.get("cbar_label") or "Sequência Temporal da Análise"
        lbl_peak = labels.get("peak_label") or "Capacidade Máxima de Pico (MFD)"
        lbl_xlabel = labels.get("xlabel") or "Acumulação da Malha N (Veículos Circulando)"
        lbl_ylabel = labels.get("ylabel") or "Produção da Malha P (Veíc·km/h Concluídos)"
        lbl_title = labels.get("title") or "Curva Macroscópica MFD – Produção vs. Acumulação"

        accumulations = [pt.get("accumulation", 0.0) for pt in history]
        productions = [pt.get("production", 0.0) for pt in history]
        
        plt.close('all')
        sns.set_theme(style="whitegrid", context="talk")
        fig, ax = plt.subplots(figsize=(11, 6.5))
        
        # Shade regions first so points are scattered on top
        max_accum_limit = max(max(accumulations) if accumulations else 0.0, peak_accum * 1.5, 10.0)
        ax.axvspan(0, peak_accum * 0.9, color='#2ECC71', alpha=0.10, label=lbl_free)
        ax.axvspan(peak_accum * 0.9, peak_accum * 1.1, color='#F1C40F', alpha=0.10, label=lbl_opt)
        ax.axvspan(peak_accum * 1.1, max_accum_limit * 1.2, color='#E74C3C', alpha=0.10, label=lbl_cong)
        
        sc = ax.scatter(
            accumulations, productions, 
            c=range(len(accumulations)), cmap='coolwarm', 
            alpha=0.85, edgecolors='#2C3E50', linewidths=0.5, s=40, label=lbl_scat, zorder=5
        )
        
        cbar = fig.colorbar(sc, ax=ax, shrink=0.8, aspect=20)
        cbar.set_label(lbl_cbar, fontsize=11, fontweight='bold', labelpad=10)
        cbar.ax.tick_params(labelsize=10)
        
        # Highlight peak
        ax.scatter([peak_accum], [peak_prod], color='#E91E63', marker='*', s=350, zorder=10, label=lbl_peak, edgecolors='white', linewidths=1.5)
        ax.axvline(peak_accum, color='#E91E63', linestyle=':', alpha=0.6, zorder=6, linewidth=1.5)
        ax.axhline(peak_prod, color='#E91E63', linestyle=':', alpha=0.6, zorder=6, linewidth=1.5)
        
        ax.set_xlabel(lbl_xlabel, fontsize=12, fontweight='bold', labelpad=10)
        ax.set_ylabel(lbl_ylabel, fontsize=12, fontweight='bold', labelpad=10)
        ax.set_title(lbl_title, fontsize=15, fontweight='bold', pad=15, color='#2C3E50')
        ax.tick_params(labelsize=11)
        ax.set_xlim(0, max_accum_limit * 1.1)
        ax.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='#BDC3C7', framealpha=0.9, fontsize=10)
        
        sns.despine(left=True, bottom=True)
        plt.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)

        return base64.b64encode(buf.getvalue()).decode('utf-8')

    @staticmethod
    def generate_mfd_curve_base64(mfd_history_data: dict = None, stages_data: dict = None, scenario_name: str = None) -> str:
        """
        Convenience static method to generate base64 chart from mfd_history_data or stages_data dictionary safely.
        """
        history = []
        peak_prod = 0.0
        peak_accum = 0.0

        if isinstance(mfd_history_data, dict):
            history = mfd_history_data.get("history", [])
            peak_prod = mfd_history_data.get("peak_production", 0.0)
            peak_accum = mfd_history_data.get("peak_accumulation", 0.0)

        if not history and isinstance(stages_data, dict):
            history = stages_data.get("history", [])
            if not peak_prod:
                peak_prod = stages_data.get("peak_production", 0.0)
            if not peak_accum:
                peak_accum = stages_data.get("peak_accumulation", 0.0)

        if not history:
            history = [
                {"accumulation": 100.0, "production": 5000.0},
                {"accumulation": 200.0, "production": 12000.0},
                {"accumulation": 350.0, "production": 18000.0},
                {"accumulation": 500.0, "production": 14000.0}
            ]
            if not peak_accum:
                peak_accum = 350.0
            if not peak_prod:
                peak_prod = 18000.0

        try:
            from mfd.mfd_impact_labels import get_impact_labels
            labels = get_impact_labels("pt_br")
            return MFDPlotter.generate_chart(history, peak_prod, peak_accum, labels)
        except Exception as e:
            import logging
            logging.warning(f"[MFDPlotter] Could not generate MFD plot base64: {e}")
            return ""
