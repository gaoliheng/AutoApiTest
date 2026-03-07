from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
import json

from models.database import db


@dataclass
class TestCase:
    id: Optional[int] = None
    name: str = ""
    api_path: str = ""
    method: str = "GET"
    headers: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    body: Optional[dict] = None
    expected_status: int = 200
    assertions: list[dict] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: object) -> "TestCase":
        return cls(
            id=row["id"],
            name=row["name"],
            api_path=row["api_path"],
            method=row["method"],
            headers=json.loads(row["headers"]) if row["headers"] else {},
            params=json.loads(row["params"]) if row["params"] else {},
            body=json.loads(row["body"]) if row["body"] else None,
            expected_status=row["expected_status"],
            assertions=json.loads(row["assertions"]) if row["assertions"] else [],
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
            INSERT INTO test_cases (name, api_path, method, headers, params, body, expected_status, assertions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.name,
                self.api_path,
                self.method,
                json.dumps(self.headers) if self.headers else None,
                json.dumps(self.params) if self.params else None,
                json.dumps(self.body) if self.body else None,
                self.expected_status,
                json.dumps(self.assertions) if self.assertions else None,
            )
        )
        self.id = cursor.lastrowid
    
    def _update(self) -> None:
        db.execute(
            """
            UPDATE test_cases 
            SET name = ?, api_path = ?, method = ?, headers = ?, params = ?, body = ?, 
                expected_status = ?, assertions = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                self.name,
                self.api_path,
                self.method,
                json.dumps(self.headers) if self.headers else None,
                json.dumps(self.params) if self.params else None,
                json.dumps(self.body) if self.body else None,
                self.expected_status,
                json.dumps(self.assertions) if self.assertions else None,
                self.id,
            )
        )
    
    def delete(self) -> None:
        if self.id is not None:
            db.execute("DELETE FROM test_cases WHERE id = ?", (self.id,))
            self.id = None
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional["TestCase"]:
        row = db.fetchone("SELECT * FROM test_cases WHERE id = ?", (id,))
        return cls.from_row(row) if row else None
    
    @classmethod
    def get_all(cls) -> list["TestCase"]:
        rows = db.fetchall("SELECT * FROM test_cases ORDER BY created_at DESC")
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def get_by_ids(cls, ids: list[int]) -> list["TestCase"]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = db.fetchall(f"SELECT * FROM test_cases WHERE id IN ({placeholders}) ORDER BY created_at DESC", tuple(ids))
        return [cls.from_row(row) for row in rows]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "api_path": self.api_path,
            "method": self.method,
            "headers": self.headers,
            "params": self.params,
            "body": self.body,
            "expected_status": self.expected_status,
            "assertions": self.assertions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
