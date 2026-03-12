"""
代码验证器模块
提供AI生成代码的验证、分析和修正功能
"""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from utils.logger import get_logger

_logger = get_logger("core.code_validator")


class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    level: ValidationLevel
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        location = ""
        if self.line is not None:
            location = f" (行 {self.line}"
            if self.column is not None:
                location += f", 列 {self.column}"
            location += ")"
        return f"[{self.level.value.upper()}]{location} {self.message}"


@dataclass
class ValidationResult:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    fixed_code: Optional[str] = None

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.WARNING]

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def get_error_message(self) -> str:
        if not self.has_errors():
            return ""
        return "\n".join(str(e) for e in self.errors)


class SyntaxValidator:
    REQUIRED_IMPORTS = {
        "pytest": "import pytest",
        "allure": "import allure",
        "requests": "import requests",
        "httpx": "import httpx",
        "json": "import json",
    }

    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        issues: list[ValidationIssue] = []

        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"语法错误: {e.msg}",
                    line=e.lineno,
                    column=e.offset,
                    suggestion="请检查语法是否正确，如括号匹配、缩进等",
                )
            )
            return ValidationResult(valid=False, issues=issues)

        return ValidationResult(valid=True, issues=issues)

    @classmethod
    def check_missing_imports(cls, code: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for module, import_stmt in cls.REQUIRED_IMPORTS.items():
            pattern = rf"\b{module}\."
            if re.search(pattern, code) and import_stmt not in code:
                if f"import {module}" not in code and f"from {module}" not in code:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            message=f"缺少导入: {import_stmt}",
                            suggestion=f"在文件开头添加: {import_stmt}",
                        )
                    )

        return issues

    @classmethod
    def fix_missing_imports(cls, code: str) -> tuple[str, list[str]]:
        missing_imports = []

        for module, import_stmt in cls.REQUIRED_IMPORTS.items():
            pattern = rf"\b{module}\."
            if re.search(pattern, code):
                if import_stmt not in code and f"import {module}" not in code and f"from {module}" not in code:
                    missing_imports.append(import_stmt)

        if not missing_imports:
            return code, []

        existing_imports = []
        other_lines = []

        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                existing_imports.append(line)
            else:
                other_lines.append(line)

        new_imports = missing_imports + existing_imports
        import_section = "\n".join(new_imports)

        code_lines = code.split("\n")
        first_non_import = 0
        for i, line in enumerate(code_lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("import ") and not stripped.startswith("from ") and not stripped.startswith("#") and not stripped.startswith('"""') and not stripped.startswith("'''"):
                first_non_import = i
                break

        header_lines = code_lines[:first_non_import]
        body_lines = code_lines[first_non_import:]

        docstring = ""
        docstring_end = 0
        if body_lines and (body_lines[0].strip().startswith('"""') or body_lines[0].strip().startswith("'''")):
            quote = '"""' if '"""' in body_lines[0] else "'''"
            docstring_lines = [body_lines[0]]
            for i in range(1, len(body_lines)):
                docstring_lines.append(body_lines[i])
                if quote in body_lines[i] and i > 0:
                    docstring_end = i + 1
                    break
            docstring = "\n".join(docstring_lines)

        if docstring:
            final_code = docstring + "\n\n" + "\n".join(missing_imports) + "\n" + "\n".join(body_lines[docstring_end:])
        else:
            final_code = "\n".join(missing_imports) + "\n\n" + "\n".join(body_lines)

        return final_code, missing_imports


class StaticAnalyzer:
    BUILTINS = {
        "print", "len", "range", "str", "int", "float", "list", "dict", "set", "tuple",
        "bool", "None", "True", "False", "if", "else", "elif", "for", "while", "def",
        "class", "return", "yield", "import", "from", "as", "with", "try", "except",
        "finally", "raise", "assert", "pass", "break", "continue", "and", "or", "not",
        "in", "is", "lambda", "global", "nonlocal", "async", "await", "__name__",
        "__file__", "__doc__", "__package__", "Exception", "BaseException", "TypeError",
        "ValueError", "KeyError", "IndexError", "AttributeError", "RuntimeError",
        "StopIteration", "GeneratorExit", "AssertionError", "ImportError",
        "ModuleNotFoundError", "OSError", "IOError", "FileNotFoundError",
        "PermissionError", "IsADirectoryError", "NotADirectoryError", "FileExistsError",
        "TimeoutError", "ConnectionError", "BrokenPipeError", "ConnectionAbortedError",
        "ConnectionRefusedError", "ConnectionResetError", "BlockingIOError",
        "ChildProcessError", "ProcessLookupError", "InterruptedError", "EOFError",
        "MemoryError", "RecursionError", "NotImplementedError", "ZeroDivisionError",
        "OverflowError", "FloatingPointError", "ArithmeticError", "LookupError",
        "UnicodeError", "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeTranslateError",
        "Warning", "UserWarning", "DeprecationWarning", "PendingDeprecationWarning",
        "SyntaxWarning", "RuntimeWarning", "FutureWarning", "ImportWarning",
        "UnicodeWarning", "BytesWarning", "ResourceWarning", "property", "classmethod",
        "staticmethod", "super", "type", "object", "any", "all", "abs", "divmod",
        "pow", "round", "bin", "hex", "oct", "chr", "ord", "repr", "ascii", "format",
        "sorted", "reversed", "enumerate", "zip", "map", "filter", "iter", "next",
        "slice", "hasattr", "getattr", "setattr", "delattr", "isinstance", "issubclass",
        "callable", "compile", "eval", "exec", "globals", "locals", "vars", "dir",
        "help", "id", "hash", "open", "input", "max", "min", "sum", "abs", "all",
        "any", "ascii", "bin", "bool", "bytearray", "bytes", "callable", "chr",
        "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod",
        "enumerate", "eval", "exec", "filter", "float", "format", "frozenset",
        "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input",
        "int", "isinstance", "issubclass", "iter", "len", "list", "locals", "map",
        "max", "memoryview", "min", "next", "object", "oct", "open", "ord", "pow",
        "print", "property", "range", "repr", "reversed", "round", "set", "setattr",
        "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple", "type",
        "vars", "zip", "__import__",
    }

    PYTEST_FIXTURES = {
        "request", "tmp_path", "tmp_path_factory", "tmpdir", "tmpdir_factory",
        "capfd", "capfdbinary", "caplog", "capsys", "capsysbinary",
        "cache", "monkeypatch", "pytestconfig", "record_property",
        "record_testsuite_property", "record_xml_attribute", "recwarn",
        "capfixture", "doctest_namespace", "event_loop", "client",
    }

    COMMON_TEST_VARIABLES = {
        "BASE_URL", "API_KEY", "TOKEN", "HEADERS", "TIMEOUT",
        "response", "result", "data", "json_data", "status_code",
        "expected", "actual", "url", "endpoint", "payload",
    }

    COMMON_FIXTURES = {
        "pytest": ["fixture", "raises", "skip", "mark", "parametrize"],
        "allure": ["step", "feature", "story", "title", "description", "severity",
                   "attach", "attachment_type", "severity_level", "link", "issue", "testCase"],
        "requests": ["get", "post", "put", "delete", "patch", "head", "options", "request", "Session", "Response"],
        "httpx": ["get", "post", "put", "delete", "patch", "head", "options", "request", "Client", "Response"],
    }

    @classmethod
    def analyze(cls, code: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return issues

        defined_names = set()
        imported_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                defined_names.add(node.name)
                for arg in node.args.args:
                    defined_names.add(arg.arg)
                for arg in node.args.kwonlyargs:
                    defined_names.add(arg.arg)
                if node.args.vararg:
                    defined_names.add(node.args.vararg.arg)
                if node.args.kwarg:
                    defined_names.add(node.args.kwarg.arg)
            elif isinstance(node, ast.ClassDef):
                defined_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)
                    elif isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                defined_names.add(elt.id)

        all_known_names = cls.BUILTINS | defined_names | imported_names | cls.PYTEST_FIXTURES | cls.COMMON_TEST_VARIABLES

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in all_known_names:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.WARNING,
                            message=f"可能未定义的变量或函数: '{node.id}'",
                            line=node.lineno,
                            column=node.col_offset,
                            suggestion=f"请检查 '{node.id}' 是否已定义或导入",
                        )
                    )

        return issues


