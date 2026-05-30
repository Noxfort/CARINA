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
#
# File: tests/unit/test_core_components.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import pytest
import os
import sys

def test_enums_maturity():
    """
    Tests if we can load and use the core Enums (Maturity)
    """
    try:
        from src.core.enums import Maturity
        assert Maturity.CHILD.name == 'CHILD'
        assert Maturity.ADULT.name == 'ADULT'
    except ImportError as e:
        pytest.fail(f"Failed to load core enums: {e}")

def test_ai_process_function_exists():
    """
    Tests if the main AI entry port (HFT) exists
    (without invoking it to avoid setting up tensors).
    """
    try:
        from src.main import run_ai_process
        assert callable(run_ai_process), "run_ai_process must be callable"
    except ImportError as e:
        pytest.fail(f"Failed to load main.py: {e}")

@pytest.mark.unit
def test_locale_backend():
    """
    Ensures that the locale manager can be initialized without crashing.
    """
    try:
        from src.utils.locale_manager_backend import LocaleManagerBackend
        lm = LocaleManagerBackend()
        # The default should be pt_BR or en_US, testing if it's not empty
        assert lm.current_lang_data is not None
        assert isinstance(lm.get_string("dummy.key", fallback="fallback_value"), str)
    except Exception as e:
        pytest.fail(f"Failure in Locales Manager: {e}")
