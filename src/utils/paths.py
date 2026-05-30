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

# File: src/utils/paths.py (NEW FILE)
# Author: Gabriel Moraes
# Date: October 22, 2025

"""
Defines utility functions to handle file paths,
ensuring compatibility with PyInstaller (--onefile).
"""

import sys
import os
import subprocess

def resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto para um recurso (arquivo de dados),
    funcionando tanto em modo de desenvolvimento quanto no executável
    criado pelo PyInstaller.

    Args:
        relative_path (str): O caminho relativo para o recurso a partir da
                             raiz do projeto (ou do bundle).

    Returns:
        str: O caminho absoluto para o recurso.
    """
    try:
        # PyInstaller creates a temporary folder and stores the path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If _MEIPASS does not exist, we are in development mode.
        # We use abspath(".") to get the root of the project where the script/command is executed.
        # We set it to go up two levels from src/utils to get to the root.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    return os.path.join(base_path, relative_path)

def get_base_output_dir() -> str:
    """
    Retorna o diretório base (OS Documents/Carina) onde arquivos de saída (logs, results) devem ser escritos.
    Resolve a pasta Documentos do SO dinamicamente (Linux).

    Returns:
        str: O caminho absoluto para o diretório base de saída.
    """
    documents_dir = None
    try:
        # Tenta obter a pasta Documentos oficial do XDG no Linux
        output = subprocess.check_output(['xdg-user-dir', 'DOCUMENTS'], stderr=subprocess.DEVNULL)
        documents_dir = output.decode('utf-8').strip()
    except Exception:
        pass
    
    if not documents_dir or not os.path.isdir(documents_dir):
        # Fallback 1: ~/Documents
        fallback_en = os.path.expanduser("~/Documents")
        if os.path.isdir(fallback_en):
            documents_dir = fallback_en
        else:
            # Fallback 2: ~/Documentos
            fallback_pt = os.path.expanduser("~/Documentos")
            if os.path.isdir(fallback_pt):
                documents_dir = fallback_pt
            else:
                # Último recurso genérico
                documents_dir = os.path.expanduser("~")

    # A subpasta Carina será em /Documentos/Carina
    carina_dir = os.path.join(documents_dir, "Carina")
    os.makedirs(carina_dir, exist_ok=True)
    return carina_dir