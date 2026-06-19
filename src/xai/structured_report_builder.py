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

# File: src/xai/structured_report_builder.py
# Author: Gabriel Moraes
# Date: 2026-06-19

import os
import logging
from typing import Dict, Any, List

try:
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    logging.warning("[XAI_REPORT_BUILDER] python-docx not installed. DOCX reports will not be available.")

from xai.report_blocks import (
    HeaderBlock,
    TitleBlock,
    MetadataBlock,
    ChartBlock,
    ContentBlock,
    SignatureBlock
)

class XaiStructuredReportBuilder:
    """Coordinates modular construction of the XAI and MFD DOCX reports."""
    
    BLOCK_REGISTRY = {
        "header": HeaderBlock(),
        "title": TitleBlock(),
        "metadata": MetadataBlock(),
        "chart": ChartBlock(),
        "content": ContentBlock(),
        "signature": SignatureBlock()
    }
    
    def __init__(self, block_order: List[str] = None) -> None:
        self.block_order = block_order or ["header", "title", "metadata", "chart", "content", "signature"]
        
    def generate_report(self, dest_path: str, context: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Generates the structured DOCX report at the destination path."""
        try:
            doc = Document()
            
            # Extract styling options
            font_name = config.get("font_name", "Arial")
            font_size = config.get("font_size", 11)
            margin_top = config.get("margin_top", 1.0)
            margin_bottom = config.get("margin_bottom", 1.0)
            margin_left = config.get("margin_left", 1.0)
            margin_right = config.get("margin_right", 1.0)
            line_spacing = config.get("line_spacing", 1.15)
            
            # Apply Normal style font and size
            style = doc.styles['Normal']
            style.font.name = font_name
            style.font.size = Pt(font_size)
            style.paragraph_format.line_spacing = line_spacing
            
            # Map alignment to WD_ALIGN_PARAGRAPH
            align_map = {
                "left": WD_ALIGN_PARAGRAPH.LEFT,
                "center": WD_ALIGN_PARAGRAPH.CENTER,
                "right": WD_ALIGN_PARAGRAPH.RIGHT,
                "justify": WD_ALIGN_PARAGRAPH.JUSTIFY
            }
            alignment_str = config.get("alignment", "justify")
            style.paragraph_format.alignment = align_map.get(alignment_str.lower(), WD_ALIGN_PARAGRAPH.JUSTIFY)
            
            # Apply base styling margins
            sections = doc.sections
            for section in sections:
                section.top_margin = Inches(margin_top)
                section.bottom_margin = Inches(margin_bottom)
                section.left_margin = Inches(margin_left)
                section.right_margin = Inches(margin_right)
                
            # Build each block sequentially
            for block_key in self.block_order:
                block = self.BLOCK_REGISTRY.get(block_key.lower())
                if block:
                    block.build(doc, context, config)
                    
            doc.save(dest_path)
            logging.info(f"[XAI_REPORT_BUILDER] Successfully saved report to: {dest_path}")
            return True
            
        except Exception as e:
            logging.error(f"[XAI_REPORT_BUILDER] Error generating report: {e}", exc_info=True)
            return False
