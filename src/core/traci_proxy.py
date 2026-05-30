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

# File: src/core/traci_proxy.py (CHANGED TO ADD MATURITY COMMAND)
# Author: Gabriel Moraes
# Date: October 8, 2025

import logging
from multiprocessing.connection import Connection

_PIPE_CONN: Connection = None

def init_proxy_pipe(pipe_conn: Connection):
    """Initializes the Pipe connection for this proxy process."""
    global _PIPE_CONN
    _PIPE_CONN = pipe_conn
    logging.info("[TRACI_PROXY] Proxy communication pipe initialized.")

class _TraciModuleProxy:
    """A generic class that represents a TraCI submodule (e.g., simulation, trafficlight)."""
    def __init__(self, module_name: str):
        self._module_name = module_name

    def __getattr__(self, func_name: str):
        """Intercepts any function call to this module (e.g., getIDList)."""
        def _proxy_call(*args, **kwargs):
            """Packages and sends the function call to the CentralController via Pipe."""
            if _PIPE_CONN is None:
                raise RuntimeError("The TraCI Proxy connection (Pipe) has not been initialized.")

            request = (self._module_name, func_name, args, kwargs)
            
            _PIPE_CONN.send(request)
            result = _PIPE_CONN.recv()

            if isinstance(result, Exception):
                raise result
            
            return result
        
        return _proxy_call

# --- Fake Top-Level TraCI Functions ---

def connect(*args, **kwargs):
    logging.info("[TRACI_PROXY] Call to 'connect' intercepted and ignored.")
    pass

def close(*args, **kwargs):
    logging.info("[TRACI_PROXY] Call to 'close' intercepted and ignored.")
    pass

def setOrder(*args, **kwargs):
    logging.info("[TRACI_PROXY] Call to 'setOrder' intercepted and ignored.")
    pass

def load(*args, **kwargs):
    logging.info("[TRACI_PROXY] Command 'load' intercepted and sent to Central Controller.")
    if _PIPE_CONN is None:
        raise RuntimeError("The TraCI Proxy connection (Pipe) has not been initialized.")
    
    request = ('traci', 'load', args, kwargs)
    _PIPE_CONN.send(request)
    
    result = _PIPE_CONN.recv()
    if isinstance(result, Exception):
        raise result
    return result

def simulationStep(*args, **kwargs):
    if _PIPE_CONN is None:
        raise RuntimeError("The TraCI Proxy connection (Pipe) has not been initialized.")
        
    request = ('traci', 'simulationStep', args, kwargs)
    _PIPE_CONN.send(request)
    _PIPE_CONN.recv()

# --- MAIN CHANGE HERE ---
def update_maturity_state(maturity_dict: dict):
    """
    Sends the maturity state dictionary to the CentralController.
    This is not a real TraCI function but uses the same proxy mechanism.
    """
    if _PIPE_CONN is None:
        raise RuntimeError("The TraCI Proxy connection (Pipe) has not been initialized.")
    
    # Packages the call as a 'custom' command
    request = ('custom', 'update_maturity_state', (maturity_dict,), {})
    _PIPE_CONN.send(request)
    _PIPE_CONN.recv() # Wait for a simple confirmation to maintain sync
# --- END OF CHANGE ---


# --- Fake TraCI Modules ---
simulation = _TraciModuleProxy('simulation')
lane = _TraciModuleProxy('lane')
vehicle = _TraciModuleProxy('vehicle')
trafficlight = _TraciModuleProxy('trafficlight')
junction = _TraciModuleProxy('junction')
gui = _TraciModuleProxy('gui')
custom = _TraciModuleProxy('custom')
edge = _TraciModuleProxy('edge')