class SandboxExecutor:
    SAFE_MODULES = {
        "pytest", "allure", "requests", "httpx", "json", "re", "os", "sys",
        "datetime", "time", "random", "string", "collections", "itertools",
        "functools", "typing", "pathlib", "io", "copy", "math", "decimal",
        "fractions", "hashlib", "base64", "uuid", "dataclasses", "enum",
    }

    @classmethod
    def validate_imports(cls, code: str) -> ValidationResult:
        issues: list[ValidationIssue] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                issues=[
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"语法错误: {e.msg}",
                        line=e.lineno,
                    )
                ],
            )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name not in cls.SAFE_MODULES:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.WARNING,
                                message=f"使用非标准库模块: '{alias.name}'",
                                line=node.lineno,
                                suggestion=f"请确保已安装 '{alias.name}' 模块",
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if module_name not in cls.SAFE_MODULES:
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.WARNING,
                                message=f"使用非标准库模块: '{node.module}'",
                                line=node.lineno,
                                suggestion=f"请确保已安装 '{node.module}' 模块",
                            )
                        )

        return ValidationResult(valid=len(issues) == 0, issues=issues)

    @classmethod
    def dry_run(cls, code: str) -> ValidationResult:
        issues: list[ValidationIssue] = []

        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"编译错误: {e.msg}",
                    line=e.lineno,
                    column=e.offset,
                )
            )
            return ValidationResult(valid=False, issues=issues)

        mock_allure = type("MockAllure", (), {})()
        mock_allure.step = lambda msg: type("MockContext", (), {"__enter__": lambda s: None, "__exit__": lambda s, *a: None})()
        mock_allure.feature = lambda *a: lambda f: f
        mock_allure.story = lambda *a: lambda f: f
        mock_allure.title = lambda *a: lambda f: f
        mock_allure.description = lambda *a: lambda f: f
        mock_allure.severity = lambda *a: lambda f: f
        mock_allure.attach = lambda *a, **k: None
        mock_allure.attachment_type = type("MockAttachmentType", (), {"JSON": "json", "TEXT": "text"})()

        mock_pytest = type("MockPytest", (), {})()
        mock_pytest.fixture = lambda *a, **k: lambda f: f
        mock_pytest.raises = type("MockRaises", (), {"__enter__": lambda s: None, "__exit__": lambda s, *a: None})
        mock_pytest.skip = lambda *a: None
        mock_pytest.mark = type("MockMark", (), {})()

        mock_requests = type("MockRequests", (), {})()
        mock_requests.get = lambda *a, **k: type("MockResponse", (), {"status_code": 200, "json": lambda: {}, "text": "{}"})()
        mock_requests.post = lambda *a, **k: type("MockResponse", (), {"status_code": 200, "json": lambda: {}, "text": "{}"})()
        mock_requests.put = lambda *a, **k: type("MockResponse", (), {"status_code": 200, "json": lambda: {}, "text": "{}"})()
        mock_requests.delete = lambda *a, **k: type("MockResponse", (), {"status_code": 200, "json": lambda: {}, "text": "{}"})()
        mock_requests.patch = lambda *a, **k: type("MockResponse", (), {"status_code": 200, "json": lambda: {}, "text": "{}"})()
        mock_requests.request = lambda *a, **k: type("MockResponse", (), {"status_code": 200, "json": lambda: {}, "text": "{}"})()

        mock_httpx = type("MockHttpx", (), {})()
        mock_httpx.get = lambda *a, **k: type("MockResponse", (), {"status_code": 200, "json": lambda: {}, "text": "{}"})()
        mock_httpx.post = lambda *a, **k: type("MockResponse", (), {"status_code": 200, "json": lambda: {}, "text": "{}"})()
        mock_httpx.Client = lambda *a, **k: type("MockClient", (), {"get": lambda s, *a, **k: mock_httpx.get(), "post": lambda s, *a, **k: mock_httpx.post()})()

        safe_globals = {
            "__builtins__": {
                "__import__": __import__,
                "__build_class__": __build_class__,
                "Exception": Exception,
                "True": True,
                "False": False,
                "None": None,
                "print": lambda *a, **k: None,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "bool": bool,
                "isinstance": isinstance,
                "hasattr": hasattr,
                "getattr": getattr,
                "setattr": setattr,
                "type": type,
                "super": super,
                "property": property,
                "classmethod": classmethod,
                "staticmethod": staticmethod,
                "object": object,
                "frozenset": frozenset,
                "bytes": bytes,
                "bytearray": bytearray,
                "memoryview": memoryview,
                "complex": complex,
                "abs": abs,
                "all": all,
                "any": any,
                "bin": bin,
                "chr": chr,
                "ord": ord,
                "hex": hex,
                "oct": oct,
                "id": id,
                "hash": hash,
                "repr": repr,
                "sorted": sorted,
                "reversed": reversed,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "iter": iter,
                "next": next,
                "slice": slice,
                "sum": sum,
                "min": min,
                "max": max,
                "round": round,
                "pow": pow,
                "divmod": divmod,
                "callable": callable,
                "open": lambda *a, **k: None,
                "input": lambda *a: "",
                "format": format,
                "ascii": ascii,
                "vars": vars,
                "dir": dir,
                "help": lambda *a: None,
                "globals": lambda: {},
                "locals": lambda: {},
                "compile": compile,
                "eval": lambda *a: None,
                "exec": lambda *a: None,
                "__name__": "__main__",
            },
            "pytest": mock_pytest,
            "allure": mock_allure,
            "requests": mock_requests,
            "httpx": mock_httpx,
            "json": __import__("json"),
            "re": __import__("re"),
            "os": __import__("os"),
            "sys": __import__("sys"),
            "datetime": __import__("datetime"),
            "time": __import__("time"),
            "random": __import__("random"),
            "string": __import__("string"),
            "collections": __import__("collections"),
            "typing": __import__("typing"),
            "pathlib": __import__("pathlib"),
            "math": __import__("math"),
            "dataclasses": __import__("dataclasses"),
            "enum": __import__("enum"),
        }

        try:
            exec(code, safe_globals, {})
        except NameError as e:
            match = re.search(r"name '(\w+)' is not defined", str(e))
            if match:
                undefined_name = match.group(1)
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"未定义的名称: '{undefined_name}'",
                        suggestion=f"请检查 '{undefined_name}' 是否已导入或定义",
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"名称错误: {str(e)}",
                    )
                )
        except ImportError as e:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"导入错误: {str(e)}",
                    suggestion="请检查所需的模块是否已安装",
                )
            )
        except Exception as e:
            error_type = type(e).__name__
            if error_type not in ["AssertionError", "SystemExit", "StopIteration"]:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        message=f"执行时可能的问题: {error_type}: {str(e)}",
                    )
                )

        return ValidationResult(valid=len([i for i in issues if i.level == ValidationLevel.ERROR]) == 0, issues=issues)


