# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security_manager.py
# Author: Gabriel Moraes
# Date: June 09, 2026

import os
import json
import logging
import hashlib
import binascii
import shutil

from utils.paths import get_base_output_dir, get_user_config_dir

class SecurityManager:
    """
    Manages user accounts, authentication, and the Lockdown failsafe logic.
    Roles available: OPERATOR, SUPERUSER, MASTER.
    """
    def __init__(self, locale_manager=None):
        self.locale_manager = locale_manager
        self.max_failed_attempts = 3
        
        user_config_dir = get_user_config_dir()
        self.security_file = os.path.join(user_config_dir, "security.json")
        self.lockdown_file = os.path.join(user_config_dir, "lockdown.flag")
        
        # Migration from old path (get_base_output_dir() / "results" / "security.json")
        old_security_file = os.path.join(get_base_output_dir(), "results", "security.json")
        if not os.path.exists(self.security_file) and os.path.exists(old_security_file):
            try:
                shutil.copy2(old_security_file, self.security_file)
                logging.info(self._get_string("security_manager.migrated_security", default="[SecurityManager] Migrated security.json from {old} to {new}", old=old_security_file, new=self.security_file))
            except Exception as e:
                logging.error(self._get_string("security_manager.migrate_security_fail", default="[SecurityManager] Failed to migrate security.json: {error}", error=e))
                
        old_lockdown_file = os.path.join(get_base_output_dir(), "results", "lockdown.flag")
        if not os.path.exists(self.lockdown_file) and os.path.exists(old_lockdown_file):
            try:
                shutil.copy2(old_lockdown_file, self.lockdown_file)
                logging.info(self._get_string("security_manager.migrated_lockdown", default="[SecurityManager] Migrated lockdown.flag from {old} to {new}", old=old_lockdown_file, new=self.lockdown_file))
            except Exception as e:
                logging.error(self._get_string("security_manager.migrate_lockdown_fail", default="[SecurityManager] Failed to migrate lockdown.flag: {error}", error=e))
        
        # Hardcoded Master Super User Hash (fallback god mode)
        self.master_user = "superuser_noxfort"
        self.master_hash = "a56cc725d6b9df386120c36f77678be3302935c97f8ec1d78ba59b74ad221e62" # SHA256 of the master password

        self._ensure_files()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)
        
    def _ensure_files(self):
        os.makedirs(os.path.dirname(self.security_file), exist_ok=True)
        if not os.path.exists(self.security_file):
            # Create default admin user if no file exists
            default_db = {
                "users": {
                    "admin": {
                        "hash": self._hash_password("admin"),
                        "role": "SUPERUSER"
                    }
                },
                "failed_attempts": 0
            }
            self._save_db(default_db)
            logging.info(self._get_string("security_manager.default_user_created", default="[SecurityManager] Security file created with default user 'admin' (password: 'admin')."))

    def _load_db(self):
        try:
            with open(self.security_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(self._get_string("security_manager.read_db_error", default="[SecurityManager] Error reading security database: {error}", error=e))
            return {"users": {}, "failed_attempts": 0}

    def _save_db(self, db):
        try:
            with open(self.security_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=4)
        except Exception as e:
            logging.error(self._get_string("security_manager.save_db_error", default="[SecurityManager] Error saving security database: {error}", error=e))

    def _hash_password(self, password: str, salt: bytes = None) -> str:
        """Hashes a password using PBKDF2 HMAC SHA256."""
        if salt is None:
            salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return f"{binascii.hexlify(salt).decode('utf-8')}:{binascii.hexlify(pwd_hash).decode('utf-8')}"

    def _verify_password(self, password: str, stored_hash_str: str) -> bool:
        """Verifies a password against a stored PBKDF2 hash string."""
        try:
            salt_hex, hash_hex = stored_hash_str.split(':')
            salt = binascii.unhexlify(salt_hex)
            stored_hash = binascii.unhexlify(hash_hex)
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return new_hash == stored_hash
        except Exception:
            return False

    def is_lockdown(self) -> bool:
        return os.path.exists(self.lockdown_file)

    def trigger_lockdown(self):
        """Creates the persistent lockdown flag."""
        try:
            with open(self.lockdown_file, "w", encoding="utf-8") as f:
                f.write("LOCKDOWN_ACTIVE")
            logging.critical(self._get_string("security_manager.lockdown_triggered", default="[SecurityManager] 🚨 SYSTEM ENTERED LOCKDOWN (Too many failed attempts)."))
        except Exception as e:
            logging.error(self._get_string("security_manager.lockdown_flag_error", default="[SecurityManager] Failed to create lockdown flag: {error}", error=e))

    def clear_lockdown(self):
        """Removes the persistent lockdown flag and resets failed attempts."""
        if os.path.exists(self.lockdown_file):
            try:
                os.remove(self.lockdown_file)
            except Exception as e:
                logging.error(self._get_string("security_manager.lockdown_remove_error", default="[SecurityManager] Failed to remove lockdown flag: {error}", error=e))
                
        db = self._load_db()
        db["failed_attempts"] = 0
        self._save_db(db)
        logging.info(self._get_string("security_manager.lockdown_cleared", default="[SecurityManager] Lockdown removed and failed attempts counter reset."))

    def authenticate(self, username: str, password: str) -> tuple[bool, str]:
        """
        Attempts to authenticate a user.
        Returns: (success_bool, role_string_or_error_msg)
        """
        invalid_msg = self._get_string("security_manager.invalid_credentials", default="Invalid credentials")
        system_locked_msg = self._get_string("security_manager.system_locked", default="SYSTEM LOCKED. Only SuperUsers can unlock.")
        
        # Master Fallback Check
        if username == self.master_user:
            # Simple SHA256 for the hardcoded master
            raw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if raw_hash == self.master_hash:
                if self.is_lockdown():
                    self.clear_lockdown()
                return True, "MASTER"
            else:
                self.record_failed_attempt()
                return False, invalid_msg

        db = self._load_db()
        
        # If in lockdown, ONLY SUPERUSER or MASTER can log in to unlock
        if self.is_lockdown():
            if username in db["users"]:
                user_data = db["users"][username]
                if user_data["role"] == "SUPERUSER":
                    if self._verify_password(password, user_data["hash"]):
                        self.clear_lockdown()
                        return True, "SUPERUSER"
            
            # Record fail even during lockdown to avoid brute force on SuperUsers
            # (Though it's already locked down, it's good practice)
            return False, system_locked_msg

        # Normal authentication
        if username not in db["users"]:
            self.record_failed_attempt()
            return False, invalid_msg

        user_data = db["users"][username]
        if self._verify_password(password, user_data["hash"]):
            # Success, reset attempts
            if db["failed_attempts"] > 0:
                db["failed_attempts"] = 0
                self._save_db(db)
            return True, user_data["role"]
        else:
            self.record_failed_attempt()
            return False, invalid_msg

    def record_failed_attempt(self) -> bool:
        """
        Increments the failed attempt counter. Triggers lockdown if >= 3.
        Returns True if lockdown was triggered during this call.
        """
        if self.is_lockdown():
            return True
            
        db = self._load_db()
        db["failed_attempts"] += 1
        
        logging.warning(self._get_string("security_manager.failed_attempt_registered", default="[SecurityManager] Failed login attempt recorded. Total: {current}/{max}", current=db['failed_attempts'], max=self.max_failed_attempts))
        
        if db["failed_attempts"] >= self.max_failed_attempts:
            self.trigger_lockdown()
            self._save_db(db)
            return True
            
        self._save_db(db)
        return False

    def add_user(self, username: str, password: str, role: str) -> bool:
        if role not in ["OPERATOR", "SUPERUSER"]:
            return False
        db = self._load_db()
        if username in db["users"]:
            return False # User already exists
            
        db["users"][username] = {
            "hash": self._hash_password(password),
            "role": role
        }
        self._save_db(db)
        logging.info(self._get_string("security_manager.user_added", default="[SecurityManager] New user registered: {username} ({role})", username=username, role=role))
        return True

    def remove_user(self, username: str) -> bool:
        if username == "admin":
            logging.warning(self._get_string("security_manager.admin_remove_blocked", default="[SecurityManager] Blocked attempt to remove 'admin' user."))
            return False
            
        db = self._load_db()
        if username in db["users"]:
            del db["users"][username]
            self._save_db(db)
            logging.info(self._get_string("security_manager.user_removed", default="[SecurityManager] User removed: {username}", username=username))
            return True
        return False
        
    def list_users(self) -> list:
        db = self._load_db()
        users = []
        for uname, data in db["users"].items():
            users.append({"username": uname, "role": data["role"]})
        return users
