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
from utils.audit_logger import AuditLogger

class UICommandHandler:
    """
    Handles all commands incoming from the Front-End (UI). 
    Actions include saving settings, changing global modes, and manual overrides.
    """
    def __init__(self, locale_manager, override_manager, failsafe_manager, security_manager, sds_data_queue, sas_data_queue=None, mfd_trigger_queue=None):
        self.locale_manager = locale_manager
        self.override_manager = override_manager
        self.failsafe_manager = failsafe_manager
        self.security_manager = security_manager
        self.sds_data_queue = sds_data_queue
        self.sas_data_queue = sas_data_queue
        self.mfd_trigger_queue = mfd_trigger_queue
        self.audit_logger = AuditLogger()
        self.last_auth_user = "Sistema"
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
            
            new_lang = None
            if "General" in payload and "language" in payload["General"]:
                new_lang = payload["General"]["language"]
            elif "language" in payload:
                new_lang = payload["language"]
                
            if new_lang:
                self.locale_manager.load_language(new_lang)
                
            self.audit_logger.log_action(self.last_auth_user, "SAVE_SETTINGS", "Configurações Globais alteradas")
            logging.info(lm.get_string("request_processor.ui_command.save_success"))

        elif cmd_type == "authenticate":
            username = payload.get("username")
            password = payload.get("password")
            success, role_or_msg = self.security_manager.authenticate(username, password)
            if success:
                self.last_auth_user = username
                self.audit_logger.log_action(username, "LOGIN_SUCCESS", f"Sessão iniciada como {role_or_msg}")
                self.sds_data_queue.put(('auth_response', {"success": True, "role": role_or_msg}))
            else:
                self.audit_logger.log_action(username or "UNKNOWN", "LOGIN_FAILED", "Falha de autenticação")
                self.sds_data_queue.put(('auth_response', {"success": False, "message": role_or_msg}))
                
                if hasattr(self.failsafe_manager, 'monitor_client') and self.failsafe_manager.monitor_client:
                    msg = self.locale_manager.get_string("monitor.auth_failure", default="Falha de autenticação detectada para o usuário: {username}", username=username)
                    self.failsafe_manager.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="WARNING",
                        message=msg
                    )

                if self.security_manager.is_lockdown():
                    logging.critical("[UICommandHandler] Lockdown ativado. Cortando heartbeats físicos.")
                    override_commands_buffer.append({"semaphore_id": "ALL", "state": "SHUTDOWN"})
                    self.sds_data_queue.put(('lockdown_event', {"active": True}))
                    
                    if hasattr(self.failsafe_manager, 'monitor_client') and self.failsafe_manager.monitor_client:
                        msg = self.locale_manager.get_string("monitor.lockdown_active", default="LOCKDOWN de segurança ativado devido a múltiplas falhas de login.")
                        self.failsafe_manager.monitor_client.report_incident(
                            category="SOFTWARE",
                            level="CRITICAL",
                            message=msg
                        )

        elif cmd_type == "check_lockdown":
            if self.security_manager.is_lockdown():
                self.sds_data_queue.put(('lockdown_event', {"active": True}))

        elif cmd_type == "add_user":
            username = payload.get("username")
            password = payload.get("password")
            role = payload.get("role")
            success = self.security_manager.add_user(username, password, role)
            if success: self.audit_logger.log_action(self.last_auth_user, "ADD_USER", f"Usuário {username} criado ({role}).")
            self.sds_data_queue.put(('account_response', {"action": "add", "success": success}))
            if success:
                self.sds_data_queue.put(('users_list', {"users": self.security_manager.list_users()}))

        elif cmd_type == "remove_user":
            username = payload.get("username")
            success = self.security_manager.remove_user(username)
            if success: self.audit_logger.log_action(self.last_auth_user, "REMOVE_USER", f"Usuário {username} deletado.")
            self.sds_data_queue.put(('account_response', {"action": "remove", "success": success}))
            if success:
                self.sds_data_queue.put(('users_list', {"users": self.security_manager.list_users()}))

        elif cmd_type == "list_users":
            users = self.security_manager.list_users()
            self.sds_data_queue.put(('users_list', {"users": users}))

        elif cmd_type == "get_audit_logs":
            self.sds_data_queue.put(('audit_logs_response', {"logs": self.audit_logger.get_logs()}))

        elif cmd_type == "set_global_mode":
            new_mode = payload.get("mode", "AUTOMATIC").upper()
            old_mode = self.failsafe_manager.current_operation_mode
            if new_mode != old_mode and new_mode in ["AUTOMATIC", "SEMI_AUTOMATIC", "MANUAL"]:
                logging.info(f"[CONTROLE GLOBAL] Modo de operação alterado de '{old_mode}' para '{new_mode}' pelo operador.")
                self.audit_logger.log_action(self.last_auth_user, "GLOBAL_MODE_CHANGE", f"De {old_mode} para {new_mode}")
                self.failsafe_manager.current_operation_mode = new_mode
            elif new_mode != old_mode:
                 logging.warning(f"[RequestProcessor] Tentativa de definir modo global inválido: '{new_mode}'")

        elif cmd_type == "set_semaphore_override":
            semaphore_id = payload.get('semaphore_id', 'N/A')
            new_state = payload.get('state', 'N/A')
            self.audit_logger.log_action(self.last_auth_user, "OVERRIDE_SEMAPHORE", f"{semaphore_id} -> {new_state}")
            logging.warning(
                lm.get_string(
                    "request_processor.override.manual_intervention",
                    semaphore_id=semaphore_id,
                    state=new_state
                )
            )
            if sumo_conn:
                override_commands_buffer.append(payload)
                self.override_manager.handle_ui_command(payload, sumo_conn)
            else:
                self.override_manager.active_overrides[semaphore_id] = new_state
                if new_state == "NORMAL":
                    self.override_manager.active_overrides.pop(semaphore_id, None)
                self.override_manager._save_state_to_disk()
                
                if self.failsafe_manager and self.failsafe_manager.ai_pipe_conn and not self.failsafe_manager.ai_pipe_conn.closed:
                    logging.info(f"[UICommandHandler] Sending manual override for {semaphore_id} ({new_state}) to AI process via pipe.")
                    self.failsafe_manager.ai_pipe_conn.send(('hardware', 'apply_override', (semaphore_id, new_state), {}))
                else:
                    logging.warning("[UICommandHandler] AI pipe connection is not active/closed. Manual override not forwarded.")

        elif cmd_type == "set_street_override":
            street_id = payload.get('street_id', 'N/A')
            new_state = payload.get('state', 'N/A')
            self.audit_logger.log_action(self.last_auth_user, "OVERRIDE_STREET", f"{street_id} -> {new_state}")
            logging.warning(f"[UICommandHandler] Intervenção manual na rua '{street_id}': {new_state}")
            self.override_manager.handle_street_command(payload)

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

        elif cmd_type == "set_hardware_connection":
            # Pass this through a special queue or we can handle it in request_processor
            pass

        elif cmd_type == "carina_ready":
            logging.info("✅ [RequestProcessor] Comando de 'carina_ready' recebido da Interface Gráfica.")
            if self.on_ui_ready and callable(self.on_ui_ready):
                self.on_ui_ready()
        elif cmd_type == "trigger_analysis":
            logging.info("[UICommandHandler] Recebido comando para forçar análise de planejamento.")
            if self.sas_data_queue:
                self.sas_data_queue.put(("trigger_analysis", {}))
            else:
                logging.warning("[UICommandHandler] sas_data_queue não disponível para forçar análise.")
        elif cmd_type == "trigger_mfd_analysis":
            logging.info("[UICommandHandler] Recebido comando para forçar análise MFD.")
            if self.mfd_trigger_queue:
                self.mfd_trigger_queue.put(("trigger_mfd", {}))
            else:
                logging.warning("[UICommandHandler] mfd_trigger_queue não disponível para forçar análise MFD.")
        else:
            logging.warning(f"[RequestProcessor] Comando UI desconhecido recebido: {cmd_type}")