class CodeValidator:
    MAX_FIX_ATTEMPTS = 3

    @classmethod
    def validate(cls, code: str, run_sandbox: bool = True) -> ValidationResult:
        _logger.debug(f"开始验证代码, 代码长度: {len(code)} 字符")

        all_issues: list[ValidationIssue] = []

        syntax_result = SyntaxValidator.validate(code)
        if not syntax_result.valid:
            _logger.warning(f"语法验证失败: {syntax_result.get_error_message()}")
            return syntax_result
        all_issues.extend(syntax_result.issues)
        _logger.debug("语法验证通过")

        import_issues = SyntaxValidator.check_missing_imports(code)
        if import_issues:
            _logger.debug(f"发现 {len(import_issues)} 个导入问题")
        all_issues.extend(import_issues)

        static_issues = StaticAnalyzer.analyze(code)
        if static_issues:
            _logger.debug(f"静态分析发现 {len(static_issues)} 个问题")
        all_issues.extend(static_issues)

        if run_sandbox:
            sandbox_result = SandboxExecutor.dry_run(code)
            if sandbox_result.issues:
                _logger.debug(f"沙箱执行发现 {len(sandbox_result.issues)} 个问题")
            all_issues.extend(sandbox_result.issues)

        has_errors = any(i.level == ValidationLevel.ERROR for i in all_issues)
        error_count = sum(1 for i in all_issues if i.level == ValidationLevel.ERROR)
        warning_count = sum(1 for i in all_issues if i.level == ValidationLevel.WARNING)
        _logger.info(f"代码验证完成: {'通过' if not has_errors else '失败'}, 错误: {error_count}, 警告: {warning_count}")

        return ValidationResult(valid=not has_errors, issues=all_issues)

    @classmethod
    def fix_code(cls, code: str) -> ValidationResult:
        _logger.debug("开始自动修正代码")

        fixed_code, added_imports = SyntaxValidator.fix_missing_imports(code)
        issues: list[ValidationIssue] = []

        if added_imports:
            _logger.info(f"自动添加缺失的导入: {', '.join(added_imports)}")
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.INFO,
                    message=f"已自动添加缺失的导入: {', '.join(added_imports)}",
                )
            )

        validation_result = cls.validate(fixed_code, run_sandbox=True)
        all_issues = issues + validation_result.issues

        return ValidationResult(
            valid=validation_result.valid,
            issues=all_issues,
            fixed_code=fixed_code if added_imports else None,
        )

    @classmethod
    def validate_and_fix(cls, code: str) -> ValidationResult:
        _logger.debug("开始验证并尝试自动修正代码")

        result = cls.validate(code)

        if result.valid:
            _logger.debug("代码验证通过，无需修正")
            return result

        _logger.debug("代码验证失败，尝试自动修正")
        fix_result = cls.fix_code(code)
        if fix_result.fixed_code:
            new_validation = cls.validate(fix_result.fixed_code)
            if new_validation.valid:
                _logger.info("代码自动修正成功")
                return ValidationResult(
                    valid=True,
                    issues=fix_result.issues + [
                        ValidationIssue(
                            level=ValidationLevel.INFO,
                            message="代码已自动修正",
                        )
                    ],
                    fixed_code=fix_result.fixed_code,
                )
            else:
                _logger.warning("代码自动修正后仍有问题")

        return fix_result
