# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/widgets/database_settings_card.py
# Author: Gabriel Moraes
# Date: 2026-04-22

import flet as ft
from typing import Dict, Any, Callable
import threading
import sqlite3
import os

from ui.handlers.locale_manager import LocaleManager
from src.utils.paths import get_base_output_dir

class DatabaseSettingsCard(ft.Card):
    """
    Card UI para configurações de Banco de Dados.
    Permite alternar entre SQLite e PostgreSQL, revelando campos extras para o Postgres,
    com botões para Conectar/Desconectar que bloqueiam os campos se a conexão for bem-sucedida.
    """
    def __init__(self, initial_values: Dict[str, Any], on_toggle_connection=None):
        super().__init__(elevation=2)
        self.initial_values = initial_values
        self.on_toggle_connection = on_toggle_connection
        self.lm = None
        
        self.is_connected = str(initial_values.get('db_connected', 'False')).lower() == 'true'
        
        # Elementos de UI
        self.title_text = ft.Text("Configurações de Banco de Dados", size=18, weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text("O PostgreSQL é recomendado para alta carga e Machine Learning distribuído.", italic=True, size=12, color=ft.Colors.GREY_500)
        
        self.db_type_dropdown = ft.Dropdown(
            label="Tipo de Banco de Dados",
            value=str(initial_values.get('db_type', 'sqlite')),
            options=[
                ft.dropdown.Option("sqlite", "SQLite (Local)"),
                ft.dropdown.Option("postgres", "PostgreSQL (Remoto/Avançado)")
            ],
            on_change=self._on_db_type_change,
            width=300,
            disabled=self.is_connected
        )

        # Campos PostgreSQL
        self.host_field = ft.TextField(label="Host", value=str(initial_values.get('db_host', 'localhost')), width=200, disabled=self.is_connected)
        self.port_field = ft.TextField(label="Porta", value=str(initial_values.get('db_port', '5432')), width=100, disabled=self.is_connected)
        self.user_field = ft.TextField(label="Usuário", value=str(initial_values.get('db_user', 'postgres')), width=200, disabled=self.is_connected)
        self.password_field = ft.TextField(label="Senha", value=str(initial_values.get('db_password', '')), password=True, can_reveal_password=True, width=200, disabled=self.is_connected)
        self.dbname_field = ft.TextField(label="Nome do Banco (DB Name)", value=str(initial_values.get('db_name', 'carina_data')), width=300, disabled=self.is_connected)

        self.postgres_container = ft.Column(
            controls=[
                ft.Row([self.host_field, self.port_field]),
                ft.Row([self.user_field, self.password_field]),
                self.dbname_field
            ],
            visible=(self.db_type_dropdown.value == "postgres")
        )

        # Action Buttons
        self.btn_connect = ft.ElevatedButton(
            text="Conectar / Testar", 
            icon=ft.Icons.LOGIN_ROUNDED, 
            on_click=self._on_connect_click,
            visible=not self.is_connected
        )
        self.btn_disconnect = ft.OutlinedButton(
            text="Desconectar", 
            icon=ft.Icons.LOGOUT_ROUNDED, 
            on_click=self._on_disconnect_click,
            visible=self.is_connected
        )

        # Status Display
        self.status_icon = ft.Icon(name=ft.Icons.CIRCLE, color=ft.Colors.GREY_500, size=16)
        self.status_text = ft.Text("NÃO TESTADO", color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500)
        self.progress_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        
        self.status_display = ft.Row([self.progress_ring, self.status_icon, self.status_text], alignment=ft.MainAxisAlignment.START, spacing=5)

        self.content = ft.Container(
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(ft.Icons.STORAGE), self.title_text]),
                    self.subtitle_text,
                    ft.Divider(height=10),
                    self.db_type_dropdown,
                    self.postgres_container,
                    ft.Divider(height=10),
                    ft.Row([
                        ft.Row([self.btn_connect, self.btn_disconnect], spacing=10),
                        self.status_display
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ]
            )
        )
        
        if self.is_connected:
            self._trigger_silent_auto_test()

    def _trigger_silent_auto_test(self):
        """Silently auto-tests the connection if initialized as connected."""
        self.status_icon.name = ft.Icons.CHECK_CIRCLE
        self.status_icon.color = ft.Colors.GREEN_500
        self.status_text.value = "CONECTADO"
        self.status_text.color = ft.Colors.GREEN_500
        
        db_type = self.db_type_dropdown.value
        host = self.host_field.value
        port = self.port_field.value
        user = self.user_field.value
        password = self.password_field.value
        dbname = self.dbname_field.value
        
        threading.Thread(target=self._test_connection_thread, args=(db_type, host, port, user, password, dbname, True), daemon=True).start()

    def _update_ui_lock_state(self):
        self.db_type_dropdown.disabled = self.is_connected
        self.host_field.disabled = self.is_connected
        self.port_field.disabled = self.is_connected
        self.user_field.disabled = self.is_connected
        self.password_field.disabled = self.is_connected
        self.dbname_field.disabled = self.is_connected
        
        self.btn_connect.visible = not self.is_connected
        self.btn_disconnect.visible = self.is_connected
        if self.page: self.update()

    def _on_db_type_change(self, e):
        self.postgres_container.visible = (self.db_type_dropdown.value == "postgres")
        self.status_icon.name = ft.Icons.CIRCLE
        self.status_icon.color = ft.Colors.GREY_500
        
        status_untested = "NÃO TESTADO"
        if self.lm:
            status_untested = self.lm.get_string("settings_view.db_card.status_untested", default=status_untested)
            
        self.status_text.value = status_untested
        self.status_text.color = ft.Colors.GREY_500
        if self.page: self.update()

    def _on_connect_click(self, e):
        self.btn_connect.disabled = True
        self.progress_ring.visible = True
        self.status_icon.visible = False
        
        status_testing = "TESTANDO..."
        if self.lm:
            status_testing = self.lm.get_string("settings_view.db_card.status_testing", default=status_testing)
            
        self.status_text.value = status_testing
        self.status_text.color = ft.Colors.AMBER_500
        if self.page: self.update()
        
        db_type = self.db_type_dropdown.value
        host = self.host_field.value
        port = self.port_field.value
        user = self.user_field.value
        password = self.password_field.value
        dbname = self.dbname_field.value
        
        threading.Thread(target=self._test_connection_thread, args=(db_type, host, port, user, password, dbname, False), daemon=True).start()

    def _on_disconnect_click(self, e):
        self.is_connected = False
        self._update_ui_lock_state()
        
        self.status_icon.name = ft.Icons.CIRCLE
        self.status_icon.color = ft.Colors.GREY_500
        status_untested = "NÃO TESTADO"
        if self.lm:
            status_untested = self.lm.get_string("settings_view.db_card.status_untested", default=status_untested)
        self.status_text.value = status_untested
        self.status_text.color = ft.Colors.GREY_500
        
        if self.on_toggle_connection:
            self.on_toggle_connection(False)
            
        if self.page: self.update()

    def _test_connection_thread(self, db_type, host, port, user, password, dbname, silent_auto):
        success = False
        error_msg = ""
        
        try:
            if db_type == "sqlite":
                db_dir = os.path.join(get_base_output_dir(), "results", "database")
                os.makedirs(db_dir, exist_ok=True)
                db_path = os.path.join(db_dir, dbname if dbname.endswith('.db') else f"{dbname}.db")
                
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
                success = True
            
            elif db_type == "postgres":
                import psycopg2
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    dbname=dbname,
                    connect_timeout=5
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1;")
                conn.close()
                success = True
                
        except Exception as e:
            success = False
            error_msg = str(e)
            
        if self.page:
            self._update_test_result(success, error_msg, silent_auto)

    def _update_test_result(self, success, error_msg, silent_auto):
        self.btn_connect.disabled = False
        self.progress_ring.visible = False
        self.status_icon.visible = True
        
        if success:
            self.is_connected = True
            self.status_icon.name = ft.Icons.CHECK_CIRCLE
            self.status_icon.color = ft.Colors.GREEN_500
            
            status_connected = "CONECTADO"
            if self.lm:
                status_connected = self.lm.get_string("settings_view.db_card.status_connected", default=status_connected)
                
            self.status_text.value = status_connected
            self.status_text.color = ft.Colors.GREEN_500
            self._update_ui_lock_state()
            
            if not silent_auto:
                success_msg = "Conexão ao banco de dados estabelecida com sucesso!"
                if self.lm:
                     success_msg = self.lm.get_string("settings_view.db_card.msg_success", default=success_msg)
                
                if self.page:
                    self.page.snack_bar = ft.SnackBar(content=ft.Text(success_msg, color=ft.colors.WHITE), bgcolor=ft.colors.GREEN_700)
                    self.page.snack_bar.open = True
                    
                if self.on_toggle_connection:
                    self.on_toggle_connection(True)
        else:
            self.is_connected = False
            self.status_icon.name = ft.Icons.ERROR
            self.status_icon.color = ft.Colors.RED_500
            
            status_error = "ERRO DE CONEXÃO"
            if self.lm:
                status_error = self.lm.get_string("settings_view.db_card.status_error", default=status_error)
                
            self.status_text.value = status_error
            self.status_text.color = ft.Colors.RED_500
            self._update_ui_lock_state()
            
            if self.page:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Erro: {error_msg}", color=ft.colors.WHITE), bgcolor=ft.colors.RED_700)
                self.page.snack_bar.open = True
                
        if self.page: self.update()

    def get_values(self) -> Dict[str, Any]:
        return {
            'db_type': self.db_type_dropdown.value,
            'db_host': self.host_field.value,
            'db_port': self.port_field.value,
            'db_user': self.user_field.value,
            'db_password': self.password_field.value,
            'db_name': self.dbname_field.value,
            'db_connected': str(self.is_connected)
        }

    def set_values(self, values: Dict[str, Any]):
        self.db_type_dropdown.value = str(values.get('db_type', 'sqlite'))
        self.host_field.value = str(values.get('db_host', 'localhost'))
        self.port_field.value = str(values.get('db_port', '5432'))
        self.user_field.value = str(values.get('db_user', 'postgres'))
        self.password_field.value = str(values.get('db_password', ''))
        self.dbname_field.value = str(values.get('db_name', 'carina_data'))
        
        is_conn = str(values.get('db_connected', 'False')).lower() == 'true'
        if is_conn != self.is_connected:
            self.is_connected = is_conn
            self._update_ui_lock_state()
            if self.is_connected:
                 self._trigger_silent_auto_test()
        
        self.postgres_container.visible = (self.db_type_dropdown.value == "postgres")
        if self.page: self.update()
        
    def update_translations(self, lm: LocaleManager):
        self.lm = lm
        self.title_text.value = lm.get_string("settings_view.db_card.title", default="Configurações de Banco de Dados")
        self.subtitle_text.value = lm.get_string("settings_view.db_card.subtitle", default="O PostgreSQL é recomendado para alta carga e Machine Learning distribuído.")
        self.db_type_dropdown.label = lm.get_string("settings_view.db_card.type_label", default="Tipo de Banco de Dados")
        
        self.host_field.label = lm.get_string("settings_view.db_card.host", default="Host")
        self.port_field.label = lm.get_string("settings_view.db_card.port", default="Porta")
        self.user_field.label = lm.get_string("settings_view.db_card.user", default="Usuário")
        self.password_field.label = lm.get_string("settings_view.db_card.password", default="Senha")
        self.dbname_field.label = lm.get_string("settings_view.db_card.dbname", default="Nome do Banco")
        
        self.btn_connect.text = lm.get_string("settings_view.db_card.btn_connect", default="Conectar")
        self.btn_disconnect.text = lm.get_string("settings_view.db_card.btn_disconnect", default="Desconectar")
        
        if self.status_icon.name == ft.Icons.CIRCLE:
            self.status_text.value = lm.get_string("settings_view.db_card.status_untested", default="NÃO TESTADO")
        elif self.status_icon.name == ft.Icons.CHECK_CIRCLE:
            self.status_text.value = lm.get_string("settings_view.db_card.status_connected", default="CONECTADO")
        elif self.status_icon.name == ft.Icons.ERROR:
            self.status_text.value = lm.get_string("settings_view.db_card.status_error", default="ERRO DE CONEXÃO")
            
        if self.page: self.update()
