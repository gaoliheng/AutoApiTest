from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json

from models.database import db


@dataclass
class AuthConfig:
    id: Optional[int] = None
    name: str = ""
    base_url: str = ""
    login_path: str = ""
    method: str = "POST"
    headers: dict = None
    body: dict = None
    token_path: str = "$.data.access_token"
    token_prefix: str = ""
    header_name: str = "Authorization"
    is_enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.body is None:
            self.body = {}
    
    @classmethod
    def from_row(cls, row: object) -> "AuthConfig":
        headers = {}
        if row["headers"]:
            try:
                headers = json.loads(row["headers"])
            except:
                headers = {}
        
        body = {}
        if row["body"]:
            try:
                body = json.loads(row["body"])
            except:
                body = {}
        
        return cls(
            id=row["id"],
            name=row["name"],
            base_url=row["base_url"],
            login_path=row["login_path"],
            method=row["method"],
            headers=headers,
            body=body,
            token_path=row["token_path"],
            token_prefix=row["token_prefix"] if row["token_prefix"] is not None else "Bearer",
            header_name=row["header_name"] or "Authorization",
            is_enabled=bool(row["is_enabled"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )
    
    def save(self) -> None:
        if self.id is None:
            self._insert()
        else:
            self._update()
    
    def _insert(self) -> None:
        cursor = db.execute(
            """
            INSERT INTO auth_config (name, base_url, login_path, method, headers, body, token_path, token_prefix, header_name, is_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.name,
                self.base_url,
                self.login_path,
                self.method,
                json.dumps(self.headers, ensure_ascii=False) if self.headers else None,
                json.dumps(self.body, ensure_ascii=False) if self.body else None,
                self.token_path,
                self.token_prefix,
                self.header_name,
                int(self.is_enabled)
            )
        )
        self.id = cursor.lastrowid
    
    def _update(self) -> None:
        db.execute(
            """
            UPDATE auth_config 
            SET name = ?, base_url = ?, login_path = ?, method = ?, headers = ?, body = ?, 
                token_path = ?, token_prefix = ?, header_name = ?, is_enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                self.name,
                self.base_url,
                self.login_path,
                self.method,
                json.dumps(self.headers, ensure_ascii=False) if self.headers else None,
                json.dumps(self.body, ensure_ascii=False) if self.body else None,
                self.token_path,
                self.token_prefix,
                self.header_name,
                int(self.is_enabled),
                self.id
            )
        )
    
    def delete(self) -> None:
        if self.id is not None:
            db.execute("DELETE FROM auth_config WHERE id = ?", (self.id,))
            self.id = None
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional["AuthConfig"]:
        row = db.fetchone("SELECT * FROM auth_config WHERE id = ?", (id,))
        return cls.from_row(row) if row else None
    
    @classmethod
    def get_all(cls) -> list["AuthConfig"]:
        rows = db.fetchall("SELECT * FROM auth_config ORDER BY created_at DESC")
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def get_enabled(cls) -> list["AuthConfig"]:
        rows = db.fetchall("SELECT * FROM auth_config WHERE is_enabled = 1 ORDER BY created_at DESC")
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def get_first_enabled(cls) -> Optional["AuthConfig"]:
        row = db.fetchone("SELECT * FROM auth_config WHERE is_enabled = 1 LIMIT 1")
        return cls.from_row(row) if row else None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "login_path": self.login_path,
            "method": self.method,
            "headers": self.headers,
            "body": self.body,
            "token_path": self.token_path,
            "token_prefix": self.token_prefix,
            "header_name": self.header_name,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
