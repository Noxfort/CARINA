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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/sas/summary_directive_builder.py
# Author: Gabriel Moraes
# Date: August 12, 2026

from sas.template_repository import TemplateRepository

class SummaryDirectiveBuilder:
    """
    Responsibility (SRP): Constructs consolidated summary lists and operational 
    conclusion directives Markdown blocks dynamically from JSON templates.
    Follows SOLID principles.
    """

    @classmethod
    def get_consolidated_summary(
        cls,
        total_junctions: int,
        keep_count: int,
        remove_count: int,
        add_count: int,
        no_signal_count: int,
        language: str,
        optimize_count: int = 0
    ) -> str:
        """
        Builds the consolidated summary section Markdown string.

        :param total_junctions: Total evaluated intersections count
        :param keep_count: Count of intersections to maintain
        :param remove_count: Count of intersections to remove
        :param add_count: Count of intersections to add
        :param no_signal_count: Count of intersections maintained unsignalized
        :param language: Target language code
        :param optimize_count: Count of intersections to optimize
        :return: Consolidated summary Markdown string
        """
        templates = TemplateRepository.load_templates()
        lang_key = (language or "pt_br").lower()

        summary_dict = templates.get("consolidated_summary_items", {}).get(lang_key)
        if not summary_dict:
            summary_dict = templates.get("consolidated_summary_items", {}).get("pt_br", {})

        header_template = summary_dict.get(
            "header",
            "Resumo Consolidado de Intervenções e Recomendação de Ações\n\n**Total de Cruzamentos Avaliados:** {total_junctions}\n"
        )
        header_str = header_template.format(total_junctions=total_junctions)

        items = []
        if optimize_count > 0 and "optimize" in summary_dict:
            items.append(summary_dict["optimize"].format(count=optimize_count))
        if add_count > 0 and "add" in summary_dict:
            items.append(summary_dict["add"].format(count=add_count))
        if keep_count > 0 and "keep" in summary_dict:
            items.append(summary_dict["keep"].format(count=keep_count))
        if remove_count > 0 and "remove" in summary_dict:
            items.append(summary_dict["remove"].format(count=remove_count))
        if no_signal_count > 0 and "no_signal" in summary_dict:
            items.append(summary_dict["no_signal"].format(count=no_signal_count))

        if not items and "stable_operation" in summary_dict:
            items.append(summary_dict["stable_operation"])

        items_str = "\n".join(items)
        return f"{header_str}{items_str}\n\n"

    @classmethod
    def get_conclusions_section(
        cls,
        add_count: int,
        remove_count: int,
        keep_count: int,
        no_signal_count: int,
        conclusion_text: str,
        has_last_report: bool,
        language: str,
        optimize_count: int = 0
    ) -> str:
        """
        Builds operational directives conclusions section Markdown string.

        :param add_count: Count of intersections to add
        :param remove_count: Count of intersections to remove
        :param keep_count: Count of intersections to maintain
        :param no_signal_count: Count of intersections maintained unsignalized
        :param conclusion_text: Historical comparison conclusion text
        :param has_last_report: True if previous analysis exists
        :param language: Target language code
        :param optimize_count: Count of intersections to optimize
        :return: Operational directives Markdown string
        """
        templates = TemplateRepository.load_templates()
        lang_key = (language or "pt_br").lower()

        directives_dict = templates.get("conclusions_directives", {}).get(lang_key)
        if not directives_dict:
            directives_dict = templates.get("conclusions_directives", {}).get("pt_br", {})

        header_str = directives_dict.get(
            "header",
            "### Diretrizes Operacionais por Categoria de Intervenção\n\nCom base no parecer do motor CARINA v1.0 (SAS Engine), recomendam-se as seguintes diretrizes:\n\n"
        )

        items = []
        item_idx = 1

        if add_count > 0 and "add" in directives_dict:
            items.append(directives_dict["add"].format(idx=item_idx, count=add_count))
            item_idx += 1
        if optimize_count > 0 and "optimize" in directives_dict:
            items.append(directives_dict["optimize"].format(idx=item_idx, count=optimize_count))
            item_idx += 1
        if remove_count > 0 and "remove" in directives_dict:
            items.append(directives_dict["remove"].format(idx=item_idx, count=remove_count))
            item_idx += 1
        if keep_count > 0 and "keep" in directives_dict:
            items.append(directives_dict["keep"].format(idx=item_idx, count=keep_count))
            item_idx += 1
        if no_signal_count > 0 and "no_signal" in directives_dict:
            items.append(directives_dict["no_signal"].format(idx=item_idx, count=no_signal_count))
            item_idx += 1

        if not items and "none_required" in directives_dict:
            items.append(directives_dict["none_required"])

        base_text = header_str + "\n".join(items) + "\n\n"

        if has_last_report and conclusion_text and len(conclusion_text) > 10:
            base_text += f"{conclusion_text}\n"

        return base_text
