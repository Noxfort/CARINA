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

# File: ui/widgets/monitor_settings_card.py
# Author: Gabriel Moraes
# Date: 2026-03-03

"""
Define o MonitorSettingsCard, um widget componente para a tela de Configurações
usado para configurar a integração com o sistema externo "Monitor" via MQTT.
"""

import flet as ft
from typing import Dict, Any
import threading
import json
import paho.mqtt.client as mqtt

from ui.handlers.locale_manager import LocaleManager

class MonitorSettingsCard(ft.Card):
    """
    Um Card que encapsula as configurações de integração com o Monitor Externo.
    """
    def __init__(self, initial_values: Dict[str, Any], on_toggle_connection=None):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()
        
        self.on_toggle_connection = on_toggle_connection

        # --- Controls ---
        self.title_text = ft.Text("External Monitor Integration", size=18, weight=ft.FontWeight.BOLD)
        
        self.is_connected = str(initial_values.get('monitor_enabled', 'False')).lower() == 'true'
        
        self.tf_host = ft.TextField(
            label="MQTT Broker Host (IP/Domain)",
            value=initial_values.get('monitor_mqtt_host', 'localhost'),
            expand=True,
            disabled=self.is_connected
        )
        
        # Action Buttons
        self.btn_connect = ft.ElevatedButton(
            text="Connect", 
            icon=ft.Icons.LOGIN_ROUNDED, 
            on_click=self._handle_connect,
            visible=not self.is_connected
        )
        
        self.btn_disconnect = ft.OutlinedButton(
            text="Disconnect", 
            icon=ft.Icons.LOGOUT_ROUNDED, 
            on_click=self._handle_disconnect,
            visible=self.is_connected
        )

        # Status Display
        self.status_icon = ft.Icon(
            name=ft.Icons.RADIO_BUTTON_CHECKED if self.is_connected else ft.Icons.RADIO_BUTTON_UNCHECKED,
            color=ft.colors.GREEN_500 if self.is_connected else ft.colors.RED_500,
            size=16
        )
        self.status_text = ft.Text(
            "CONNECTED" if self.is_connected else "DISCONNECTED", 
            color=ft.colors.GREEN_500 if self.is_connected else ft.colors.RED_500, 
            weight=ft.FontWeight.W_500
        )
        self.status_display = ft.Row([self.status_icon, self.status_text], alignment=ft.MainAxisAlignment.START)
        
        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                ft.Row([
                    ft.Row([ft.Icon(ft.Icons.MONITOR_HEART), self.title_text]),
                    self.status_display
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Container(height=5),
                ft.Row([self.tf_host], alignment=ft.MainAxisAlignment.START),
                ft.Row([self.btn_connect, self.btn_disconnect], alignment=ft.MainAxisAlignment.END)
            ])
        )

    def _update_ui_state(self):
        self.tf_host.disabled = self.is_connected
        
        self.btn_connect.visible = not self.is_connected
        self.btn_disconnect.visible = self.is_connected
        
        self.status_icon.name = ft.Icons.RADIO_BUTTON_CHECKED if self.is_connected else ft.Icons.RADIO_BUTTON_UNCHECKED
        self.status_icon.color = ft.colors.GREEN_500 if self.is_connected else ft.colors.RED_500
        
        status_str = "CONNECTED" if self.is_connected else "DISCONNECTED"
        if hasattr(self, 'lm') and self.lm:
            key = "settings_view.monitor_card.status_connected" if self.is_connected else "settings_view.monitor_card.status_disconnected"
            status_str = self.lm.get_string(key, default=status_str)
            
        self.status_text.value = status_str.upper()
        self.status_text.color = ft.colors.GREEN_500 if self.is_connected else ft.colors.RED_500

        if self.page:
            self.update()

    def _handle_connect(self, e):
        self.is_connected = True
        self._update_ui_state()
        
        # Fire an immediate heartbeat in the background so the UI doesn't freeze
        host = self.tf_host.value
        threading.Thread(target=self._send_immediate_ping, args=(host,), daemon=True).start()
        
        if self.on_toggle_connection:
            self.on_toggle_connection(True, host)

    def _send_immediate_ping(self, host: str):
        """Envia o heartbeat no formato exato solicitado assim que conecta pela UI."""
        payload = {
            "origin": "Carina",
            "level": "info",
            "message": "heartbeat"
        }
        try:
            target_host = host
            target_port = 1883
            if ":" in host:
                parts = host.split(":", 1)
                target_host = parts[0]
                try:
                    target_port = int(parts[1])
                except ValueError:
                    pass

            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="carina_ui_ping")
            client.connect(target_host, target_port, keepalive=5)
            info = client.publish("noxfort/telemetry/", json.dumps(payload), qos=0)
            info.wait_for_publish()
            client.disconnect()
        except Exception as err:
            print(f"Failed to send immediate monitor ping from UI to {host}: {err}")
        
    def _handle_disconnect(self, e):
        self.is_connected = False
        self._update_ui_state()
        
        if self.on_toggle_connection:
            self.on_toggle_connection(False, self.tf_host.value)

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'monitor_enabled': str(self.is_connected),
            'monitor_mqtt_host': self.tf_host.value
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.is_connected = str(values.get('monitor_enabled', 'False')).lower() == 'true'
        self.tf_host.value = values.get('monitor_mqtt_host', 'localhost')
        self._update_ui_state()

    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.lm = lm
        self.title_text.value = lm.get_string("settings_view.monitor_card.title", default="External Monitor Integration")
        self.tf_host.label = lm.get_string("settings_view.monitor_card.host", default="MQTT Broker Host (IP/Domain)")
        
        self.btn_connect.text = lm.get_string("settings_view.monitor_card.btn_connect", default="Connect")
        self.btn_disconnect.text = lm.get_string("settings_view.monitor_card.btn_disconnect", default="Disconnect")
        
        self._update_ui_state()
