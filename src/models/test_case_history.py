from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json

from models.database import db


@dataclass
class TestCaseHistory:
    """测试用例生成历史记录模型"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    test_cases: list = field(default_factory=list)
    base_url: str = ""
    api_path: str = ""
    common_headers: str = ""
    api_document: str = ""
    is_favorite: bool = False
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: object) -> "TestCaseHistory":
        """从数据库行创建实例"""
        test_cases = []
        if row["test_cases"]:
            try:
                test_cases = json.loads(row["test_cases"])
            except:
                test_cases = []
        
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            test_cases=test_cases,
            base_url=row["base_url"] or "",
            api_path=row["api_path"] or "",
            common_headers=row["common_headers"] or "",
            api_document=row["api_document"] or "",
            is_favorite=bool(row["is_favorite"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
    
    def save(self) -> None:
        """保存历史记录"""
        if self.id is None:
            self._insert()
        else:
            self._update()
    
    def _insert(self) -> None:
        """插入新记录"""
        # 检查普通记录数量限制（收藏记录不限制）
        if not self.is_favorite:
            self._enforce_limit()
        
        cursor = db.execute(
            """
            INSERT INTO test_case_history 
            (name, description, test_cases, base_url, api_path, common_headers, api_document, is_favorite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.name,
                self.description,
                json.dumps(self.test_cases, ensure_ascii=False),
                self.base_url,
                self.api_path,
                self.common_headers,
                self.api_document,
                int(self.is_favorite),
            )
        )
        self.id = cursor.lastrowid
    
    def _update(self) -> None:
        """更新记录"""
        db.execute(
            """
            UPDATE test_case_history 
            SET name = ?, description = ?, test_cases = ?, base_url = ?, api_path = ?, 
                common_headers = ?, api_document = ?, is_favorite = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                self.name,
                self.description,
                json.dumps(self.test_cases, ensure_ascii=False),
                self.base_url,
                self.api_path,
                self.common_headers,
                self.api_document,
                int(self.is_favorite),
                self.id,
            )
        )
    
    def _enforce_limit(self) -> None:
        """强制执行50条普通记录限制"""
        # 获取普通记录数量
        result = db.fetchone(
            "SELECT COUNT(*) as count FROM test_case_history WHERE is_favorite = 0"
        )
        count = result["count"] if result else 0
        
        # 如果达到或超过50条，删除最旧的记录
        if count >= 50:
            # 删除最旧的普通记录，保留最新的49条
            db.execute(
                """
                DELETE FROM test_case_history 
                WHERE id IN (
                    SELECT id FROM test_case_history 
                    WHERE is_favorite = 0 
                    ORDER BY created_at ASC 
                    LIMIT ?
                )
                """,
                (count - 49,)
            )
    
    def delete(self) -> None:
        """删除记录"""
        if self.id is not None:
            db.execute("DELETE FROM test_case_history WHERE id = ?", (self.id,))
            self.id = None
    
    def toggle_favorite(self) -> None:
        """切换收藏状态"""
        self.is_favorite = not self.is_favorite
        self.save()
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional["TestCaseHistory"]:
        """根据ID获取历史记录"""
        row = db.fetchone("SELECT * FROM test_case_history WHERE id = ?", (id,))
        return cls.from_row(row) if row else None
    
    @classmethod
    def get_all(cls, favorite_only: bool = False) -> list["TestCaseHistory"]:
        """获取所有历史记录
        
        Args:
            favorite_only: 是否只获取收藏的记录
        """
        if favorite_only:
            rows = db.fetchall(
                "SELECT * FROM test_case_history WHERE is_favorite = 1 ORDER BY created_at DESC"
            )
        else:
            rows = db.fetchall(
                "SELECT * FROM test_case_history ORDER BY is_favorite DESC, created_at DESC"
            )
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def get_normal_count(cls) -> int:
        """获取普通记录数量"""
        result = db.fetchone(
            "SELECT COUNT(*) as count FROM test_case_history WHERE is_favorite = 0"
        )
        return result["count"] if result else 0
    
    @classmethod
    def get_favorite_count(cls) -> int:
        """获取收藏记录数量"""
        result = db.fetchone(
            "SELECT COUNT(*) as count FROM test_case_history WHERE is_favorite = 1"
        )
        return result["count"] if result else 0
    
    def to_dict(self) -> dict:
        """转换为字典（用于导出）"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "test_cases": self.test_cases,
            "base_url": self.base_url,
            "api_path": self.api_path,
            "common_headers": self.common_headers,
            "api_document": self.api_document,
            "is_favorite": self.is_favorite,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TestCaseHistory":
        """从字典创建实例（用于导入）"""
        return cls(
            id=None,  # 导入时重置ID
            name=data.get("name", ""),
            description=data.get("description", ""),
            test_cases=data.get("test_cases", []),
            base_url=data.get("base_url", ""),
            api_path=data.get("api_path", ""),
            common_headers=data.get("common_headers", ""),
            api_document=data.get("api_document", ""),
            is_favorite=data.get("is_favorite", False),
            created_at=None,  # 导入时使用新的时间
        )
