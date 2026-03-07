"""
测试脚本生成服务
提供根据测试用例生成 Python 测试脚本的功能
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from ai.client import AIClient, ChatMessage, MessageRole
from ai.prompts import TestCase as PromptTestCase
from ai.prompts import TestScriptPrompt
from models.test_case import TestCase
from models.test_script import TestScript


@dataclass
class ScriptGenerateRequest:
    test_case_ids: list[int]
    base_url: str = "http://localhost:8080"
    additional_requirements: Optional[str] = None
    model_id: Optional[int] = None
    use_ai_generation: bool = True


@dataclass
class ScriptCreateRequest:
    name: str
    content: str
    test_case_ids: list[int] = field(default_factory=list)


@dataclass
class ScriptUpdateRequest:
    id: int
    name: Optional[str] = None
    content: Optional[str] = None
    test_case_ids: Optional[list[int]] = None


@dataclass
class GenerateResult:
    success: bool
    message: str
    scripts: list[TestScript] = field(default_factory=list)


class TestScriptService:
    @staticmethod
    def generate_scripts(
        request: ScriptGenerateRequest,
        ai_client: Optional[AIClient] = None,
    ) -> GenerateResult:
        test_cases = TestCase.get_by_ids(request.test_case_ids)
        if not test_cases:
            return GenerateResult(
                success=False,
                message="未找到指定的测试用例",
            )

        if request.use_ai_generation:
            return TestScriptService._generate_with_ai(
                test_cases=test_cases,
                request=request,
                ai_client=ai_client,
            )
        else:
            return TestScriptService._generate_simple(
                test_cases=test_cases,
                request=request,
            )

    @staticmethod
    def _generate_with_ai(
        test_cases: list[TestCase],
        request: ScriptGenerateRequest,
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
            test_cases_data = []
            for tc in test_cases:
                prompt_tc = PromptTestCase(
                    id=f"TC_{tc.id:03d}",
                    name=tc.name,
                    description=f"测试接口 {tc.api_path}",
                    endpoint=tc.api_path,
                    method=tc.method,
                    headers=tc.headers,
                    query_params=tc.params,
                    request_body=tc.body,
                    expected_status=tc.expected_status,
                    assertions=tc.assertions,
                )
                test_cases_data.append(prompt_tc)

            messages_data = TestScriptPrompt.build_messages(
                test_cases=test_cases_data,
                base_url=request.base_url,
                additional_requirements=request.additional_requirements,
            )

            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM if msg["role"] == "system" else MessageRole.USER,
                    content=msg["content"],
                )
                for msg in messages_data
            ]

            response = client.chat(messages, max_tokens=8192)

            parsed_scripts = TestScriptPrompt.parse_response(response)

            saved_scripts: list[TestScript] = []
            for idx, script in enumerate(parsed_scripts):
                test_script = TestScript(
                    name=f"{test_cases[idx].name}_script" if idx < len(test_cases) else f"test_script_{idx}",
                    content=script.code,
                    test_case_ids=request.test_case_ids,
                )
                test_script.save()
                saved_scripts.append(test_script)

            return GenerateResult(
                success=True,
                message=f"成功生成并保存 {len(saved_scripts)} 个测试脚本",
                scripts=saved_scripts,
            )

        except Exception as e:
            return GenerateResult(
                success=False,
                message=f"生成测试脚本失败: {str(e)}",
            )

        finally:
            if should_close and client:
                client.close()

    @staticmethod
    def _generate_simple(
        test_cases: list[TestCase],
        request: ScriptGenerateRequest,
    ) -> GenerateResult:
        saved_scripts: list[TestScript] = []

        for tc in test_cases:
            prompt_tc = PromptTestCase(
                id=f"TC_{tc.id:03d}",
                name=tc.name,
                description=f"测试接口 {tc.api_path}",
                endpoint=tc.api_path,
                method=tc.method,
                headers=tc.headers,
                query_params=tc.params,
                request_body=tc.body,
                expected_status=tc.expected_status,
                assertions=tc.assertions,
            )

            code = TestScriptPrompt.generate_simple_script(
                test_case=prompt_tc,
                base_url=request.base_url,
            )

            test_script = TestScript(
                name=f"{tc.name}_script",
                content=code,
                test_case_ids=[tc.id] if tc.id else [],
            )
            test_script.save()
            saved_scripts.append(test_script)

        return GenerateResult(
            success=True,
            message=f"成功生成并保存 {len(saved_scripts)} 个测试脚本",
            scripts=saved_scripts,
        )

    @staticmethod
    def create_script(request: ScriptCreateRequest) -> TestScript:
        script = TestScript(
            name=request.name,
            content=request.content,
            test_case_ids=request.test_case_ids,
        )
        script.save()
        return script

    @staticmethod
    def update_script(request: ScriptUpdateRequest) -> Optional[TestScript]:
        script = TestScript.get_by_id(request.id)
        if script is None:
            return None

        if request.name is not None:
            script.name = request.name
        if request.content is not None:
            script.content = request.content
        if request.test_case_ids is not None:
            script.test_case_ids = request.test_case_ids

        script.save()
        return script

    @staticmethod
    def delete_script(script_id: int) -> bool:
        script = TestScript.get_by_id(script_id)
        if script is None:
            return False
        script.delete()
        return True

    @staticmethod
    def delete_scripts_batch(script_ids: list[int]) -> int:
        deleted_count = 0
        for script_id in script_ids:
            if TestScriptService.delete_script(script_id):
                deleted_count += 1
        return deleted_count

    @staticmethod
    def get_script_by_id(script_id: int) -> Optional[TestScript]:
        return TestScript.get_by_id(script_id)

    @staticmethod
    def get_all_scripts() -> list[TestScript]:
        return TestScript.get_all()

    @staticmethod
    def get_scripts_by_test_case_id(test_case_id: int) -> list[TestScript]:
        all_scripts = TestScript.get_all()
        return [
            script
            for script in all_scripts
            if test_case_id in script.test_case_ids
        ]

    @staticmethod
    def regenerate_script(
        script_id: int,
        base_url: str = "http://localhost:8080",
        model_id: Optional[int] = None,
        use_ai_generation: bool = True,
    ) -> GenerateResult:
        script = TestScript.get_by_id(script_id)
        if script is None:
            return GenerateResult(
                success=False,
                message=f"未找到 ID 为 {script_id} 的测试脚本",
            )

        if not script.test_case_ids:
            return GenerateResult(
                success=False,
                message="该测试脚本未关联任何测试用例",
            )

        request = ScriptGenerateRequest(
            test_case_ids=script.test_case_ids,
            base_url=base_url,
            model_id=model_id,
            use_ai_generation=use_ai_generation,
        )

        result = TestScriptService.generate_scripts(request)

        if result.success and result.scripts:
            TestScriptService.delete_script(script_id)

        return result
