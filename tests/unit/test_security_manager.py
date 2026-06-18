# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# File: tests/unit/test_security_manager.py
# Author: Gabriel Moraes

import os
import json
import sqlite3
import tempfile
import pytest
from src.utils.security_manager import SecurityManager

class MockEngine:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db_type = "sqlite"

    def get_connection(self):
        return sqlite3.connect(self.db_path)

class MockDatabaseManager:
    def __init__(self, db_path):
        self.engine = MockEngine(db_path)

@pytest.mark.unit
def test_security_manager_database_redundancy():
    # Create temp files for JSON and DB
    temp_dir = tempfile.TemporaryDirectory()
    try:
        db_path = os.path.join(temp_dir.name, "test_carina.db")
        
        # Initialize Mock DB Manager
        db_manager = MockDatabaseManager(db_path)
        
        # Instantiate SecurityManager with temp file override
        sm = SecurityManager(db_manager=db_manager)
        json_path = os.path.join(temp_dir.name, "security.json")
        sm.security_file = json_path
        
        # Force re-initialization with the temp JSON path
        sm._ensure_files()
        sm._sync_with_db()
        
        # 1. Verify default user is in JSON and DB
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "admin" in data["users"]
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM security_users WHERE username = 'admin'")
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "SUPERUSER"
        conn.close()
        
        # 2. Add a new user
        assert sm.add_user("operator_test", "password123", "OPERATOR")
        
        # Verify in JSON and DB
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "operator_test" in data["users"]
        assert data["users"]["operator_test"]["role"] == "OPERATOR"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM security_users WHERE username = 'operator_test'")
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "OPERATOR"
        conn.close()
        
        # 3. Simulate file deletion (the redundancy scenario!)
        os.remove(json_path)
        assert not os.path.exists(json_path)
        
        # Reload from DB (which should trigger automatic sync and restore the file from DB)
        loaded_data = sm._load_db()
        assert os.path.exists(json_path)
        assert "admin" in loaded_data["users"]
        assert "operator_test" in loaded_data["users"]
        assert loaded_data["users"]["operator_test"]["role"] == "OPERATOR"
        
        # 4. Remove a user
        assert sm.remove_user("operator_test")
        
        # Verify deleted from JSON and DB
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "operator_test" not in data["users"]
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM security_users WHERE username = 'operator_test'")
        row = cursor.fetchone()
        assert row is None
        conn.close()
    finally:
        temp_dir.cleanup()
