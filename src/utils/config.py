import json
from pathlib import Path
from typing import Optional, Any
import yaml
import sys
import os


DEFAULT_TEST_DIMENSIONS = [
    {
        "id": "happy_path",
        "name": "正常场景测试",
        "description": "测试接口在正常输入和正确参数情况下的行为",
        "enabled": True,
        "priority": "high"
    },
    {
        "id": "boundary",
        "name": "边界值测试",
        "description": "测试参数在边界值情况下的行为（最大值、最小值、空值等）",
        "enabled": True,
        "priority": "medium"
    },
    {
        "id": "error_case",
        "name": "异常场景测试",
        "description": "测试参数缺失、类型错误、权限问题等异常情况",
        "enabled": True,
        "priority": "high"
    },
    {
        "id": "performance",
        "name": "性能相关测试",
        "description": "测试大数据量或高并发场景",
        "enabled": False,
        "priority": "low"
    },
]


class Config:
    _instance: Optional["Config"] = None
    
    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._initialized = True
        
        if getattr(sys, 'frozen', False):
            self._base_path: Path = Path(sys.executable).parent
        else:
            self._base_path: Path = Path(__file__).parent.parent.parent
        
        self._data_path: Path = self._base_path / "data"
        self._exports_path: Path = self._base_path / "exports"
        self._config_path: Path = self._data_path / "config.yaml"
        self._db_path: Path = self._data_path / "autotest.db"
        
        self._ensure_directories()
        self._settings: dict = self._load_config()
    
    def _ensure_directories(self) -> None:
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._exports_path.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> dict:
        if self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def save_config(self) -> None:
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self._settings, f, allow_unicode=True, default_flow_style=False)
    
    @property
    def base_path(self) -> Path:
        return self._base_path
    
    @property
    def data_path(self) -> Path:
        return self._data_path
    
    @property
    def exports_path(self) -> Path:
        return self._exports_path
    
    @property
    def db_path(self) -> Path:
        return Path(self._settings.get("db_path", str(self._db_path)))
    
    @db_path.setter
    def db_path(self, value: Path) -> None:
        self._settings["db_path"] = str(value)
        self.save_config()
    
    @property
    def default_ai_model_id(self) -> Optional[int]:
        return self._settings.get("default_ai_model_id")
    
    @default_ai_model_id.setter
    def default_ai_model_id(self, value: int) -> None:
        self._settings["default_ai_model_id"] = value
        self.save_config()
    
    def get(self, key: str, default: Optional[object] = None) -> Optional[object]:
        return self._settings.get(key, default)
    
    def set(self, key: str, value: object) -> None:
        self._settings[key] = value
        self.save_config()

    @property
    def test_dimensions(self) -> list[dict[str, Any]]:
        return self._settings.get("test_dimensions", DEFAULT_TEST_DIMENSIONS.copy())

    @test_dimensions.setter
    def test_dimensions(self, value: list[dict[str, Any]]) -> None:
        self._settings["test_dimensions"] = value
        self.save_config()

    def get_enabled_dimensions(self) -> list[dict[str, Any]]:
        return [d for d in self.test_dimensions if d.get("enabled", False)]

    def reset_test_dimensions(self) -> None:
        self._settings["test_dimensions"] = DEFAULT_TEST_DIMENSIONS.copy()
        self.save_config()


config = Config()
