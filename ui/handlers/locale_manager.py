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

# File: ui/handlers/locale_manager.py
# Author: Gabriel Moraes
# Date: December 16, 2025

"""
Define o LocaleManager, o "cérebro" do sistema de tradução da UI.
Nesta versão, o método get_string foi atualizado para aceitar o argumento
'default' (anteriormente 'fallback') para compatibilidade com as Views.
"""

import os
import json
import logging
from typing import Dict, Any, List

from ui.handlers.settings_handler import SettingsHandler

class LocaleManager:
    """
    Gerencia o carregamento e o acesso às strings de tradução da UI.
    """
    def __init__(self):
        """
        Inicializa o gerenciador de tradução, lendo a configuração
        de idioma salva.
        """
        self.locales_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "locales"))
        self.fallback_lang_code = "en_us"
        
        self.current_lang_data: Dict[str, Any] = {}
        self.fallback_lang_data: Dict[str, Any] = {}

        settings_handler = SettingsHandler()
        current_settings = settings_handler.get_current_settings()
        initial_lang_code = current_settings.get('language', 'pt_br')
        
        logging.info(f"[LocaleManager] Idioma inicial definido como '{initial_lang_code}' a partir das configurações.")
        self.load_language(initial_lang_code)

    def _load_file(self, lang_code: str) -> Dict[str, Any]:
        """
        Lê e processa um único arquivo JSON de tradução.
        """
        file_path = os.path.join(self.locales_dir, f"{lang_code}.json")
        if not os.path.exists(file_path):
            logging.error(f"[LocaleManager] Arquivo de tradução não encontrado: {file_path}")
            return {}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"[LocaleManager] Falha ao carregar ou processar o arquivo '{file_path}': {e}")
            return {}

    def load_language(self, lang_code: str):
        """
        Carrega um novo idioma como o principal e garante que o idioma de fallback (inglês)
        esteja sempre carregado como reserva.
        """
        logging.info(f"[LocaleManager] Carregando idioma: '{lang_code}'...")
        
        self.fallback_lang_data = self._load_file(self.fallback_lang_code)
        if not self.fallback_lang_data:
            logging.critical("[LocaleManager] FALHA CRÍTICA: Não foi possível carregar o idioma de fallback (en_us).")

        if lang_code == self.fallback_lang_code:
            self.current_lang_data = self.fallback_lang_data
        else:
            self.current_lang_data = self._load_file(lang_code)
        
        logging.info(f"'{lang_code}' carregado com sucesso.")

    def _get_nested_value(self, data: Dict, keys: List[str]) -> str | None:
        """
        Navega em um dicionário aninhado usando uma lista de chaves.
        """
        temp_dict = data
        for key in keys:
            if isinstance(temp_dict, dict) and key in temp_dict:
                temp_dict = temp_dict[key]
            else:
                return None
        return str(temp_dict) if isinstance(temp_dict, (str, int, float, bool)) else None

    def get_string(self, key: str, default: str = None) -> str:
        """
        Obtém uma string de tradução usando uma chave aninhada (ex: "main_ui.app_title").
        Implementa a lógica de fallback para o inglês e para um valor padrão (default).
        """
        keys = key.split('.')
        
        # 1. Try the translation in the current language
        translation = self._get_nested_value(self.current_lang_data, keys)
        if translation is not None:
            return translation
            
        # 2. If it fails, try the translation in the fallback language (English)
        # logging.warning(f"[LocaleManager] Key '{key}' not found in current language. Trying to fallback to English...")
        fallback_translation = self._get_nested_value(self.fallback_lang_data, keys)
        if fallback_translation is not None:
            return fallback_translation
            
        # 3. If it fails again, use the default value provided in the call
        if default is not None:
            # logging.warning(f"[LocaleManager] Key '{key}' not found in English. Using default value.")
            return default

        # 4. As a last resort, return the key itself
        logging.error(f"[LocaleManager] Chave '{key}' não encontrada em nenhum arquivo de tradução e sem default fornecido.")
        return key# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
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

