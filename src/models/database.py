import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from utils.config import config


class Database:
    _instance: Optional["Database"] = None
    
    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._initialized = True
        self._db_path: Path = config.db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._initialize_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(str(self._db_path))
            self._connection.row_factory = sqlite3.Row
            self._enable_foreign_keys()
        return self._connection
    
    def _enable_foreign_keys(self) -> None:
        cursor = self._connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
    
    @contextmanager
    def get_cursor(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _initialize_db(self) -> None:
        with self.get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    api_base TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    is_default INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    api_path TEXT NOT NULL,
                    method TEXT NOT NULL,
                    headers TEXT,
                    params TEXT,
                    body TEXT,
                    expected_status INTEGER DEFAULT 200,
                    assertions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    test_case_ids TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_models_is_default 
                ON ai_models(is_default)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_cases_name 
                ON test_cases(name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_scripts_name 
                ON test_scripts(name)
            """)
    
    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def fetchall(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


db = Database()
