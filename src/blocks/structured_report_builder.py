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

# File: src/blocks/structured_report_builder.py
# Author: Gabriel Moraes
# Date: July 24, 2026

import os
import logging
from typing import Dict, Any, List

try:
    from docx import Document
    from docx.shared import Pt, Inches, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    logging.warning("[STRUCTURED_REPORT_BUILDER] python-docx not installed. DOCX reports will not be available.")

from blocks.header import HeaderBlock
from blocks.title import TitleBlock
from blocks.metadata import MetadataBlock
from blocks.chart import ChartBlock
from blocks.content import ContentBlock
from blocks.signature import SignatureBlock

class StructuredReportBuilder:
    """
    Universal coordinator for modular construction of Word DOCX reports
    across all subsystems (XAI, MFD, and Planning & Optimization).
    """

    BLOCK_REGISTRY = {
        "header": HeaderBlock(),
        "title": TitleBlock(),
        "metadata": MetadataBlock(),
        "chart": ChartBlock(),
        "planning_map": ChartBlock(),
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
            font_size = float(config.get("font_size", 11.0))
            margin_top = float(config.get("margin_top", 1.0))
            margin_bottom = float(config.get("margin_bottom", 1.0))
            margin_left = float(config.get("margin_left", 1.0))
            margin_right = float(config.get("margin_right", 1.0))
            line_spacing = float(config.get("line_spacing", 1.15))

            # Apply Normal style font, size, and black color
            style = doc.styles['Normal']
            style.font.name = font_name
            style.font.size = Pt(font_size)
            style.font.color.rgb = RGBColor(0, 0, 0)
            style.paragraph_format.line_spacing = line_spacing

            # Apply black color to other styles if they exist
            for style_name in ['Heading 1', 'Heading 2', 'Heading 3']:
                if style_name in doc.styles:
                    s = doc.styles[style_name]
                    s.font.name = font_name
                    s.font.color.rgb = RGBColor(0, 0, 0)

            # Map alignment to WD_ALIGN_PARAGRAPH
            align_map = {
                "left": WD_ALIGN_PARAGRAPH.LEFT,
                "center": WD_ALIGN_PARAGRAPH.CENTER,
                "right": WD_ALIGN_PARAGRAPH.RIGHT,
                "justify": WD_ALIGN_PARAGRAPH.JUSTIFY
            }
            alignment_str = str(config.get("alignment", "justify"))
            style.paragraph_format.alignment = align_map.get(alignment_str.lower(), WD_ALIGN_PARAGRAPH.JUSTIFY)

            # Apply base styling margins in centimeters (Cm)
            sections = doc.sections
            for section in sections:
                section.top_margin = Cm(margin_top)
                section.bottom_margin = Cm(margin_bottom)
                section.left_margin = Cm(margin_left)
                section.right_margin = Cm(margin_right)

            # Build each block sequentially
            for block_key in self.block_order:
                block = self.BLOCK_REGISTRY.get(block_key.lower())
                if block:
                    block.build(doc, context, config)

            # Fallback: Guarantee signature is rendered if not already processed in content/block_order
            if not context.get("_signature_rendered", False):
                try:
                    from blocks.signature import SignatureBlock
                    SignatureBlock().build(doc, context, config)
                except Exception as sig_err:
                    logging.warning(f"[STRUCTURED_REPORT_BUILDER] Fallback signature rendering failed: {sig_err}")

            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            doc.save(dest_path)
            logging.info(f"[STRUCTURED_REPORT_BUILDER] Successfully saved report to: {dest_path}")
            return True

        except Exception as e:
            logging.error(f"[STRUCTURED_REPORT_BUILDER] Error generating report: {e}", exc_info=True)
            return False