# File: ui/handlers/locale_manager.py
# Author: Gabriel Moraes
# Date: December 16, 2025

"""
Define o LocaleManager, o "cérebro" do sistema de tradução da UI.
Nesta versão, o método get_string foi atualizado para aceitar o argumento
'default' (anteriormente 'fallback') para compatibilidade com as Views.
"""

import os
import json
import logging
from typing import Dict, Any, List

from ui.handlers.settings_handler import SettingsHandler

class LocaleManager:
    """
    Gerencia o carregamento e o acesso às strings de tradução da UI.
    """
    def __init__(self):
        """
        Inicializa o gerenciador de tradução, lendo a configuração
        de idioma salva.
        """
        self.locales_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "locales"))
        self.fallback_lang_code = "en_us"
        
        self.current_lang_data: Dict[str, Any] = {}
        self.fallback_lang_data: Dict[str, Any] = {}

        settings_handler = SettingsHandler()
        current_settings = settings_handler.get_current_settings()
        initial_lang_code = current_settings.get('language', 'pt_br')
        
        logging.info(f"[LocaleManager] Idioma inicial definido como '{initial_lang_code}' a partir das configurações.")
        self.load_language(initial_lang_code)

    def _load_file(self, lang_code: str) -> Dict[str, Any]:
        """
        Lê e processa um único arquivo JSON de tradução.
        """
        file_path = os.path.join(self.locales_dir, f"{lang_code}.json")
        if not os.path.exists(file_path):
            logging.error(f"[LocaleManager] Arquivo de tradução não encontrado: {file_path}")
            return {}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"[LocaleManager] Falha ao carregar ou processar o arquivo '{file_path}': {e}")
            return {}

    def load_language(self, lang_code: str):
        """
        Carrega um novo idioma como o principal e garante que o idioma de fallback (inglês)
        esteja sempre carregado como reserva.
        """
        logging.info(f"[LocaleManager] Carregando idioma: '{lang_code}'...")
        
        self.fallback_lang_data = self._load_file(self.fallback_lang_code)
        if not self.fallback_lang_data:
            logging.critical("[LocaleManager] FALHA CRÍTICA: Não foi possível carregar o idioma de fallback (en_us).")

        if lang_code == self.fallback_lang_code:
            self.current_lang_data = self.fallback_lang_data
        else:
            self.current_lang_data = self._load_file(lang_code)
        
        logging.info(f"'{lang_code}' carregado com sucesso.")

    def _get_nested_value(self, data: Dict, keys: List[str]) -> str | None:
        """
        Navega em um dicionário aninhado usando uma lista de chaves.
        """
        temp_dict = data
        for key in keys:
            if isinstance(temp_dict, dict) and key in temp_dict:
                temp_dict = temp_dict[key]
            else:
                return None
        return str(temp_dict) if isinstance(temp_dict, (str, int, float, bool)) else None

    def get_string(self, key: str, default: str = None) -> str:
        """
        Obtém uma string de tradução usando uma chave aninhada (ex: "main_ui.app_title").
        Implementa a lógica de fallback para o inglês e para um valor padrão (default).
        """
        keys = key.split('.')
        
        # 1. Try the translation in the current language
        translation = self._get_nested_value(self.current_lang_data, keys)
        if translation is not None:
            return translation
            
        # 2. If it fails, try the translation in the fallback language (English)
        # logging.warning(f"[LocaleManager] Key '{key}' not found in current language. Trying to fallback to English...")
        fallback_translation = self._get_nested_value(self.fallback_lang_data, keys)
        if fallback_translation is not None:
            return fallback_translation
            
        # 3. If it fails again, use the default value provided in the call
        if default is not None:
            # logging.warning(f"[LocaleManager] Key '{key}' not found in English. Using default value.")
            return default

        # 4. As a last resort, return the key itself
        logging.error(f"[LocaleManager] Chave '{key}' não encontrada em nenhum arquivo de tradução e sem default fornecido.")
        return key