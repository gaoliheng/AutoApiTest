from pathlib import Path
from typing import Optional, Any
import yaml
import sys
import os


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
        from models.dimension_config import DimensionConfig
        DimensionConfig.initialize_defaults()
        configs = DimensionConfig.get_all()
        return [dim.to_dict() for dim in configs]

    @test_dimensions.setter
    def test_dimensions(self, value: list[dict[str, Any]]) -> None:
        from models.dimension_config import DimensionConfig
        DimensionConfig.initialize_defaults()
        for dim_data in value:
            existing = DimensionConfig.get_by_dimension_id(dim_data.get("dimension_id", ""))
            if existing:
                existing.name = dim_data.get("name", existing.name)
                existing.description = dim_data.get("description", existing.description)
                existing.enabled = dim_data.get("enabled", existing.enabled)
                existing.priority = dim_data.get("priority", existing.priority)
                existing.sort_order = dim_data.get("sort_order", existing.sort_order)
                existing.save()

    def get_enabled_dimensions(self) -> list[dict[str, Any]]:
        from models.dimension_config import DimensionConfig
        configs = DimensionConfig.get_enabled()
        return [dim.to_dict() for dim in configs]

    def reset_test_dimensions(self) -> None:
        from models.dimension_config import DimensionConfig
        DimensionConfig.reset_to_defaults()


config = Config()
