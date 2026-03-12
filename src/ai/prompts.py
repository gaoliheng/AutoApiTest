"""
AI Prompt 模板模块
提供测试用例生成和测试脚本生成的 Prompt 模板
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from utils.logger import get_logger

_logger = get_logger("ai.prompts")


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

    REQUIRED_FIELDS = ["id", "name", "endpoint", "method"]
    OPTIONAL_FIELDS = ["description", "headers", "path_params", "query_params", 
                       "request_body", "expected_status", "expected_response", 
                       "assertions", "priority", "tags"]

    @classmethod
    def parse_response(cls, response: dict[str, Any]) -> list[TestCase]:
        choices = response.get("choices", [])
        if not choices:
            _logger.warning("AI响应中没有choices")
            return []

        content = choices[0].get("message", {}).get("content", "")
        content = content.strip()

        if not content:
            _logger.warning("AI响应内容为空")
            return []

        content = cls._clean_json_content(content)
        
        test_cases_data = cls._try_parse_json(content)
        
        if test_cases_data is None:
            _logger.warning("JSON解析失败，尝试正则提取...")
            test_cases_data = cls._extract_by_regex(content)
        
        if not test_cases_data:
            _logger.error(f"无法提取测试用例，内容前500字符: {content[:500]}")
            return []

        if not isinstance(test_cases_data, list):
            test_cases_data = [test_cases_data]

        test_cases = []
        for tc_data in test_cases_data:
            if not cls._validate_test_case_data(tc_data):
                _logger.warning(f"测试用例数据不完整: {tc_data.get('id', 'unknown')}")
                continue
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
            except Exception as e:
                _logger.warning(f"解析测试用例失败: {e}")
                continue

        _logger.info(f"成功解析 {len(test_cases)} 个测试用例")
        return test_cases

    @classmethod
    def _validate_test_case_data(cls, data: dict) -> bool:
        if not isinstance(data, dict):
            return False
        for field in cls.REQUIRED_FIELDS:
            if field not in data or data[field] is None or data[field] == "":
                _logger.debug(f"缺少必需字段: {field}")
                return False
        return True

    @classmethod
    def _extract_by_regex(cls, content: str) -> list[dict]:
        test_cases = []
        
        tc_blocks = re.split(r'\}\s*,\s*\{', content)
        
        for i, block in enumerate(tc_blocks):
            tc_data = {}
            
            id_match = re.search(r'"id"\s*:\s*"([^"]*)"', block)
            if id_match:
                tc_data["id"] = id_match.group(1)
            
            name_match = re.search(r'"name"\s*:\s*"([^"]*)"', block)
            if name_match:
                tc_data["name"] = name_match.group(1)
            
            endpoint_match = re.search(r'"endpoint"\s*:\s*"([^"]*)"', block)
            if endpoint_match:
                tc_data["endpoint"] = endpoint_match.group(1)
            
            method_match = re.search(r'"method"\s*:\s*"(\w+)"', block)
            if method_match:
                tc_data["method"] = method_match.group(1)
            
            desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', block)
            if desc_match:
                tc_data["description"] = desc_match.group(1)
            
            status_match = re.search(r'"expected_status"\s*:\s*(\d+)', block)
            if status_match:
                tc_data["expected_status"] = int(status_match.group(1))
            
            priority_match = re.search(r'"priority"\s*:\s*"(\w+)"', block)
            if priority_match:
                tc_data["priority"] = priority_match.group(1)
            
            headers_match = re.search(r'"headers"\s*:\s*(\{[^}]*\})', block)
            if headers_match:
                try:
                    tc_data["headers"] = json.loads(headers_match.group(1))
                except:
                    tc_data["headers"] = {}
            
            query_params_match = re.search(r'"query_params"\s*:\s*(\{[^}]*\})', block)
            if query_params_match:
                try:
                    tc_data["query_params"] = json.loads(query_params_match.group(1))
                except:
                    tc_data["query_params"] = {}
            
            request_body_match = re.search(r'"request_body"\s*:\s*(\{[\s\S]*?\})\s*,\s*"', block)
            if request_body_match:
                try:
                    tc_data["request_body"] = json.loads(request_body_match.group(1))
                except:
                    pass
            
            if tc_data.get("id") and tc_data.get("name"):
                test_cases.append(tc_data)
        
        return test_cases

    @classmethod
    def _clean_json_content(cls, content: str) -> str:
        content = content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            content = json_match.group(0)
        else:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                content = "[" + json_match.group(0) + "]"
        
        return content

    @classmethod
    def _try_parse_json(cls, content: str) -> Any:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            _logger.debug(f"直接JSON解析失败: {e}")
        
        fixed_content = cls._fix_json(content)
        try:
            return json.loads(fixed_content)
        except json.JSONDecodeError as e:
            _logger.debug(f"修复后JSON解析失败: {e}")
        
        return None

    @classmethod
    def _fix_json(cls, content: str) -> str:
        content = re.sub(r',\s*]', ']', content)
        content = re.sub(r',\s*}', '}', content)
        
        content = re.sub(r'(?<!\\)"(?![\s:,\]\}])', '\\"', content)
        
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        if open_brackets > 0:
            content += ']' * open_brackets
        if open_braces > 0:
            content += '}' * open_braces
        
        return content


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
            _logger.warning("AI响应中没有choices")
            return []

        content = choices[0].get("message", {}).get("content", "")
        content = content.strip()

        if not content:
            _logger.warning("AI响应内容为空")
            return []

        content = cls._clean_json_content(content)
        
        scripts_data = cls._try_parse_json(content)
        
        if scripts_data is None:
            _logger.error(f"JSON解析失败，内容前500字符: {content[:500]}")
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
            except Exception as e:
                _logger.warning(f"解析测试脚本失败: {e}")
                continue

        _logger.info(f"成功解析 {len(test_scripts)} 个测试脚本")
        return test_scripts

    @classmethod
    def _clean_json_content(cls, content: str) -> str:
        content = content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```python"):
            content = content[9:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            content = json_match.group(0)
        else:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                content = "[" + json_match.group(0) + "]"
        
        return content

    @classmethod
    def _try_parse_json(cls, content: str) -> Any:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            _logger.debug(f"直接JSON解析失败: {e}")
        
        fixed_content = cls._fix_json(content)
        try:
            return json.loads(fixed_content)
        except json.JSONDecodeError as e:
            _logger.debug(f"修复后JSON解析失败: {e}")
        
        return None

    @classmethod
    def _fix_json(cls, content: str) -> str:
        content = re.sub(r',\s*]', ']', content)
        content = re.sub(r',\s*}', '}', content)
        
        content = re.sub(r'(?<!\\)"(?![\s:,\]\}])', '\\"', content)
        
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        if open_brackets > 0:
            content += ']' * open_brackets
        if open_braces > 0:
            content += '}' * open_braces
        
        return content

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


class CodeFixPrompt:
    CODE_FIX_SYSTEM_PROMPT = """你是一个专业的Python代码修复专家。你的任务是修复有问题的Python测试代码。

