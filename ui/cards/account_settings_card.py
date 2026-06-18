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

# File: ui/widgets/account_settings_card.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import flet as ft
from typing import Callable, List, Dict

from ui.handlers.locale_manager import LocaleManager

class AccountSettingsCard(ft.Card):
    def __init__(self, locale_manager: LocaleManager, on_add_user: Callable[[str, str, str], None], on_remove_user: Callable[[str], None], on_request_list: Callable[[], None]):
        super().__init__(elevation=2)
        self.locale_manager = locale_manager
        self.on_add_user = on_add_user
        self.on_remove_user = on_remove_user
        self.on_request_list = on_request_list
        
        self.title_text = ft.Text(self.locale_manager.get_string("accounts.title", "Gerenciamento de Contas"), size=18, weight=ft.FontWeight.BOLD)
        
        self.username_field = ft.TextField(label=self.locale_manager.get_string("security.username", "Nome de Usuário"), expand=True)
        self.password_field = ft.TextField(label=self.locale_manager.get_string("security.password", "Senha"), password=True, can_reveal_password=True, expand=True)
        self.role_dropdown = ft.Dropdown(
            label=self.locale_manager.get_string("accounts.access_level", "Nível de Acesso"),
            options=[
                ft.dropdown.Option("OPERATOR", self.locale_manager.get_string("accounts.operator", "Operador (Acesso Padrão)")),
                ft.dropdown.Option("SUPERUSER", self.locale_manager.get_string("accounts.superuser", "Super Usuário (Acesso Total)")),
            ],
            value="OPERATOR",
            expand=True
        )
        
        self.add_btn = ft.ElevatedButton(self.locale_manager.get_string("accounts.add_user", "Adicionar Usuário"), icon=ft.Icons.PERSON_ADD, on_click=self._add_user)
        self.refresh_btn = ft.IconButton(icon=ft.Icons.REFRESH, tooltip=self.locale_manager.get_string("accounts.refresh_list", "Atualizar Lista"), on_click=lambda e: self.on_request_list())
        
        self.add_account_title = ft.Text(self.locale_manager.get_string("accounts.add_new_account", "Adicionar Nova Conta:"), weight=ft.FontWeight.BOLD)
        self.registered_accounts_title = ft.Text(self.locale_manager.get_string("accounts.registered_accounts", "Contas Cadastradas:"), weight=ft.FontWeight.BOLD)
        
        self.users_list_view = ft.ListView(expand=True, spacing=10, height=200)
        
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.MANAGE_ACCOUNTS, color=ft.Colors.BLUE_400), self.title_text]),
                ft.Divider(height=10),
                self.add_account_title,
                ft.Row([self.username_field, self.password_field]),
                ft.Row([self.role_dropdown, self.add_btn]),
                ft.Divider(height=20),
                ft.Row([self.registered_accounts_title, self.refresh_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    content=self.users_list_view,
                    border=ft.border.all(1, ft.Colors.WHITE24),
                    border_radius=5,
                    padding=10
                )
            ])
        )
        
    def update_translations(self, lm: LocaleManager):
        self.title_text.value = lm.get_string("accounts.title", "Gerenciamento de Contas")
        self.username_field.label = lm.get_string("security.username", "Nome de Usuário")
        self.password_field.label = lm.get_string("security.password", "Senha")
        self.role_dropdown.label = lm.get_string("accounts.access_level", "Nível de Acesso")
        if len(self.role_dropdown.options) >= 2:
            self.role_dropdown.options[0].text = lm.get_string("accounts.operator", "Operador (Acesso Padrão)")
            self.role_dropdown.options[1].text = lm.get_string("accounts.superuser", "Super Usuário (Acesso Total)")
        self.add_btn.text = lm.get_string("accounts.add_user", "Adicionar Usuário")
        self.refresh_btn.tooltip = lm.get_string("accounts.refresh_list", "Atualizar Lista")
        self.add_account_title.value = lm.get_string("accounts.add_new_account", "Adicionar Nova Conta:")
        self.registered_accounts_title.value = lm.get_string("accounts.registered_accounts", "Contas Cadastradas:")
        
        if self.page: self.update()

    def _add_user(self, e):
        uname = self.username_field.value.strip()
        pwd = self.password_field.value
        role = self.role_dropdown.value
        if uname and pwd and role:
            self.on_add_user(uname, pwd, role)
            self.username_field.value = ""
            self.password_field.value = ""
            if self.page: self.update()
            
    def update_user_list(self, users: List[Dict]):
        self.users_list_view.controls.clear()
        for u in users:
            uname = u.get("username", "")
            role = u.get("role", "")
            
            # Prevent removing the master from here if it leaks, but master is not in DB.
            icon_color = ft.Colors.AMBER if role == "SUPERUSER" else ft.Colors.BLUE_200
            
            row = ft.Row([
                ft.Icon(ft.Icons.PERSON, color=icon_color),
                ft.Text(f"{uname} ({role})", expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE_FOREVER, 
                    icon_color=ft.Colors.RED_400,
                    tooltip=f"{self.locale_manager.get_string('accounts.remove_user', 'Remover')} {uname}",
                    on_click=lambda e, u=uname: self.on_remove_user(u),
                    visible=uname != "admin"
                )
            ])
            self.users_list_view.controls.append(row)
            
        if self.page: self.update()
