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

# File: src/sas/report_transducer_factory.py
# Author: Gabriel Moraes
# Date: August 10, 2026

import gc
import logging
from typing import Any

from slm.local_llama_transducer import LocalLlamaTransducer


class ReportTransducerFactory:
    """
    Factory for initializing, providing, and releasing neural transducer models used
    in technical report generation.
    """

    @staticmethod
    def create_transducer() -> Any:
        """
        Attempts to load the primary SemanticTransducer neural model.
        Falls back to LocalLlamaTransducer if initialization fails.

        Returns:
            Any: An initialized transducer instance exposing the generate_report interface.
        """
        try:
            from slm.semantic_transducer import SemanticTransducer
            transducer = SemanticTransducer()
            transducer.load_resources()
            logging.info("[REPORT_TRANSDUCER_FACTORY] SemanticTransducer (SLM) loaded successfully.")
            return transducer
        except Exception as e:
            logging.warning(
                f"[REPORT_TRANSDUCER_FACTORY] SemanticTransducer initialization failed: {e}. "
                "Falling back to LocalLlamaTransducer.",
                exc_info=True
            )
            return LocalLlamaTransducer()

    @staticmethod
    def release_transducer(transducer: Any) -> None:
        """
        Safely deletes references to the transducer model and triggers explicit garbage collection.

        Args:
            transducer (Any): Transducer instance to be released.
        """
        if transducer is not None:
            try:
                del transducer
            except Exception as e:
                logging.debug(f"[REPORT_TRANSDUCER_FACTORY] Failed to delete transducer reference: {e}")

        gc.collect()
        logging.debug("[REPORT_TRANSDUCER_FACTORY] Transducer resources released and gc.collect() executed.")
