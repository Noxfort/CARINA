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

# File: tests/unit/test_xai_report_builder.py
# Author: Gabriel Moraes
# Date: 2026-06-19

import os
import pytest
from xai.structured_report_builder import XaiStructuredReportBuilder

def test_xai_structured_report_builder_generation(tmp_path):
    # Setup destinations
    output_docx = os.path.join(tmp_path, "test_report.docx")
    
    # Mock configurations
    config = {
        "logo_path": "",
        "secretary_name": "Dr. Test Secretary",
        "secretary_title": "Director of Test Automation",
        "agency_name": "Test Authority Group",
        "department_name": "Quality Assurance Bureau",
        "title": "LAUDO AUTOMÁTICO DE TESTES UNITÁRIOS",
        "font_name": "Times New Roman",
        "font_size": 12,
        "margin_top": 1.25,
        "margin_bottom": 1.25,
        "margin_left": 1.25,
        "margin_right": 1.25,
        "line_spacing": 1.5,
        "alignment": "left"
    }
    
    # Mock contexts
    context = {
        "agent_id": "intersection_123",
        "scenario": "test_scenario_suite",
        "engine_version": "CARINA TestEngine v1.0.0",
        "image_path": "",
        "text_content": "### Parecer Técnico\nO agente priorizou o fluxo da avenida principal devido à detecção de longa fila no sensor 1."
    }
    
    # Test all blocks
    builder = XaiStructuredReportBuilder()
    success = builder.generate_report(output_docx, context, config)
    
    assert success is True
    assert os.path.exists(output_docx)
    assert os.path.getsize(output_docx) > 0

def test_xai_structured_report_builder_custom_block_order(tmp_path):
    output_docx = os.path.join(tmp_path, "test_report_custom.docx")
    
    config = {
        "secretary_name": "Dr. Test Secretary",
        "title": "TITULO REORDENADO"
    }
    
    context = {
        "agent_id": "agent_456",
        "text_content": "Texto de teste"
    }
    
    # Generate report with custom block order
    builder = XaiStructuredReportBuilder(block_order=["title", "content", "signature"])
    success = builder.generate_report(output_docx, context, config)
    
    assert success is True
    assert os.path.exists(output_docx)
    assert os.path.getsize(output_docx) > 0
