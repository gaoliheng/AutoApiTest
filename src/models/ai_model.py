from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json

from models.database import db


@dataclass
class AIModel:
    id: Optional[int] = None
    name: str = ""
    api_base: str = ""
    api_key: str = ""
    model_name: str = ""
    is_default: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: object) -> "AIModel":
        return cls(
            id=row["id"],
            name=row["name"],
            api_base=row["api_base"],
            api_key=row["api_key"],
            model_name=row["model_name"],
            is_default=bool(row["is_default"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )
    
    def save(self) -> None:
        if self.id is None:
            self._insert()
        else:
            self._update()
    
    def _insert(self) -> None:
        if self.is_default:
            db.execute("UPDATE ai_models SET is_default = 0")
        
        cursor = db.execute(
            """
            INSERT INTO ai_models (name, api_base, api_key, model_name, is_default)
            VALUES (?, ?, ?, ?, ?)
            """,
            (self.name, self.api_base, self.api_key, self.model_name, int(self.is_default))
        )
        self.id = cursor.lastrowid
    
    def _update(self) -> None:
        if self.is_default:
            db.execute("UPDATE ai_models SET is_default = 0")
        
        db.execute(
            """
            UPDATE ai_models 
            SET name = ?, api_base = ?, api_key = ?, model_name = ?, is_default = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (self.name, self.api_base, self.api_key, self.model_name, int(self.is_default), self.id)
        )
    
    def delete(self) -> None:
        if self.id is not None:
            db.execute("DELETE FROM ai_models WHERE id = ?", (self.id,))
            self.id = None
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional["AIModel"]:
        row = db.fetchone("SELECT * FROM ai_models WHERE id = ?", (id,))
        return cls.from_row(row) if row else None
    
    @classmethod
    def get_all(cls) -> list["AIModel"]:
        rows = db.fetchall("SELECT * FROM ai_models ORDER BY created_at DESC")
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def get_default(cls) -> Optional["AIModel"]:
        row = db.fetchone("SELECT * FROM ai_models WHERE is_default = 1 LIMIT 1")
        return cls.from_row(row) if row else None
    
    def set_as_default(self) -> None:
        db.execute("UPDATE ai_models SET is_default = 0")
        db.execute("UPDATE ai_models SET is_default = 1 WHERE id = ?", (self.id,))
        self.is_default = True
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "api_base": self.api_base,
            "api_key": self.api_key,
            "model_name": self.model_name,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
