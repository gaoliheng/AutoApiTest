"""
测试用例服务
提供测试用例的生成、查询、编辑、删除等功能
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

from ai.client import AIClient, ChatMessage, MessageRole
from ai.prompts import DocumentFormat, TestCasePrompt
from models.test_case import TestCase


@dataclass
class TestCaseGenerateRequest:
    api_document: str
    document_format: DocumentFormat = DocumentFormat.JSON
    additional_requirements: Optional[str] = None
    model_id: Optional[int] = None


@dataclass
class TestCaseCreateRequest:
    name: str
    api_path: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    body: Optional[dict[str, Any]] = None
    expected_status: int = 200
    assertions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TestCaseUpdateRequest:
    id: int
    name: Optional[str] = None
    api_path: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    params: Optional[dict[str, Any]] = None
    body: Optional[dict[str, Any]] = None
    expected_status: Optional[int] = None
    assertions: Optional[list[dict[str, Any]]] = None


@dataclass
class TestCaseBatchUpdateRequest:
    ids: list[int]
    updates: dict[str, Any]


@dataclass
class GenerateResult:
    success: bool
    message: str
    test_cases: list[TestCase] = field(default_factory=list)


class TestCaseService:
    @staticmethod
    def generate_test_cases(
        request: TestCaseGenerateRequest,
        ai_client: Optional[AIClient] = None,
    ) -> GenerateResult:
        client = ai_client
        should_close = False

        if client is None:
            from core.ai_model_service import AIModelService

            if request.model_id:
                client = AIModelService.get_model_as_client(request.model_id)
            else:
                client = AIModelService.get_default_model_as_client()

            if client is None:
                return GenerateResult(
                    success=False,
                    message="未找到可用的 AI 模型配置，请先配置 AI 模型",
                )
            should_close = True

        try:
            messages_data = TestCasePrompt.build_messages(
                api_document=request.api_document,
                document_format=request.document_format,
                additional_requirements=request.additional_requirements,
            )

            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM if msg["role"] == "system" else MessageRole.USER,
                    content=msg["content"],
                )
                for msg in messages_data
            ]

            response = client.chat(messages)

            parsed_cases = TestCasePrompt.parse_response(response)

            saved_cases: list[TestCase] = []
            for tc in parsed_cases:
                test_case = TestCase(
                    name=tc.name,
                    api_path=tc.endpoint,
                    method=tc.method,
                    headers=tc.headers,
                    params={**tc.path_params, **tc.query_params},
                    body=tc.request_body,
                    expected_status=tc.expected_status,
                    assertions=tc.assertions,
                )
                test_case.save()
                saved_cases.append(test_case)

            return GenerateResult(
                success=True,
                message=f"成功生成并保存 {len(saved_cases)} 个测试用例",
                test_cases=saved_cases,
            )

        except Exception as e:
            return GenerateResult(
                success=False,
                message=f"生成测试用例失败: {str(e)}",
            )

        finally:
            if should_close and client:
                client.close()

    @staticmethod
    def generate_test_cases_from_json(
        json_content: str,
        additional_requirements: Optional[str] = None,
        model_id: Optional[int] = None,
    ) -> GenerateResult:
        return TestCaseService.generate_test_cases(
            TestCaseGenerateRequest(
                api_document=json_content,
                document_format=DocumentFormat.JSON,
                additional_requirements=additional_requirements,
                model_id=model_id,
            )
        )

    @staticmethod
    def generate_test_cases_from_yaml(
        yaml_content: str,
        additional_requirements: Optional[str] = None,
        model_id: Optional[int] = None,
    ) -> GenerateResult:
        return TestCaseService.generate_test_cases(
            TestCaseGenerateRequest(
                api_document=yaml_content,
                document_format=DocumentFormat.YAML,
                additional_requirements=additional_requirements,
                model_id=model_id,
            )
        )

    @staticmethod
    def generate_test_cases_from_markdown(
        markdown_content: str,
        additional_requirements: Optional[str] = None,
        model_id: Optional[int] = None,
    ) -> GenerateResult:
        return TestCaseService.generate_test_cases(
            TestCaseGenerateRequest(
                api_document=markdown_content,
                document_format=DocumentFormat.MARKDOWN,
                additional_requirements=additional_requirements,
                model_id=model_id,
            )
        )

    @staticmethod
    def create_test_case(request: TestCaseCreateRequest) -> TestCase:
        test_case = TestCase(
            name=request.name,
            api_path=request.api_path,
            method=request.method,
            headers=request.headers,
            params=request.params,
            body=request.body,
            expected_status=request.expected_status,
            assertions=request.assertions,
        )
        test_case.save()
        return test_case

    @staticmethod
    def update_test_case(request: TestCaseUpdateRequest) -> Optional[TestCase]:
        test_case = TestCase.get_by_id(request.id)
        if test_case is None:
            return None

        if request.name is not None:
            test_case.name = request.name
        if request.api_path is not None:
            test_case.api_path = request.api_path
        if request.method is not None:
            test_case.method = request.method
        if request.headers is not None:
            test_case.headers = request.headers
        if request.params is not None:
            test_case.params = request.params
        if request.body is not None:
            test_case.body = request.body
        if request.expected_status is not None:
            test_case.expected_status = request.expected_status
        if request.assertions is not None:
            test_case.assertions = request.assertions

        test_case.save()
        return test_case

    @staticmethod
    def delete_test_case(test_case_id: int) -> bool:
        test_case = TestCase.get_by_id(test_case_id)
        if test_case is None:
            return False
        test_case.delete()
        return True

    @staticmethod
    def delete_test_cases_batch(test_case_ids: list[int]) -> int:
        deleted_count = 0
        for test_case_id in test_case_ids:
            if TestCaseService.delete_test_case(test_case_id):
                deleted_count += 1
        return deleted_count

    @staticmethod
    def get_test_case_by_id(test_case_id: int) -> Optional[TestCase]:
        return TestCase.get_by_id(test_case_id)

    @staticmethod
    def get_all_test_cases() -> list[TestCase]:
        return TestCase.get_all()

    @staticmethod
    def get_test_cases_by_ids(test_case_ids: list[int]) -> list[TestCase]:
        return TestCase.get_by_ids(test_case_ids)

    @staticmethod
    def batch_update_test_cases(request: TestCaseBatchUpdateRequest) -> list[TestCase]:
        updated_cases: list[TestCase] = []
        for test_case_id in request.ids:
            test_case = TestCase.get_by_id(test_case_id)
            if test_case is None:
                continue

            for key, value in request.updates.items():
                if hasattr(test_case, key):
                    setattr(test_case, key, value)

            test_case.save()
            updated_cases.append(test_case)

        return updated_cases

    @staticmethod
    def search_test_cases(
        keyword: Optional[str] = None,
        method: Optional[str] = None,
        api_path_prefix: Optional[str] = None,
    ) -> list[TestCase]:
        all_cases = TestCase.get_all()

        filtered_cases = all_cases

        if keyword:
            keyword_lower = keyword.lower()
            filtered_cases = [
                tc
                for tc in filtered_cases
                if keyword_lower in tc.name.lower()
                or keyword_lower in tc.api_path.lower()
            ]

        if method:
            filtered_cases = [
                tc for tc in filtered_cases if tc.method.upper() == method.upper()
            ]

        if api_path_prefix:
            filtered_cases = [
                tc
                for tc in filtered_cases
                if tc.api_path.startswith(api_path_prefix)
            ]

        return filtered_cases

    @staticmethod
    def duplicate_test_case(test_case_id: int, new_name: Optional[str] = None) -> Optional[TestCase]:
        original = TestCase.get_by_id(test_case_id)
        if original is None:
            return None

        new_test_case = TestCase(
            name=new_name or f"{original.name} (副本)",
            api_path=original.api_path,
            method=original.method,
            headers=original.headers.copy(),
            params=original.params.copy(),
            body=original.body.copy() if original.body else None,
            expected_status=original.expected_status,
            assertions=original.assertions.copy(),
        )
        new_test_case.save()
        return new_test_case
