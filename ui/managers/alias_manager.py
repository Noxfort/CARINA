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

# File: ui/handlers/alias_manager.py
# Author: Gabriel Moraes
# Date: 2026-06-10

import json
import os
import logging
from src.utils.paths import resource_path

class AliasManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AliasManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.filepath = resource_path(os.path.join("config", "aliases.json"))
        self.aliases = {}
        self.load()
        self._initialized = True

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.aliases = json.load(f)
            except Exception as e:
                logging.error(f"[AliasManager] Erro ao carregar aliases: {e}")
                self.aliases = {}

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.aliases, f, indent=4)
        except Exception as e:
            logging.error(f"[AliasManager] Erro ao salvar aliases: {e}")

    def get_alias(self, original_id: str) -> str:
        return self.aliases.get(original_id, original_id)

    def set_alias(self, original_id: str, alias: str):
        if alias and alias.strip():
            self.aliases[original_id] = alias.strip()
        else:
            if original_id in self.aliases:
                del self.aliases[original_id]
        self.save()
