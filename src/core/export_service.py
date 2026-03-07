"""
导出下载服务
提供测试用例和测试脚本的导出功能
"""

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

from models.test_case import TestCase
from models.test_script import TestScript


class ExportFormat(Enum):
    JSON = "json"
    YAML = "yaml"


@dataclass
class ExportResult:
    success: bool
    message: str
    content: Optional[bytes] = None
    filename: Optional[str] = None


@dataclass
class TestCaseExportRequest:
    test_case_ids: list[int]
    format: ExportFormat = ExportFormat.JSON
    include_metadata: bool = True


@dataclass
class TestScriptExportRequest:
    script_ids: list[int]
    include_test_cases: bool = False
    create_init_file: bool = True


class ExportService:
    @staticmethod
    def export_test_cases(request: TestCaseExportRequest) -> ExportResult:
        test_cases = TestCase.get_by_ids(request.test_case_ids)
        if not test_cases:
            return ExportResult(
                success=False,
                message="未找到指定的测试用例",
            )

        try:
            data = ExportService._build_export_data(
                test_cases=test_cases,
                include_metadata=request.include_metadata,
            )

            if request.format == ExportFormat.JSON:
                content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
                filename = ExportService._generate_filename("test_cases", "json")
            else:
                content = yaml.dump(
                    data,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                ).encode("utf-8")
                filename = ExportService._generate_filename("test_cases", "yaml")

            return ExportResult(
                success=True,
                message=f"成功导出 {len(test_cases)} 个测试用例",
                content=content,
                filename=filename,
            )

        except Exception as e:
            return ExportResult(
                success=False,
                message=f"导出测试用例失败: {str(e)}",
            )

    @staticmethod
    def export_all_test_cases(format: ExportFormat = ExportFormat.JSON) -> ExportResult:
        test_cases = TestCase.get_all()
        if not test_cases:
            return ExportResult(
                success=False,
                message="没有可导出的测试用例",
            )

        return ExportService.export_test_cases(
            TestCaseExportRequest(
                test_case_ids=[tc.id for tc in test_cases if tc.id],
                format=format,
            )
        )

    @staticmethod
    def export_test_scripts(request: TestScriptExportRequest) -> ExportResult:
        scripts: list[TestScript] = []
        for script_id in request.script_ids:
            script = TestScript.get_by_id(script_id)
            if script:
                scripts.append(script)

        if not scripts:
            return ExportResult(
                success=False,
                message="未找到指定的测试脚本",
            )

        try:
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                if request.create_init_file:
                    zip_file.writestr("__init__.py", "")

                if request.include_test_cases:
                    test_case_ids = list(
                        set(
                            tc_id
                            for script in scripts
                            for tc_id in script.test_case_ids
                        )
                    )
                    if test_case_ids:
                        test_cases = TestCase.get_by_ids(test_case_ids)
                        test_cases_data = ExportService._build_export_data(
                            test_cases=test_cases,
                            include_metadata=True,
                        )
                        zip_file.writestr(
                            "test_cases.json",
                            json.dumps(test_cases_data, ensure_ascii=False, indent=2),
                        )

                for script in scripts:
                    safe_name = ExportService._sanitize_filename(script.name)
                    filename = f"test_{safe_name}.py"
                    zip_file.writestr(filename, script.content)

                readme_content = ExportService._generate_readme(scripts)
                zip_file.writestr("README.md", readme_content)

            zip_buffer.seek(0)
            content = zip_buffer.getvalue()
            filename = ExportService._generate_filename("test_scripts", "zip")

            return ExportResult(
                success=True,
                message=f"成功导出 {len(scripts)} 个测试脚本",
                content=content,
                filename=filename,
            )

        except Exception as e:
            return ExportResult(
                success=False,
                message=f"导出测试脚本失败: {str(e)}",
            )

    @staticmethod
    def export_all_test_scripts(include_test_cases: bool = False) -> ExportResult:
        scripts = TestScript.get_all()
        if not scripts:
            return ExportResult(
                success=False,
                message="没有可导出的测试脚本",
            )

        return ExportService.export_test_scripts(
            TestScriptExportRequest(
                script_ids=[s.id for s in scripts if s.id],
                include_test_cases=include_test_cases,
            )
        )

    @staticmethod
    def export_single_script(script_id: int) -> ExportResult:
        script = TestScript.get_by_id(script_id)
        if script is None:
            return ExportResult(
                success=False,
                message=f"未找到 ID 为 {script_id} 的测试脚本",
            )

        try:
            safe_name = ExportService._sanitize_filename(script.name)
            filename = f"test_{safe_name}.py"
            content = script.content.encode("utf-8")

            return ExportResult(
                success=True,
                message="成功导出测试脚本",
                content=content,
                filename=filename,
            )

        except Exception as e:
            return ExportResult(
                success=False,
                message=f"导出测试脚本失败: {str(e)}",
            )

    @staticmethod
    def export_test_cases_by_filter(
        keyword: Optional[str] = None,
        method: Optional[str] = None,
        api_path_prefix: Optional[str] = None,
        format: ExportFormat = ExportFormat.JSON,
    ) -> ExportResult:
        from core.test_case_service import TestCaseService

        test_cases = TestCaseService.search_test_cases(
            keyword=keyword,
            method=method,
            api_path_prefix=api_path_prefix,
        )

        if not test_cases:
            return ExportResult(
                success=False,
                message="没有符合条件的测试用例",
            )

        return ExportService.export_test_cases(
            TestCaseExportRequest(
                test_case_ids=[tc.id for tc in test_cases if tc.id],
                format=format,
            )
        )

    @staticmethod
    def _build_export_data(
        test_cases: list[TestCase],
        include_metadata: bool = True,
    ) -> dict:
        cases_data = [tc.to_dict() for tc in test_cases]

        if include_metadata:
            return {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "total_count": len(cases_data),
                    "version": "1.0",
                },
                "test_cases": cases_data,
            }
        else:
            return {"test_cases": cases_data}

    @staticmethod
    def _generate_filename(prefix: str, extension: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        safe_chars = []
        for char in name:
            if char.isalnum() or char in "_-":
                safe_chars.append(char)
            elif char.isspace():
                safe_chars.append("_")
        result = "".join(safe_chars)
        return result.lower() if result else "unnamed"

    @staticmethod
    def _generate_readme(scripts: list[TestScript]) -> str:
        content = """# 测试脚本说明

本压缩包包含自动生成的 pytest 测试脚本。

## 文件列表

"""
        for script in scripts:
            safe_name = ExportService._sanitize_filename(script.name)
            content += f"- `test_{safe_name}.py` - {script.name}\n"

        content += """
## 运行要求

- Python 3.11+
- pytest
- requests
- allure-pytest (可选，用于生成 Allure 报告)

## 安装依赖

```bash
pip install pytest requests allure-pytest
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行指定测试文件
pytest test_xxx.py

# 生成 Allure 报告
pytest --alluredir=./allure-results
allure serve ./allure-results
```

## 注意事项

1. 请根据实际环境修改 `BASE_URL` 变量
2. 部分测试可能需要先配置测试数据
3. 建议在测试环境中运行测试

---
生成时间: {timestamp}
""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        return content

    @staticmethod
    def save_to_file(content: bytes, filepath: str) -> bool:
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return True
        except Exception:
            return False
