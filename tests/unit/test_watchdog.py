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
# File: tests/unit/test_watchdog.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import pytest
import time
from src.watchdog import Watchdog

@pytest.fixture
def watchdog_instance():
    """
    Creates an isolated instance of the Watchdog (Safety).
    """
    # Create the instance setting 500ms of timeout
    wd = Watchdog(timeout_ms=500)
    return wd

@pytest.mark.unit
def test_watchdog_healthy_pulse(watchdog_instance):
    """
    Tests if sending constant pulses prevents the security trigger.
    """
    wd = watchdog_instance
    
    # Register the manual heartbeat (simulating Synapse)
    wd.register_heartbeat()
    time.sleep(0.1)
    
    # Verify system health
    is_healthy = wd.check_system_health()
    
    assert is_healthy is True
    assert wd.is_in_failsafe is False

@pytest.mark.unit
def test_watchdog_timeout_trigger(watchdog_instance):
    """
    Simulates a delay greater than timeout_ms and verifies if failsafe is activated.
    """
    wd = watchdog_instance
    
    # Register base heartbeat and artificially delay it
    wd.register_heartbeat()
    wd._last_heartbeat_time = time.perf_counter() - 0.6  # 600ms gap
    
    # The check must return False and activate Failsafe
    is_healthy = wd.check_system_health()
    
    assert is_healthy is False
    assert wd.is_in_failsafe is True

@pytest.mark.unit
def test_watchdog_recovery(watchdog_instance):
    """
    Tests if the Watchdog can recover after entering Failsafe.
    """
    wd = watchdog_instance
    wd._last_heartbeat_time = time.perf_counter() - 0.6
    wd.check_system_health()
    assert wd.is_in_failsafe is True
    
    # New heartbeat must reset the system
    wd.register_heartbeat()
    assert wd.is_in_failsafe is False
