from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models.database import db


DEFAULT_TEST_DIMENSIONS = [
    {
        "dimension_id": "happy_path",
        "name": "正常场景测试",
        "description": "测试接口在正常输入和正确参数情况下的行为",
        "enabled": True,
        "priority": "high",
        "is_system": True,
        "sort_order": 1,
    },
    {
        "dimension_id": "boundary",
        "name": "边界值测试",
        "description": "测试参数在边界值情况下的行为（最大值、最小值、空值等）",
        "enabled": True,
        "priority": "medium",
        "is_system": True,
        "sort_order": 2,
    },
    {
        "dimension_id": "error_case",
        "name": "异常场景测试",
        "description": "测试参数缺失、类型错误、权限问题等异常情况",
        "enabled": True,
        "priority": "high",
        "is_system": True,
        "sort_order": 3,
    },
    {
        "dimension_id": "performance",
        "name": "性能相关测试",
        "description": "测试大数据量或高并发场景",
        "enabled": False,
        "priority": "low",
        "is_system": True,
        "sort_order": 4,
    },
]


@dataclass
class DimensionConfig:
    """测试维度配置模型"""
    id: Optional[int] = None
    dimension_id: str = ""
    name: str = ""
    description: str = ""
    enabled: bool = True
    priority: str = "medium"
    is_system: bool = False
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: object) -> "DimensionConfig":
        """从数据库行创建实例"""
        return cls(
            id=row["id"],
            dimension_id=row["dimension_id"],
            name=row["name"],
            description=row["description"] or "",
            enabled=bool(row["enabled"]),
            priority=row["priority"] or "medium",
            is_system=bool(row["is_system"]),
            sort_order=row["sort_order"] or 0,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )

    def save(self) -> None:
        """保存维度配置"""
        if self.id is None:
            self._insert()
        else:
            self._update()

    def _insert(self) -> None:
        """插入新记录"""
        cursor = db.execute(
            """
            INSERT INTO test_dimensions
            (dimension_id, name, description, enabled, priority, is_system, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.dimension_id,
                self.name,
                self.description,
                int(self.enabled),
                self.priority,
                int(self.is_system),
                self.sort_order,
            )
        )
        self.id = cursor.lastrowid

    def _update(self) -> None:
        """更新记录"""
        db.execute(
            """
            UPDATE test_dimensions
            SET name = ?, description = ?, enabled = ?, priority = ?, sort_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                self.name,
                self.description,
                int(self.enabled),
                self.priority,
                self.sort_order,
                self.id,
            )
        )

    def delete(self) -> None:
        """删除记录（系统维度不能删除）"""
        if self.id is not None and not self.is_system:
            db.execute("DELETE FROM test_dimensions WHERE id = ?", (self.id,))
            self.id = None

    @classmethod
    def get_by_id(cls, id: int) -> Optional["DimensionConfig"]:
        """根据ID获取维度配置"""
        row = db.fetchone("SELECT * FROM test_dimensions WHERE id = ?", (id,))
        return cls.from_row(row) if row else None

    @classmethod
    def get_by_dimension_id(cls, dimension_id: str) -> Optional["DimensionConfig"]:
        """根据dimension_id获取维度配置"""
        row = db.fetchone("SELECT * FROM test_dimensions WHERE dimension_id = ?", (dimension_id,))
        return cls.from_row(row) if row else None

    @classmethod
    def get_all(cls) -> list["DimensionConfig"]:
        """获取所有维度配置，按sort_order排序"""
        if cls.is_empty():
            cls.initialize_defaults()
        rows = db.fetchall("SELECT * FROM test_dimensions ORDER BY sort_order ASC")
        return [cls.from_row(row) for row in rows]

    @classmethod
    def get_enabled(cls) -> list["DimensionConfig"]:
        """获取已启用的维度配置"""
        if cls.is_empty():
            cls.initialize_defaults()
        rows = db.fetchall(
            "SELECT * FROM test_dimensions WHERE enabled = 1 ORDER BY sort_order ASC"
        )
        return [cls.from_row(row) for row in rows]

    @classmethod
    def get_count(cls) -> int:
        """获取维度配置数量"""
        result = db.fetchone("SELECT COUNT(*) as count FROM test_dimensions")
        return result["count"] if result else 0

    @classmethod
    def is_empty(cls) -> bool:
        """检查是否为空（未初始化）"""
        return cls.get_count() == 0

    @classmethod
    def initialize_defaults(cls) -> None:
        """初始化默认维度配置"""
        for dim in DEFAULT_TEST_DIMENSIONS:
            existing = cls.get_by_dimension_id(dim["dimension_id"])
            if not existing:
                config = cls(
                    dimension_id=dim["dimension_id"],
                    name=dim["name"],
                    description=dim["description"],
                    enabled=dim["enabled"],
                    priority=dim["priority"],
                    is_system=dim["is_system"],
                    sort_order=dim["sort_order"],
                )
                config.save()

    @classmethod
    def reset_to_defaults(cls) -> None:
        """重置为默认配置"""
        db.execute("DELETE FROM test_dimensions WHERE is_system = 1")
        for dim in DEFAULT_TEST_DIMENSIONS:
            existing = cls.get_by_dimension_id(dim["dimension_id"])
            if not existing:
                config = cls(
                    dimension_id=dim["dimension_id"],
                    name=dim["name"],
                    description=dim["description"],
                    enabled=dim["enabled"],
                    priority=dim["priority"],
                    is_system=dim["is_system"],
                    sort_order=dim["sort_order"],
                )
                config.save()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "dimension_id": self.dimension_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "is_system": self.is_system,
            "sort_order": self.sort_order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DimensionConfig":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            dimension_id=data.get("dimension_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", "medium"),
            is_system=data.get("is_system", False),
            sort_order=data.get("sort_order", 0),
        )
