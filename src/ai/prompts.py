"""
AI Prompt 模板模块
提供测试用例生成和测试脚本生成的 Prompt 模板
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class DocumentFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    OPENAPI = "openapi"


@dataclass
class TestCaseField:
    name: str
    description: str
    required: bool = True
    type_hint: str = "str"
    example: Optional[str] = None


@dataclass
class TestCase:
    id: str
    name: str
    description: str
    endpoint: str
    method: str
    headers: dict[str, str] = field(default_factory=dict)
    path_params: dict[str, Any] = field(default_factory=dict)
    query_params: dict[str, Any] = field(default_factory=dict)
    request_body: Optional[dict[str, Any]] = None
    expected_status: int = 200
    expected_response: Optional[dict[str, Any]] = None
    assertions: list[dict[str, Any]] = field(default_factory=list)
    priority: str = "medium"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "endpoint": self.endpoint,
            "method": self.method,
            "headers": self.headers,
            "path_params": self.path_params,
            "query_params": self.query_params,
            "request_body": self.request_body,
            "expected_status": self.expected_status,
            "expected_response": self.expected_response,
            "assertions": self.assertions,
            "priority": self.priority,
            "tags": self.tags,
        }


@dataclass
class TestScript:
    test_case_id: str
    test_case_name: str
    code: str
    imports: list[str] = field(default_factory=list)
    fixtures: list[str] = field(default_factory=list)
    allure_features: list[str] = field(default_factory=list)
    allure_stories: list[str] = field(default_factory=list)
    allure_severity: str = "normal"

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "test_case_name": self.test_case_name,
            "code": self.code,
            "imports": self.imports,
            "fixtures": self.fixtures,
            "allure_features": self.allure_features,
            "allure_stories": self.allure_stories,
            "allure_severity": self.allure_severity,
        }


class TestCasePrompt:
    TEST_CASE_SYSTEM_PROMPT = """你是一个专业的 API 测试工程师，擅长分析接口文档并生成全面的测试用例。
你需要根据用户提供的接口文档，生成结构化的测试用例，确保覆盖各种测试场景。

测试用例应该包括：
1. 正常场景测试（Happy Path）
2. 边界值测试
3. 异常场景测试（如参数缺失、类型错误、权限问题等）
4. 性能相关测试（如大数据量请求）

输出格式要求：必须输出有效的 JSON 数组，每个测试用例包含以下字段：
- id: 测试用例唯一标识（格式：TC_XXX_001）
- name: 测试用例名称
- description: 测试用例描述
- endpoint: 接口路径
- method: HTTP 方法（GET/POST/PUT/DELETE/PATCH）
- headers: 请求头字典
- path_params: 路径参数字典
- query_params: 查询参数字典
- request_body: 请求体（可选）
- expected_status: 预期 HTTP 状态码
- expected_response: 预期响应体（可选）
- assertions: 断言列表，每个断言包含 type（断言类型）、path（JSONPath）、expected（期望值）
- priority: 优先级（high/medium/low）
- tags: 标签列表"""

    @classmethod
    def build_prompt(
        cls,
        api_document: str,
        document_format: DocumentFormat = DocumentFormat.JSON,
        additional_requirements: Optional[str] = None,
    ) -> str:
        format_instruction = {
            DocumentFormat.JSON: "接口文档为 JSON 格式",
            DocumentFormat.YAML: "接口文档为 YAML 格式",
            DocumentFormat.MARKDOWN: "接口文档为 Markdown 格式",
            DocumentFormat.OPENAPI: "接口文档为 OpenAPI/Swagger 格式",
        }

        prompt = f"""请根据以下接口文档生成测试用例。

{format_instruction.get(document_format, '')}

接口文档内容：
```
{api_document}
```
"""
        if additional_requirements:
            prompt += f"\n额外要求：\n{additional_requirements}\n"

        prompt += """
