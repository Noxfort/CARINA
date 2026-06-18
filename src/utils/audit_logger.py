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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/utils/audit_logger.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import os
import json
import logging
from datetime import datetime
from utils.paths import get_base_output_dir

class AuditLogger:
    """
    Registra ações de auditoria (quem, quando, o que) em um arquivo persistente.
    """
    def __init__(self):
        self.audit_file = os.path.join(get_base_output_dir(), "results", "audit_log.json")
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.audit_file), exist_ok=True)
        if not os.path.exists(self.audit_file):
            self._save_data([])

    def _load_data(self):
        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"[AuditLogger] Erro ao ler auditoria: {e}")
            return []

    def _save_data(self, data):
        try:
            with open(self.audit_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"[AuditLogger] Erro ao salvar auditoria: {e}")

    def log_action(self, username: str, action: str, details: str = ""):
        """
        Registra uma ação no log de auditoria.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "username": username,
            "action": action,
            "details": details
        }
        data = self._load_data()
        data.append(entry)
        
        # Mantém apenas os últimos 1000 registros para não pesar
        if len(data) > 1000:
            data = data[-1000:]
            
        self._save_data(data)
        logging.info(f"[AUDIT] Usuário '{username}' realizou '{action}'. Detalhes: {details}")

    def get_logs(self, limit: int = 100):
        data = self._load_data()
        # Retorna do mais recente para o mais antigo
        return list(reversed(data))[-limit:]
