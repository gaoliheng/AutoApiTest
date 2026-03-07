from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json

from models.database import db


@dataclass
class TestScript:
    id: Optional[int] = None
    name: str = ""
    content: str = ""
    test_case_ids: list[int] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: object) -> "TestScript":
        return cls(
            id=row["id"],
            name=row["name"],
            content=row["content"],
            test_case_ids=json.loads(row["test_case_ids"]) if row["test_case_ids"] else [],
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
            INSERT INTO test_scripts (name, content, test_case_ids)
            VALUES (?, ?, ?)
            """,
            (self.name, self.content, json.dumps(self.test_case_ids))
        )
        self.id = cursor.lastrowid
    
    def _update(self) -> None:
        db.execute(
            """
            UPDATE test_scripts 
            SET name = ?, content = ?, test_case_ids = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (self.name, self.content, json.dumps(self.test_case_ids), self.id)
        )
    
    def delete(self) -> None:
        if self.id is not None:
            db.execute("DELETE FROM test_scripts WHERE id = ?", (self.id,))
            self.id = None
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional["TestScript"]:
        row = db.fetchone("SELECT * FROM test_scripts WHERE id = ?", (id,))
        return cls.from_row(row) if row else None
    
    @classmethod
    def get_all(cls) -> list["TestScript"]:
        rows = db.fetchall("SELECT * FROM test_scripts ORDER BY created_at DESC")
        return [cls.from_row(row) for row in rows]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "test_case_ids": self.test_case_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