请生成完整的测试用例，直接输出 JSON 数组格式，不要包含任何其他说明文字。
确保 JSON 格式正确，可以被直接解析。"""
        return prompt

    @classmethod
    def build_messages(
        cls,
        api_document: str,
        document_format: DocumentFormat = DocumentFormat.JSON,
        additional_requirements: Optional[str] = None,
    ) -> list[dict[str, str]]:
        from .client import ChatMessage, MessageRole

        return [
            {"role": "system", "content": cls.TEST_CASE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": cls.build_prompt(
                    api_document, document_format, additional_requirements
                ),
            },
        ]

    @classmethod
    def parse_response(cls, response: dict[str, Any]) -> list[TestCase]:
        choices = response.get("choices", [])
        if not choices:
            return []

        content = choices[0].get("message", {}).get("content", "")
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            test_cases_data = json.loads(content)
        except json.JSONDecodeError:
            return []

        if not isinstance(test_cases_data, list):
            test_cases_data = [test_cases_data]

        test_cases = []
        for tc_data in test_cases_data:
            try:
                test_case = TestCase(
                    id=tc_data.get("id", ""),
                    name=tc_data.get("name", ""),
                    description=tc_data.get("description", ""),
                    endpoint=tc_data.get("endpoint", ""),
                    method=tc_data.get("method", "GET"),
                    headers=tc_data.get("headers", {}),
                    path_params=tc_data.get("path_params", {}),
                    query_params=tc_data.get("query_params", {}),
                    request_body=tc_data.get("request_body"),
                    expected_status=tc_data.get("expected_status", 200),
                    expected_response=tc_data.get("expected_response"),
                    assertions=tc_data.get("assertions", []),
                    priority=tc_data.get("priority", "medium"),
                    tags=tc_data.get("tags", []),
                )
                test_cases.append(test_case)
            except Exception:
                continue

        return test_cases


class TestScriptPrompt:
    TEST_SCRIPT_SYSTEM_PROMPT = """你是一个专业的 Python 测试开发工程师，擅长编写自动化测试脚本。
你需要根据测试用例生成符合 pytest + Allure 框架规范的 Python 测试代码。

代码规范要求：
1. 使用 pytest 框架编写测试函数
2. 使用 allure-pytest 添加 Allure 注解
3. 使用 requests 库发送 HTTP 请求
4. 包含完整的断言验证
5. 代码需要有适当的注释
6. 遵循 PEP 8 编码规范

Allure 注解要求：
- @allure.feature: 功能模块名称
- @allure.story: 用户故事或场景
- @allure.severity: 严重程度（blocker/critical/normal/minor/trivial）
- @allure.title: 测试用例标题
- @allure.description: 测试用例描述
- @allure.step: 测试步骤

输出格式要求：必须输出有效的 JSON 对象，包含以下字段：
- test_case_id: 测试用例 ID
- test_case_name: 测试用例名称
- code: 完整的 Python 测试代码（字符串）
- imports: 需要导入的模块列表
- fixtures: 需要的 pytest fixtures
- allure_features: Allure feature 列表
- allure_stories: Allure story 列表
- allure_severity: Allure 严重程度"""

    CODE_TEMPLATE = '''"""
测试用例: {test_case_name}
测试 ID: {test_case_id}
描述: {description}
"""
import allure
import pytest
import requests

{imports}

BASE_URL = "{{base_url}}"  # 请根据实际环境修改


@allure.feature("{feature}")
@allure.story("{story}")
@allure.severity("{severity}")
@allure.title("{test_case_name}")
@allure.description("{description}")
def test_{test_function_name}():
    """测试 {test_case_name}"""
    
    # 准备请求参数
    endpoint = "{endpoint}"
    method = "{method}"
    headers = {headers}
    {params_section}
    {body_section}
    
    # 发送请求
    with allure.step("发送 {method} 请求到 {endpoint}"):
        response = requests.{method_lower}(
            url=f"{{BASE_URL}}{{endpoint}}",
            headers=headers,
            {params_arg}
            {body_arg}
            timeout=30
        )
    
    # 验证响应状态码
    with allure.step("验证响应状态码"):
        assert response.status_code == {expected_status}, \\
            f"预期状态码 {expected_status}, 实际状态码 {{response.status_code}}"
    
    # 验证响应内容
    {assertions_section}
    
    # 附加响应信息到 Allure 报告
    allure.attach(
        response.text,
        name="响应内容",
        attachment_type=allure.attachment_type.JSON
    )
'''

    @classmethod
    def build_prompt(
        cls,
        test_cases: list[dict[str, Any]] | list[TestCase],
        base_url: str = "http://localhost:8080",
        additional_requirements: Optional[str] = None,
    ) -> str:
        test_cases_data = []
        for tc in test_cases:
            if isinstance(tc, TestCase):
                test_cases_data.append(tc.to_dict())
            else:
                test_cases_data.append(tc)

        prompt = f"""请根据以下测试用例生成 Python 测试脚本。

测试用例（JSON 格式）：
```json
{json.dumps(test_cases_data, ensure_ascii=False, indent=2)}
```

基础 URL: {base_url}
"""
        if additional_requirements:
            prompt += f"\n额外要求：\n{additional_requirements}\n"

        prompt += """
