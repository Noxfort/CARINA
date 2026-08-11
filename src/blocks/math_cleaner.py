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

# File: src/blocks/math_cleaner.py
# Author: Gabriel Moraes
# Date: July 25, 2026

import re

def clean_latex_math(eq: str) -> str:
    """
    Cleans LaTeX mathematical syntax for clean Word document rendering.
    Processes:
    - Fractions \\frac{num}{den} into num / (den) or num / den
    - Subscript variables (v_{real} -> v_real, P_{95} -> P_95, F_{ideal} -> F_ideal)
    - Stripping \\mathbf, \\text, \\tag and LaTeX escape characters
    """
    if not eq:
        return ""

    eq = eq.replace('$$', '').replace('$', '').strip()

    # Clean \\tag{...} and \\mathbf{...}
    eq = re.sub(r'\\tag\{[^{}]+\}', '', eq)
    eq = re.sub(r'\\mathbf\s*\{', '', eq)

    # Clean \\left and \\right delimiters
    eq = eq.replace(r'\left(', '(').replace(r'\right)', ')')
    eq = eq.replace(r'\left[', '[').replace(r'\right]', ']')
    eq = eq.replace(r'\left\{', '{').replace(r'\right\}', '}')
    eq = eq.replace(r'\left', '').replace(r'\right', '')

    # Clean \\text{...}
    eq = re.sub(r'\\text\{([^{}]+)\}', r'\1', eq)

    # Process \\frac{num}{den} robustly
    def _format_frac(m):
        num = m.group(1).strip()
        den = m.group(2).strip()
        if r'\times' in den or r'\cdot' in den or '*' in den or '+' in den or '-' in den or ' ' in den or '×' in den:
            return f"{num} / ({den})"
        return f"{num} / {den}"

    frac_pattern = re.compile(r'\\frac\{((?:[^{}]|\{[^{}]*\})+)\}\{((?:[^{}]|\{[^{}]*\})+)\}')
    max_loops = 5
    while r'\frac' in eq and max_loops > 0:
        max_loops -= 1
        new_eq = frac_pattern.sub(_format_frac, eq)
        if new_eq == eq:
            eq = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 / \2', eq)
            break
        eq = new_eq

    # Clean subscripts (v_{real} -> v_real, v_{limite} -> v_limite, F_{ideal} -> F_ideal, P_{95} -> P_95)
    eq = re.sub(r'([a-zA-Z0-9]+)_\{([a-zA-Z0-9_]+)\}', r'\1_\2', eq)
    eq = re.sub(r'([a-zA-Z0-9]+)_([a-zA-Z0-9]+)', r'\1_\2', eq)
    eq = eq.replace('P_{95}', 'P_95').replace('P95', 'P_95')
    eq = eq.replace('v_{real}', 'v_real').replace('vreal', 'v_real')
    eq = eq.replace('v_{limite}', 'v_limite').replace('vlimite', 'v_limite')
    eq = eq.replace('F_{ideal}', 'F_ideal').replace('Fideal', 'F_ideal')

    # Clean latex multiplication & math operators
    eq = eq.replace(r'\times', '×').replace(r'\cdot', '·')
    eq = eq.replace(r'\sum_{a}', '∑ₐ').replace(r'\sum_{', '∑_').replace(r'\sum', '∑')
    eq = eq.replace(r'\log', 'log')
    eq = eq.replace(r'\Delta', 'Δ').replace(r'\delta', 'δ')
    eq = eq.replace(r'\pi', 'π')
    eq = eq.replace(r'\mathcal{H}', 'H').replace(r'\mathcal{P}', 'P')
    eq = eq.replace(r'\%', '%')
    eq = eq.replace(r'\infty', '∞').replace(r'\approx', '≈')
    eq = eq.replace(r'\leq', '≤').replace(r'\geq', '≥').replace(r'\neq', '≠')

    # Clean any remaining unknown LaTeX keywords or backslashes
    eq = re.sub(r'\\[a-zA-Z]+', '', eq)
    eq = eq.replace('{', '').replace('}', '').replace('\\', '')

    # Clean inline math $...$
    def replace_inline(match):
        val = match.group(1)
        val = re.sub(r'([a-zA-Z0-9]+)_\{([a-zA-Z0-9_]+)\}', r'\1_\2', val)
        val = re.sub(r'([a-zA-Z0-9]+)_([a-zA-Z0-9]+)', r'\1_\2', val)
        val = val.replace('P_{95}', 'P_95').replace('P95', 'P_95')
        val = val.replace('{', '').replace('}', '').replace('\\', '')
        return val

    eq = re.sub(r'\$([^$]+)\$', replace_inline, eq)

    # Remove duplicate spaces
    eq = re.sub(r'\s+', ' ', eq).strip()
    return eq
