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

# File: src/sas/heatmap_calibrator.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import logging
import os
import json
from typing import List, Dict

SKLEARN_AVAILABLE = False
try:
    import pandas as pd
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
    logging.debug("[HEATMAP_CALIBRATOR] Pandas e Scikit-learn detectados para calibração.")
except Exception as _e:
    logging.warning(f"[HEATMAP_CALIBRATOR] Bibliotecas 'pandas' ou 'sklearn' não encontradas para calibração. Erro: {_e}")

class HeatmapCalibrator:
    """Manages the calibration of heatmap weights based on operational telemetry samples."""

    @staticmethod
    def is_available() -> bool:
        return SKLEARN_AVAILABLE

    def calibrate(self, data_points: List[Dict]) -> Dict | None:
        if not SKLEARN_AVAILABLE:
            logging.error("[HEATMAP_CALIBRATOR] Pandas/sklearn indisponíveis. Calibração abortada.")
            return None

        logging.info(f"[HEATMAP_CALIBRATOR] Iniciando calibração com {len(data_points)} pontos de dados.")
        if len(data_points) < 100:
            logging.warning(f"[HEATMAP_CALIBRATOR] Dados insuficientes para calibração (necessário 100+, temos {len(data_points)}). Abortando.")
            return None

        try:
            df = pd.DataFrame(data_points)
            df.replace([float('inf'), -float('inf')], float('nan'), inplace=True)
            df.dropna(inplace=True)

            if df.empty or len(df) < 2:
                logging.warning("[HEATMAP_CALIBRATOR] Nenhum dado válido restante após a limpeza. Abortando.")
                return None

            features = ['occupancy', 'waiting_time', 'flow']
            target = 'bad_events'

            if not all(feat in df.columns for feat in features) or target not in df.columns:
                 logging.error(f"[HEATMAP_CALIBRATOR] Colunas necessárias ({features + [target]}) não encontradas. Colunas: {df.columns.tolist()}.")
                 return None

            X = df[features]
            y = df[target]

            if X.isnull().values.any() or y.isnull().values.any():
                 logging.warning("[HEATMAP_CALIBRATOR] Dados nulos (NaN) ainda presentes. Abortando.")
                 return None

            if not pd.api.types.is_numeric_dtype(y):
                 logging.warning(f"[HEATMAP_CALIBRATOR] Coluna target '{target}' não é numérica. Abortando.")
                 return None

            if not all(pd.api.types.is_numeric_dtype(X[col]) for col in X.columns):
                 logging.warning("[HEATMAP_CALIBRATOR] Uma ou mais colunas de features não são numéricas. Abortando.")
                 return None

            model = LinearRegression(positive=False)
            model.fit(X, y)

            coef_occupancy = max(0.0, model.coef_[0])
            coef_waiting = max(0.0, model.coef_[1])
            coef_flow = model.coef_[2]

            total_abs_weight = abs(coef_occupancy) + abs(coef_waiting) + abs(coef_flow)
            if total_abs_weight > 1e-6:
                 norm_factor = 3.0 / total_abs_weight
                 coef_occupancy *= norm_factor
                 coef_waiting *= norm_factor
                 coef_flow *= norm_factor

            new_weights = {
                'weight_occupancy': round(coef_occupancy, 4),
                'weight_waiting_time': round(coef_waiting, 4),
                'weight_flow': round(-abs(coef_flow), 4)
            }

            logging.info(f"[HEATMAP_CALIBRATOR] Calibração concluída. Novos pesos: {new_weights}")
            return new_weights

        except Exception as e:
            logging.error(f"[HEATMAP_CALIBRATOR] Erro durante a calibração do mapa de calor: {e}", exc_info=True)
            return None

    def save_live_weights(self, scenario_dir: str, weights: Dict):
        if not scenario_dir or not os.path.exists(scenario_dir):
            logging.error("[HEATMAP_CALIBRATOR] Diretório do cenário inválido. Não é possível salvar pesos.")
            return

        live_weights_path = os.path.join(scenario_dir, "heatmap_weights_live.json")
        try:
            with open(live_weights_path, "w", encoding="utf-8") as f:
                json.dump(weights, f, indent=4)
            logging.info(f"[HEATMAP_CALIBRATOR] Pesos do mapa de calor salvos em: {live_weights_path}")
        except IOError as e:
            logging.error(f"[HEATMAP_CALIBRATOR] Falha ao salvar os pesos do mapa de calor: {e}")