请生成完整的测试脚本，直接输出 JSON 格式（如果是多个测试用例则输出数组），不要包含任何其他说明文字。
确保 JSON 格式正确，可以被直接解析。"""
        return prompt

    @classmethod
    def build_messages(
        cls,
        test_cases: list[dict[str, Any]] | list[TestCase],
        base_url: str = "http://localhost:8080",
        additional_requirements: Optional[str] = None,
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": cls.TEST_SCRIPT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": cls.build_prompt(
                    test_cases, base_url, additional_requirements
                ),
            },
        ]

    @classmethod
    def parse_response(cls, response: dict[str, Any]) -> list[TestScript]:
        choices = response.get("choices", [])
        if not choices:
            return []

        content = choices[0].get("message", {}).get("content", "")
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```python"):
            content = content[9:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            scripts_data = json.loads(content)
        except json.JSONDecodeError:
            return []

        if not isinstance(scripts_data, list):
            scripts_data = [scripts_data]

        test_scripts = []
        for script_data in scripts_data:
            try:
                test_script = TestScript(
                    test_case_id=script_data.get("test_case_id", ""),
                    test_case_name=script_data.get("test_case_name", ""),
                    code=script_data.get("code", ""),
                    imports=script_data.get("imports", []),
                    fixtures=script_data.get("fixtures", []),
                    allure_features=script_data.get("allure_features", []),
                    allure_stories=script_data.get("allure_stories", []),
                    allure_severity=script_data.get("allure_severity", "normal"),
                )
                test_scripts.append(test_script)
            except Exception:
                continue

        return test_scripts

    @classmethod
    def generate_simple_script(
        cls,
        test_case: TestCase,
        base_url: str = "http://localhost:8080",
    ) -> str:
        test_function_name = test_case.id.lower().replace("-", "_")

        headers_str = json.dumps(test_case.headers, ensure_ascii=False, indent=8)

        params_section = ""
        params_arg = ""
        if test_case.query_params:
            params_section = f"params = {json.dumps(test_case.query_params, ensure_ascii=False, indent=8)}"
            params_arg = "params=params,"

        body_section = ""
        body_arg = ""
        if test_case.request_body:
            body_section = f"json_body = {json.dumps(test_case.request_body, ensure_ascii=False, indent=8)}"
            body_arg = "json=json_body,"

        assertions_section = cls._generate_assertions(test_case)

        feature = test_case.tags[0] if test_case.tags else "API测试"
        story = test_case.name
        severity = cls._map_priority_to_severity(test_case.priority)

        code = cls.CODE_TEMPLATE.format(
            test_case_name=test_case.name,
            test_case_id=test_case.id,
            description=test_case.description,
            imports="",
            base_url=base_url,
            feature=feature,
            story=story,
            severity=severity,
            test_function_name=test_function_name,
            endpoint=test_case.endpoint,
            method=test_case.method,
            headers=headers_str,
            params_section=params_section,
            body_section=body_section,
            method_lower=test_case.method.lower(),
            params_arg=params_arg,
            body_arg=body_arg,
            expected_status=test_case.expected_status,
            assertions_section=assertions_section,
        )

        return code

    @classmethod
    def _generate_assertions(cls, test_case: TestCase) -> str:
        assertions = []

        if test_case.expected_response:
            assertions.append(
                f"expected_response = {json.dumps(test_case.expected_response, ensure_ascii=False, indent=8)}"
            )
            assertions.append(
                "    with allure.step(\"验证响应内容\"):\n"
                "        response_json = response.json()\n"
                "        assert response_json == expected_response, \"响应内容不匹配\""
            )

        for assertion in test_case.assertions:
            assertion_type = assertion.get("type", "equals")
            path = assertion.get("path", "")
            expected = assertion.get("expected")

            if assertion_type == "equals":
                assertions.append(
                    f'    with allure.step("验证字段 {path}"):\n'
                    f'        assert response.json().get("{path}") == {json.dumps(expected)}, \\\n'
                    f'            f"字段 {path} 值不匹配"'
                )
            elif assertion_type == "contains":
                assertions.append(
                    f'    with allure.step("验证字段 {path} 包含预期值"):\n'
                    f'        assert {json.dumps(expected)} in response.json().get("{path}", []), \\\n'
                    f'            f"字段 {path} 不包含预期值"'
                )
            elif assertion_type == "not_null":
                assertions.append(
                    f'    with allure.step("验证字段 {path} 不为空"):\n'
                    f'        assert response.json().get("{path}") is not None, \\\n'
                    f'            f"字段 {path} 为空"'
                )

        if not assertions:
            return "pass  # 暂无断言"

        return "\n".join(assertions)

    @classmethod
    def _map_priority_to_severity(cls, priority: str) -> str:
        mapping = {
            "high": "critical",
            "medium": "normal",
            "low": "minor",
        }
        return mapping.get(priority, "normal")
