"""
AI 模型配置管理服务
提供 AI 模型配置的增删改查、设置默认模型、测试连接等功能
"""

from dataclasses import dataclass
from typing import Optional

from ai.client import AIClient, AIModelConfig, ConnectionTestResult
from models.ai_model import AIModel


@dataclass
class AIModelCreateRequest:
    name: str
    api_base: str
    api_key: str
    model_name: str
    is_default: bool = False


@dataclass
class AIModelUpdateRequest:
    id: int
    name: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    is_default: Optional[bool] = None


class AIModelService:
    @staticmethod
    def create_model(request: AIModelCreateRequest) -> AIModel:
        model = AIModel(
            name=request.name,
            api_base=request.api_base,
            api_key=request.api_key,
            model_name=request.model_name,
            is_default=request.is_default,
        )
        model.save()
        return model

    @staticmethod
    def update_model(request: AIModelUpdateRequest) -> Optional[AIModel]:
        model = AIModel.get_by_id(request.id)
        if model is None:
            return None

        if request.name is not None:
            model.name = request.name
        if request.api_base is not None:
            model.api_base = request.api_base
        if request.api_key is not None:
            model.api_key = request.api_key
        if request.model_name is not None:
            model.model_name = request.model_name
        if request.is_default is not None:
            model.is_default = request.is_default

        model.save()
        return model

    @staticmethod
    def delete_model(model_id: int) -> bool:
        model = AIModel.get_by_id(model_id)
        if model is None:
            return False
        model.delete()
        return True

    @staticmethod
    def get_model_by_id(model_id: int) -> Optional[AIModel]:
        return AIModel.get_by_id(model_id)

    @staticmethod
    def get_all_models() -> list[AIModel]:
        return AIModel.get_all()

    @staticmethod
    def get_default_model() -> Optional[AIModel]:
        return AIModel.get_default()

    @staticmethod
    def set_default_model(model_id: int) -> bool:
        model = AIModel.get_by_id(model_id)
        if model is None:
            return False
        model.set_as_default()
        return True

    @staticmethod
    def test_model_connection(model_id: int) -> ConnectionTestResult:
        model = AIModel.get_by_id(model_id)
        if model is None:
            return ConnectionTestResult(
                success=False,
                message=f"未找到 ID 为 {model_id} 的模型配置",
            )

        config = AIModelConfig(
            name=model.name,
            api_base_url=model.api_base,
            api_key=model.api_key,
            model_name=model.model_name,
        )

        with AIClient(config) as client:
            return client.test_connection()

    @staticmethod
    def test_model_connection_by_config(
        api_base: str,
        api_key: str,
        model_name: str,
    ) -> ConnectionTestResult:
        config = AIModelConfig(
            name="test",
            api_base_url=api_base,
            api_key=api_key,
            model_name=model_name,
        )

        with AIClient(config) as client:
            return client.test_connection()

    @staticmethod
    def get_model_as_client(model_id: int) -> Optional[AIClient]:
        model = AIModel.get_by_id(model_id)
        if model is None:
            return None

        config = AIModelConfig(
            name=model.name,
            api_base_url=model.api_base,
            api_key=model.api_key,
            model_name=model.model_name,
        )
        return AIClient(config)

    @staticmethod
    def get_default_model_as_client() -> Optional[AIClient]:
        model = AIModel.get_default()
        if model is None:
            return None

        config = AIModelConfig(
            name=model.name,
            api_base_url=model.api_base,
            api_key=model.api_key,
            model_name=model.model_name,
        )
        return AIClient(config)