修复原则：
1. 保持原有代码的功能和意图不变
2. 只修复报告的错误，不要随意修改其他代码
3. 确保修复后的代码可以正常运行
4. 保持代码风格一致

常见问题修复指南：
- 语法错误：检查括号匹配、缩进、冒号等
- 导入缺失：添加必要的import语句
- 未定义变量：检查变量名拼写或添加定义
- 类型错误：确保类型匹配
- 断言错误：修正断言逻辑

输出要求：
- 直接输出修复后的完整Python代码
- 用```python包裹代码
- 不要添加任何解释说明"""

    @classmethod
    def build_messages(
        cls,
        original_code: str,
        error_messages: list[str],
    ) -> list[dict[str, str]]:
        from .client import ChatMessage, MessageRole

        error_text = "\n".join(f"- {err}" for err in error_messages)

        user_message = f"""请修复以下Python测试代码中的错误。

## 原始代码
```python
{original_code}
```

## 检测到的问题
{error_text}

请修复这些问题并输出完整的修正后的代码。"""

        return [
            {"role": "system", "content": cls.CODE_FIX_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

    @classmethod
    def parse_response(cls, response: dict[str, Any]) -> Optional[str]:
        choices = response.get("choices", [])
        if not choices:
            _logger.warning("AI响应中没有choices")
            return None

        content = choices[0].get("message", {}).get("content", "")
        content = content.strip()

        if not content:
            _logger.warning("AI响应内容为空")
            return None

        if "```python" in content:
            start = content.find("```python") + 9
            end = content.find("```", start)
            if end > start:
                result = content[start:end].strip()
                _logger.info(f"成功提取Python代码，长度: {len(result)}")
                return result
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                result = content[start:end].strip()
                _logger.info(f"成功提取代码块，长度: {len(result)}")
                return result

        if content and ("import " in content or "def " in content):
            _logger.info(f"直接返回代码内容，长度: {len(content)}")
            return content

        _logger.warning("无法从响应中提取有效代码")
        return None
