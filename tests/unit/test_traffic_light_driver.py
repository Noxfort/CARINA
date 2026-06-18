# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems

import os
import pytest
from unittest.mock import MagicMock, patch
from src.drivers.traffic_light_driver import TrafficLightDriver

@pytest.mark.unit
def test_traffic_light_driver_log_carina_colors(tmp_path):
    # Setup dummy driver
    driver = TrafficLightDriver(
        intersection_id="J1",
        ip_address="127.0.0.1",
        port=161,
        green_stages=[0, 2]
    )
    driver.is_connected = True
    driver.hardware_driver = MagicMock()
    
    stage_codes = {
        0: "GgOrrOGGO",
        2: "yyyrrrGyy"
    }

    # Redirect logging path to tmp_path/carina_colors.log
    log_file_path = os.path.join(tmp_path, "carina_colors.log")
    
    original_join = os.path.join

    with patch("os.path.abspath") as mock_abspath, patch("os.path.join") as mock_join:
        # We want to intercept os.path.join(project_root, "carina_colors.log")
        def side_effect_join(*args):
            if len(args) >= 2 and args[-1] == "carina_colors.log":
                return log_file_path
            return original_join(*args)
            
        mock_abspath.side_effect = lambda x: x
        mock_join.side_effect = side_effect_join

        # 1. Test stage index 0
        driver.log_carina_colors(current_stage_idx=0, stage_codes=stage_codes)
        
        # Verify content
        assert os.path.exists(log_file_path)
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == "estágio 1: GgOrrOGGO"

        # 2. Test stage index 2
        driver.log_carina_colors(current_stage_idx=2, stage_codes={0: "GgOrrOGGO", 2: "yyyrrrGyy"})
        
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert lines[1].strip() == "estágio 3: yyyrrrGyy"

        # 3. Test all-red stage index 4
        driver.log_carina_colors(current_stage_idx=4, stage_codes={4: "rrrrrrrrr"})
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 3
        assert lines[2].strip() == "estágio 0: rrrrrrrrr"

@pytest.mark.unit
def test_traffic_light_driver_load_states_from_map(tmp_path):
    # Create a dummy net.xml file
    net_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.16" junctionCornerDetail="5" limitTurnSpeed="5.50" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/net_file.xsd">
    <tlLogic id="J_MAP_TEST" type="static" programID="0" offset="0">
        <phase duration="42" state="GgOrrOGGO_MAP"/>
        <phase duration="3" state="yyyrrrGyy_MAP"/>
    </tlLogic>
</net>
"""
    map_file_path = os.path.join(tmp_path, "test_map.net.xml")
    with open(map_file_path, "w", encoding="utf-8") as f:
        f.write(net_xml_content)

    with patch("src.controller.map_discoverer.MapTopologyDiscoverer.get_map_file", return_value=map_file_path):
        driver = TrafficLightDriver(
            intersection_id="J_MAP_TEST",
            ip_address="127.0.0.1",
            port=161,
            green_stages=[0, 1]
        )
        
        # Verify that it loaded states correctly from the map file
        assert driver.stage_states == {
            0: "GgOrrOGGO_MAP",
            1: "yyyrrrGyy_MAP"
        }
