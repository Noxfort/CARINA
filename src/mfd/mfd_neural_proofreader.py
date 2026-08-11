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

# File: src/mfd/mfd_neural_proofreader.py
# Author: Gabriel Moraes
# Date: August 9, 2026

import logging
from typing import Any
from blocks.report_post_processor import ReportPostProcessor

class MFDNeuralProofreader:
    """
    Responsibility (SRP): Execute global 2nd pass neural proofreading on narrative report sections
    using the SLM Transducer, enforcing safety boundaries and clean fallback error handling.
    """

    @staticmethod
    def proofread_narrative(narrative_text: str, raw_exec_summary: str = "", transducer: Any = None, lang: str = "pt_br") -> str:
        """
        Executes a single global proofreading pass over narrative sections 1 through 5.

        :param narrative_text: Input narrative Markdown text
        :param raw_exec_summary: Raw executive summary string to check bypass conditions
        :param transducer: SLM transducer instance
        :param lang: UI target language
        :return: Proofread narrative Markdown text string
        """
        if not narrative_text or len(narrative_text.strip()) < 10:
            return narrative_text

        # Bypass proofreading pass if transducer is missing or does not have review_text method
        if transducer is None or not hasattr(transducer, "review_text"):
            return narrative_text

        try:
            logging.info("[MFD_NEURAL_PROOFREADER] Executing single global proofreading pass on narrative sections 1-5...")
            revised_text = transducer.review_text(narrative_text, language=lang)
            if revised_text and len(revised_text.strip()) > len(narrative_text) * 0.4:
                logging.info("[MFD_NEURAL_PROOFREADER] Global proofreading pass completed successfully.")
                narrative_text = revised_text
            else:
                logging.warning("[MFD_NEURAL_PROOFREADER] Proofreading returned truncated output; retaining original draft.")
        except Exception as rev_err:
            logging.warning(f"[MFD_NEURAL_PROOFREADER] Single global proofreading pass failed: {rev_err}")

        narrative_text = ReportPostProcessor.enforce_semantic_consistency(narrative_text)
        narrative_text = ReportPostProcessor.sanitize_truncated_text(narrative_text)
        return narrative_text
