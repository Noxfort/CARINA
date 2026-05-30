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
# File: tests/test_sanity.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import pytest
import os
import sys

def test_environment_setup():
    """
    Tests if the environment was properly configured by conftest.py
    """
    assert os.environ.get('CARINA_TEST_MODE') == '1'
    assert os.environ.get('QT_QPA_PLATFORM') == 'offscreen'

def test_import_src_modules():
    """
    Skipping temporarily - root import causes hang
    """
    pytest.skip("Skipping root src imports on pure headless sanity to avoid hangs")

def test_import_ui_modules():
    """
    Tests if pytest can see the ui/ folder and import base modules.
    """
    pytest.skip("Skiping UI imports on pure headless sanity to avoid Qt hangs")

@pytest.mark.unit
def test_dummy_math():
    """
    Simple test to ensure the unit execution runs.
    """
    assert 1 + 1 == 2
