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

# File: src/handlers/ui_command_handler.py
# Author: Gabriel Moraes
# Date: 2026-04-17

import logging
from typing import Any
from utils.settings_manager import SettingsManager

class UICommandHandler:
    """
    Handles all commands incoming from the Front-End (UI). 
    Actions include saving settings, changing global modes, and manual overrides.
    """
    def __init__(self, locale_manager, override_manager, failsafe_manager):
        self.locale_manager = locale_manager
        self.override_manager = override_manager
        self.failsafe_manager = failsafe_manager
        self.on_ui_ready = None

    def set_ui_ready_callback(self, cb):
        self.on_ui_ready = cb

    def process(self, command: dict, sumo_conn: Any, override_commands_buffer: list):
        lm = self.locale_manager
        cmd_type = command.get("type")
        payload = command.get("payload", {})

        logging.info(lm.get_string("request_processor.ui_command.received", type=cmd_type))

        if cmd_type == "save_settings":
            settings_manager = SettingsManager()
            settings_manager.save_settings(payload)
            logging.info(lm.get_string("request_processor.ui_command.save_success"))

        elif cmd_type == "set_global_mode":
            new_mode = payload.get("mode", "AUTOMATIC").upper()
            old_mode = self.failsafe_manager.current_operation_mode
            if new_mode != old_mode and new_mode in ["AUTOMATIC", "SEMI_AUTOMATIC", "MANUAL"]:
                logging.info(f"[CONTROLE GLOBAL] Modo de operação alterado de '{old_mode}' para '{new_mode}' pelo operador.")
                self.failsafe_manager.current_operation_mode = new_mode
            elif new_mode != old_mode:
                 logging.warning(f"[RequestProcessor] Tentativa de definir modo global inválido: '{new_mode}'")

        elif cmd_type == "set_semaphore_override":
            if sumo_conn:
                override_commands_buffer.append(payload)
                logging.warning(
                    lm.get_string(
                        "request_processor.override.manual_intervention",
                        semaphore_id=payload.get('semaphore_id', 'N/A'),
                        state=payload.get('state', 'N/A')
                    )
                )
                self.override_manager.handle_ui_command(payload, sumo_conn)
            else:
                logging.warning("[RequestProcessor] Comando de override recebido mas sem conexão SUMO direta (Modo HFT?). Comando ignorado.")

        elif cmd_type == "set_monitor_connection":
            enabled = payload.get("enabled", False)
            host = payload.get("host", "localhost")
            
            if hasattr(self.failsafe_manager, 'monitor_client') and self.failsafe_manager.monitor_client:
                if enabled:
                    self.failsafe_manager.monitor_client.connect_manual(host)
                    logging.info(f"[RequestProcessor] Monitor manually CONNECTED to {host}")
                else:
                    self.failsafe_manager.monitor_client.disconnect_manual()
                    logging.info("[RequestProcessor] Monitor manually DISCONNECTED.")
            else:
                logging.warning("[RequestProcessor] MonitorClient interface not found.")
                
            # Auto-Save connection intent for the next session
            settings_manager = SettingsManager()
            current_settings = settings_manager.load_settings()
            current_settings["monitor_enabled"] = str(enabled).lower()
            current_settings["monitor_mqtt_host"] = host
            settings_manager.save_settings(current_settings)
            logging.info("[RequestProcessor] Monitor connection state permanently saved to settings.ini.")

        elif cmd_type == "set_semaphore_timings":
            logging.warning(
                f"[CONFIGURAÇÃO MANUAL] Operador alterou os tempos do semáforo '{payload.get('semaphore_id', 'N/A')}': "
                f"Tempo de Verde='{payload.get('green_time', 'N/A')}', Tempo de Amarelo='{payload.get('yellow_time', 'N/A')}' "
                f"(Modo de Operação: {self.failsafe_manager.current_operation_mode}). (Funcionalidade não implementada no backend)"
            )
        elif cmd_type == "carina_ready":
            logging.info("✅ [RequestProcessor] Comando de 'carina_ready' recebido da Interface Gráfica.")
            if self.on_ui_ready and callable(self.on_ui_ready):
                self.on_ui_ready()
        else:
            logging.warning(f"[RequestProcessor] Comando UI desconhecido recebido: {cmd_type}")
