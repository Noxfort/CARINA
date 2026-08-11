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

# File: src/blocks/base.py
# Author: Gabriel Moraes
# Date: 2026-07-02

import logging
from typing import Dict, Any

try:
    from docx.shared import Pt, RGBColor
except ImportError:
    pass

class ReportBlock:
    """Base class for all modular report blocks."""
    def build(self, doc: Any, context: Dict[str, Any], config: Dict[str, Any]) -> None:
        raise NotImplementedError("Subclasses must implement build().")

def get_translated(config: Dict[str, Any], key: str, default: str) -> str:
    lm = config.get("locale_manager")
    if lm:
        return lm.get_string(key, default=default)
    return default

def add_markdown_paragraph(doc: Any, text: str, style: Any = None, font_size: float = None, bold: bool = False, space_before: float = None, first_line_indent: float = None) -> Any:
    p = doc.add_paragraph(style=style)
    if space_before is not None:
        p.paragraph_format.space_before = Pt(space_before)
    if first_line_indent is not None:
        try:
            from docx.shared import Cm
            p.paragraph_format.first_line_indent = Cm(first_line_indent)
        except Exception:
            pass
    
    parts = text.split('**')
    is_bold = False
    for part in parts:
        if part:
            run = p.add_run(part)
            if is_bold or bold:
                run.bold = True
            if font_size is not None:
                run.font.size = Pt(font_size)
            try:
                run.font.color.rgb = RGBColor(0, 0, 0)
            except:
                pass
        is_bold = not is_bold
    return p
