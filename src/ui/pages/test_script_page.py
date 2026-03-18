import json
import re
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QComboBox,
    QGroupBox,
    QMessageBox,
    QProgressBar,
    QFileDialog,
)

from models.ai_model import AIModel
from ai.client import AIClient, AIModelConfig, ChatMessage, MessageRole
from core.code_validator import CodeValidator, ValidationLevel
from ui.styles import style_manager
from ui.pages.base_page import BasePage
from ui.pages.test_case_page import (
    get_test_cases,
    get_base_url,
    get_api_path,
    get_common_headers,
    get_selected_indices,
    get_api_doc,
)
from utils.logger import get_logger

_logger = get_logger("ui.test_script_page")


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        
        self._formats = {}
        
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.GlobalColor.darkBlue)
        keyword_format.setFontWeight(QFont.Weight.Bold)
        self._formats["keyword"] = keyword_format
        
        string_format = QTextCharFormat()
        string_format.setForeground(Qt.GlobalColor.darkGreen)
        self._formats["string"] = string_format
        
        comment_format = QTextCharFormat()
        comment_format.setForeground(Qt.GlobalColor.gray)
        self._formats["comment"] = comment_format
        
        function_format = QTextCharFormat()
        function_format.setForeground(Qt.GlobalColor.darkMagenta)
        self._formats["function"] = function_format
        
        number_format = QTextCharFormat()
        number_format.setForeground(Qt.GlobalColor.darkRed)
        self._formats["number"] = number_format
        
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(Qt.GlobalColor.darkYellow)
        self._formats["decorator"] = decorator_format
        
        self._rules = [
            (r"\b(def|class|if|elif|else|for|while|try|except|finally|with|as|import|from|return|yield|raise|break|continue|pass|lambda|and|or|not|in|is|None|True|False)\b", "keyword"),
            (r'"[^"\\]*(\\.[^"\\]*)*"|\'[^\'\\]*(\\.[^\'\\]*)*\'', "string"),
            (r"#.*$", "comment"),
            (r"\bdef\s+(\w+)", "function"),
            (r"\bclass\s+(\w+)", "function"),
            (r"\b\d+\.?\d*\b", "number"),
            (r"@\w+", "decorator"),
        ]
    
    def highlightBlock(self, text: str) -> None:
        for pattern, format_key in self._rules:
            for match in re.finditer(pattern, text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, self._formats[format_key])


class ScriptGenerateThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        ai_model: AIModel,
        test_cases: list,
        base_url: str,
        api_path: str,
        common_headers: str,
        api_doc: str,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._ai_model = ai_model
        self._test_cases = test_cases
        self._base_url = base_url
        self._api_path = api_path
        self._common_headers = common_headers
        self._api_doc = api_doc
    
    def run(self) -> None:
        try:
            self.progress.emit("正在初始化 AI 模型...")
            
            config = AIModelConfig(
                name=self._ai_model.name,
                api_base_url=self._ai_model.api_base,
                api_key=self._ai_model.api_key,
                model_name=self._ai_model.model_name,
                timeout=300.0,
            )
            
            client = AIClient(config)
            
            self.progress.emit("正在分析测试用例...")
            
            system_prompt = """你是一个专业的Python测试工程师。你的任务是根据用户提供的接口文档和测试用例生成pytest测试脚本。

请严格遵循以下要求：

## 基本要求
1. 使用pytest框架编写测试脚本
2. 使用httpx库发送HTTP请求
3. 代码要符合PEP8规范

## Allure框架要求（必须）
每个测试函数都要添加allure注解：
- @allure.feature("模块名称")
- @allure.story("功能点")
- @allure.title("测试用例标题")
- @allure.severity(allure.severity_level.NORMAL/CRITICAL/MINOR)
- 使用 allure.step("步骤描述") 标记测试步骤
- 使用 allure.attach() 附加请求和响应数据

## 重要：测试函数生成规则
**必须为每个测试用例生成一个独立的测试函数！**
- 如果有10个测试用例，就必须生成10个测试函数
- 每个测试函数名称要能体现测试场景，如：test_register_success, test_register_missing_username
- 不要合并或省略任何测试用例
- 测试函数命名规则：test_<接口名>_<场景描述>

## 【严格】断言生成规则（必须遵守）
1. **HTTP状态码断言（强制）**：每个测试函数必须包含对expected_status的状态码断言
   - 格式：assert response.status_code == {expected_status}, f"预期状态码 {expected_status}，实际状态码 {response.status_code}"
   
2. **断言数量严格限制**：
   - 如果assertions字段为空或空白：只生成HTTP状态码断言，不要添加任何其他断言
   - 如果assertions字段有内容：只根据assertions中的描述生成对应断言，**严禁发散或扩展额外的断言**
   - 例如：用户写了1条断言，脚本里就只能有1条（加上状态码断言共2条）
   
3. **禁止发散行为**：
   - 不要根据接口文档"推测"应该验证什么
   - 不要自动添加字段存在性检查、类型检查等额外断言
   - 严格按照assertions字段的字面意思生成断言代码
   
4. **自然语言断言转换**：
   - 将自然语言描述转换为准确的Python断言代码
   - 保持原意，不要扩展含义

## 其他要求
5. 添加适当的注释和文档字符串
6. 使用fixture管理测试数据
7. 使用提供的BASE_URL + API_PATH作为完整请求地址
8. 在请求头中添加提供的公共请求头
9. 根据接口文档理解接口的业务逻辑和参数含义
10. 根据自然语言描述的请求参数、请求体生成对应的代码

请直接输出Python代码，用```python包裹。开头需要导入：
import pytest
import allure
import httpx
import json"""

            cases_data = []
            for case in self._test_cases:
                cases_data.append({
                    "name": case.name,
                    "method": case.method,
                    "params": case.params,
                    "body": case.body,
                    "expected_status": case.expected_status,
                    "assertions": case.assertions,
                })
            
            cases_json = json.dumps(cases_data, ensure_ascii=False, indent=2)
            headers_text = self._common_headers if self._common_headers else "无"
            
            user_message = f"""以下是接口文档和测试配置：

## 接口文档
{self._api_doc}

## 测试配置
- BASE_URL: {self._base_url}
- API_PATH: {self._api_path}
- 完整URL: {self._base_url}{self._api_path}
- 公共请求头: {headers_text}

## 测试用例
{cases_json}

请根据以上接口文档和测试用例生成pytest+allure测试脚本。

## 重要提醒
1. **HTTP状态码断言必须生成**：每个用例都要验证 expected_status 字段指定的状态码
2. **断言严格匹配**：
   - assertions字段为空时：只判断状态码，不要生成其他断言
   - assertions字段有内容时：严格按照描述生成，不要发散扩展
3. params、body字段可能是自然语言描述，请根据描述生成对应的代码
4. 每个测试用例都要有完整的allure注解
5. 使用allure.step标记测试步骤
6. 附加请求和响应信息到allure报告"""

            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_message),
            ]
            
            self.progress.emit("正在生成测试脚本...")
            
            response = client.chat(messages, temperature=0.3, max_tokens=16384)
            
            content = response["choices"][0]["message"]["content"]
            
            script_content = self._extract_code(content)
            
            client.close()
            
            self.progress.emit("测试脚本生成完成!")
            self.finished.emit(script_content)
            
        except Exception as e:
            self.error.emit(f"生成失败: {str(e)}")
    
    def _extract_code(self, content: str) -> str:
        if "```python" in content:
            start = content.find("```python") + 9
            end = content.find("```", start)
            return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            return content[start:end].strip()
        return content


class CodeFixThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        ai_model: AIModel,
        code: str,
        error_messages: list[str],
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._ai_model = ai_model
        self._code = code
        self._error_messages = error_messages

    def run(self) -> None:
        try:
            self.progress.emit("正在初始化 AI 模型...")

            config = AIModelConfig(
                name=self._ai_model.name,
                api_base_url=self._ai_model.api_base,
                api_key=self._ai_model.api_key,
                model_name=self._ai_model.model_name,
                timeout=120.0,
            )

            client = AIClient(config)

            self.progress.emit("正在分析代码问题...")

            system_prompt = """你是一个专业的Python代码修复专家。你的任务是修复有问题的Python测试代码。

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

            error_text = "\n".join(f"- {err}" for err in self._error_messages)

            user_message = f"""请修复以下Python测试代码中的错误。

## 原始代码
```python
{self._code}
```

## 检测到的问题
{error_text}

请修复这些问题并输出完整的修正后的代码。"""

            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_message),
            ]

            self.progress.emit("正在修复代码...")

            response = client.chat(messages, temperature=0.3, max_tokens=16384)

            content = response["choices"][0]["message"]["content"]

            fixed_code = self._extract_code(content)

            client.close()

            self.progress.emit("代码修复完成!")
            self.finished.emit(fixed_code)

        except Exception as e:
            self.error.emit(f"修复失败: {str(e)}")

    def _extract_code(self, content: str) -> str:
        if "```python" in content:
            start = content.find("```python") + 9
            end = content.find("```", start)
            return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            return content[start:end].strip()
        return content


class TestScriptPage(BasePage):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("生成测试脚本", parent)
        self._generate_thread: Optional[ScriptGenerateThread] = None
        self._fix_thread: Optional[CodeFixThread] = None
        self._generated_script: str = ""
        self._validation_result = None
        self._current_ai_model: Optional[AIModel] = None
        self._init_content()
        self._load_ai_models()
    
    def _init_content(self) -> None:
        info_group = QGroupBox("测试配置信息")
        info_layout = QVBoxLayout(info_group)
        
        info_row = QHBoxLayout()
        self._info_label = QLabel("当前共有 0 条测试用例")
        self._info_label.setStyleSheet("font-size: 14px; color: #333;")
        info_row.addWidget(self._info_label)
        info_row.addStretch()
        info_layout.addLayout(info_row)
        
        self._config_label = QLabel("")
        self._config_label.setStyleSheet("font-size: 12px; color: #666;")
        info_layout.addWidget(self._config_label)
        
        info_btn_layout = QHBoxLayout()
        self._view_cases_btn = QPushButton("查看测试用例")
        self._view_cases_btn.clicked.connect(self._go_to_test_cases)
        style_manager.apply_style(self._view_cases_btn, "button_secondary")
        info_btn_layout.addWidget(self._view_cases_btn)
        info_btn_layout.addStretch()
        info_layout.addLayout(info_btn_layout)
        
        style_manager.apply_style(info_group, "group_box")
        self.add_widget(info_group)
        
        model_group = QGroupBox("AI 模型选择")
        model_layout = QHBoxLayout(model_group)
        
        self._model_combo = QComboBox()
        self._model_combo.setPlaceholderText("请选择 AI 模型")
        style_manager.apply_style(self._model_combo, "combobox")
        model_layout.addWidget(self._model_combo)
        
        self._generate_btn = QPushButton("生成测试脚本")
        self._generate_btn.clicked.connect(self._generate_script)
        style_manager.apply_style(self._generate_btn, "button_primary")
        model_layout.addWidget(self._generate_btn)
        
        style_manager.apply_style(model_group, "group_box")
        self.add_widget(model_group)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)
        style_manager.apply_style(self._progress_bar, "progress_bar")
        self.add_widget(self._progress_bar)
        
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #757575;")
        self.add_widget(self._status_label)
        
        preview_group = QGroupBox("生成的测试脚本")
        preview_layout = QVBoxLayout(preview_group)

        self._validation_label = QLabel("")
        self._validation_label.setStyleSheet("font-size: 12px; padding: 5px; border-radius: 3px;")
        self._validation_label.setVisible(False)
        preview_layout.addWidget(self._validation_label)

        self._script_preview = QTextEdit()
        self._script_preview.setReadOnly(False)
        self._script_preview.setPlaceholderText("生成的测试脚本将在此显示...")
        self._script_preview.setFont(QFont("Consolas", 10))
        self._highlighter = PythonHighlighter(self._script_preview.document())
        style_manager.apply_style(self._script_preview, "input")
        preview_layout.addWidget(self._script_preview)

        save_layout = QHBoxLayout()
        self._validate_btn = QPushButton("验证代码")
        self._validate_btn.clicked.connect(self._validate_script)
        self._validate_btn.setEnabled(False)
        style_manager.apply_style(self._validate_btn, "button_secondary")
        save_layout.addWidget(self._validate_btn)

        self._ai_fix_btn = QPushButton("AI修复代码")
        self._ai_fix_btn.clicked.connect(self._ai_fix_script)
        self._ai_fix_btn.setEnabled(False)
        style_manager.apply_style(self._ai_fix_btn, "button_secondary")
        save_layout.addWidget(self._ai_fix_btn)

        self._save_file_btn = QPushButton("保存为文件")
        self._save_file_btn.clicked.connect(self._save_to_file)
        self._save_file_btn.setEnabled(False)
        style_manager.apply_style(self._save_file_btn, "button_primary")
        save_layout.addWidget(self._save_file_btn)

        self._copy_btn = QPushButton("复制到剪贴板")
        self._copy_btn.clicked.connect(self._copy_script)
        self._copy_btn.setEnabled(False)
        style_manager.apply_style(self._copy_btn, "button_secondary")
        save_layout.addWidget(self._copy_btn)

        self._help_btn = QPushButton("执行帮助")
        self._help_btn.clicked.connect(self._show_execution_help)
        style_manager.apply_style(self._help_btn, "button_secondary")
        save_layout.addWidget(self._help_btn)

        save_layout.addStretch()
        preview_layout.addLayout(save_layout)

        style_manager.apply_style(preview_group, "group_box")
        self.add_widget(preview_group)

    def _show_execution_help(self) -> None:
        help_text = """<h3>测试脚本执行指南</h3>
<p>保存测试脚本后，您可以通过以下命令执行测试并生成Allure报告：</p>

<h4>1. 执行测试并生成Allure结果</h4>
<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
pytest test_api.py --alluredir=allure-results
</pre>

<h4>2. 生成Allure静态报告</h4>
<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
allure generate allure-results --clean -o allure-report
</pre>

<h4>3. 查看报告</h4>
<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
allure open allure-report
</pre>

<h4>常用参数</h4>
<ul>
<li><code>-v</code> : 详细输出模式</li>
<li><code>-s</code> : 显示print输出</li>
<li><code>-k "关键字"</code> : 只运行包含关键字的测试</li>
<li><code>--markers</code> : 运行指定标记的测试</li>
<li><code>--html=report.html</code> : 生成HTML报告（需安装pytest-html）</li>
</ul>

<h4>前置条件</h4>
<ul>
<li>已安装 pytest: <code>pip install pytest</code></li>
<li>已安装 allure-pytest: <code>pip install allure-pytest</code></li>
<li>已安装 Allure 命令行工具（用于生成和查看报告）</li>
</ul>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("执行帮助")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setStyleSheet("""
            QMessageBox {
                min-width: 500px;
            }
            QMessageBox QLabel {
                min-width: 480px;
                font-size: 13px;
            }
        """)
        msg.exec()
    
    def _load_ai_models(self) -> None:
        self._model_combo.clear()
        models = AIModel.get_all()
        
        for model in models:
            default_marker = " (默认)" if model.is_default else ""
            self._model_combo.addItem(f"{model.name}{default_marker}", model.id)
        
        default_model = AIModel.get_default()
        if default_model:
            index = self._model_combo.findData(default_model.id)
            if index >= 0:
                self._model_combo.setCurrentIndex(index)
    
    def _go_to_test_cases(self) -> None:
        from ui.main_window import MainWindow
        window = self.window()
        if isinstance(window, MainWindow):
            window._nav_list.setCurrentRow(2)
    
    def _generate_script(self) -> None:
        all_test_cases = get_test_cases()
        selected_indices = get_selected_indices()
        
        if selected_indices:
            test_cases = [all_test_cases[i] for i in selected_indices if i < len(all_test_cases)]
        else:
            test_cases = all_test_cases
        
        if not test_cases:
            QMessageBox.warning(self, "提示", "请先在「测试用例」页面生成或添加测试用例")
            return
        
        base_url = get_base_url()
        if not base_url:
            QMessageBox.warning(self, "提示", "请先在「测试用例」页面配置 Base URL")
            return
        
        api_path = get_api_path()
        if not api_path:
            QMessageBox.warning(self, "提示", "请先在「测试用例」页面配置接口路径")
            return
        
        api_doc = get_api_doc()
        if not api_doc:
            QMessageBox.warning(self, "提示", "请先在「测试用例」页面输入接口文档")
            return
        
        common_headers = get_common_headers()
        
        model_id = self._model_combo.currentData()
        if not model_id:
            QMessageBox.warning(self, "提示", "请选择 AI 模型")
            return
        
        ai_model = AIModel.get_by_id(model_id)
        if not ai_model:
            QMessageBox.warning(self, "提示", "AI 模型不存在")
            return

        self._current_ai_model = ai_model

        _logger.info(f"开始生成测试脚本: model={ai_model.name}, test_cases={len(test_cases)}, url={base_url}{api_path}")
        
        self._generate_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._status_label.setText("正在生成测试脚本...")
        
        self._generate_thread = ScriptGenerateThread(
            ai_model=ai_model,
            test_cases=test_cases,
            base_url=base_url,
            api_path=api_path,
            common_headers=common_headers,
            api_doc=api_doc,
        )
        self._generate_thread.progress.connect(self._on_progress)
        self._generate_thread.finished.connect(self._on_finished)
        self._generate_thread.error.connect(self._on_error)
        self._generate_thread.start()
    
    def _on_progress(self, message: str) -> None:
        self._status_label.setText(message)
        _logger.debug(f"脚本生成进度: {message}")
    
    def _on_finished(self, script_content: str) -> None:
        self._generate_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText("测试脚本生成完成")

        _logger.info(f"测试脚本生成完成: length={len(script_content)}")

        self._generated_script = script_content
        self._script_preview.setText(script_content)
        self._save_file_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)
        self._validate_btn.setEnabled(True)
        self._ai_fix_btn.setEnabled(False)

        self._validate_and_display(script_content)

    def _validate_script(self) -> None:
        code = self._script_preview.toPlainText()
        if not code:
            QMessageBox.warning(self, "提示", "没有可验证的代码")
            return

        _logger.info("用户手动触发代码验证")
        self._validate_and_display(code)

    def _validate_and_display(self, code: str) -> None:
        _logger.debug(f"开始验证代码, 长度: {len(code)} 字符")
        result = CodeValidator.validate_and_fix(code)
        self._validation_result = result

        self._validation_label.setVisible(True)

        error_count = len(result.errors)
        warning_count = len(result.warnings)
        _logger.info(f"验证结果: 错误={error_count}, 警告={warning_count}, 通过={result.valid}")

        if result.valid:
            if warning_count > 0:
                self._validation_label.setText(f"✓ 代码验证通过（有 {warning_count} 个警告）")
                self._validation_label.setStyleSheet(
                    "font-size: 12px; padding: 5px; border-radius: 3px; "
                    "background-color: #fff3e0; color: #e65100;"
                )
            else:
                self._validation_label.setText("✓ 代码验证通过")
                self._validation_label.setStyleSheet(
                    "font-size: 12px; padding: 5px; border-radius: 3px; "
                    "background-color: #e8f5e9; color: #2e7d32;"
                )
            self._ai_fix_btn.setEnabled(False)
        else:
            error_msg = ""
            if result.errors:
                error_msg = "\n".join(str(e) for e in result.errors[:3])
                if len(result.errors) > 3:
                    error_msg += f"\n... 还有 {len(result.errors) - 3} 个错误"

            self._validation_label.setText(f"✗ 发现 {error_count} 个错误, {warning_count} 个警告\n{error_msg}")
            self._validation_label.setStyleSheet(
                "font-size: 12px; padding: 5px; border-radius: 3px; "
                "background-color: #ffebee; color: #c62828;"
            )

            has_ai_model = self._current_ai_model is not None
            self._ai_fix_btn.setEnabled(has_ai_model)

            if result.fixed_code:
                reply = QMessageBox.question(
                    self,
                    "自动修正",
                    f"检测到 {error_count} 个问题，是否应用自动修正？\n\n"
                    f"主要问题:\n{error_msg}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    _logger.info("用户选择应用自动修正")
                    self._script_preview.setText(result.fixed_code)
                    self._generated_script = result.fixed_code
                    self._validate_and_display(result.fixed_code)

    def _ai_fix_script(self) -> None:
        code = self._script_preview.toPlainText()
        if not code:
            QMessageBox.warning(self, "提示", "没有可修复的代码")
            return

        if not self._validation_result or not self._validation_result.errors:
            QMessageBox.information(self, "提示", "代码没有检测到错误，无需修复")
            return

        if not self._current_ai_model:
            QMessageBox.warning(self, "提示", "请先选择 AI 模型")
            return

        error_messages = [str(e) for e in self._validation_result.errors]
        _logger.info(f"用户触发AI修复, 模型: {self._current_ai_model.name}, 错误数: {len(error_messages)}")

        reply = QMessageBox.question(
            self,
            "AI修复确认",
            f"将使用 {self._current_ai_model.name} 修复代码中的 {len(error_messages)} 个错误。\n\n"
            "注意：这会调用AI API，可能需要一些时间。\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            _logger.debug("用户取消AI修复")
            return

        _logger.info(f"开始AI修复, 代码长度: {len(code)} 字符")
        self._ai_fix_btn.setEnabled(False)
        self._validate_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._status_label.setText("正在使用AI修复代码...")

        self._fix_thread = CodeFixThread(
            ai_model=self._current_ai_model,
            code=code,
            error_messages=error_messages,
        )
        self._fix_thread.progress.connect(self._on_fix_progress)
        self._fix_thread.finished.connect(self._on_fix_finished)
        self._fix_thread.error.connect(self._on_fix_error)
        self._fix_thread.start()

    def _on_fix_progress(self, message: str) -> None:
        _logger.debug(f"AI修复进度: {message}")
        self._status_label.setText(message)

    def _on_fix_finished(self, fixed_code: str) -> None:
        self._progress_bar.setVisible(False)
        self._validate_btn.setEnabled(True)
        self._status_label.setText("AI修复完成")

        if fixed_code:
            _logger.info(f"AI修复成功, 修复后代码长度: {len(fixed_code)} 字符")
            self._script_preview.setText(fixed_code)
            self._generated_script = fixed_code
            QMessageBox.information(self, "成功", "代码已修复，正在重新验证...")
            self._validate_and_display(fixed_code)
        else:
            _logger.warning("AI未能生成修复后的代码")
            QMessageBox.warning(self, "提示", "AI未能生成修复后的代码")

    def _on_fix_error(self, error_message: str) -> None:
        self._progress_bar.setVisible(False)
        self._validate_btn.setEnabled(True)
        self._status_label.setText("AI修复失败")
        _logger.error(f"AI修复失败: {error_message}")
        QMessageBox.critical(self, "错误", error_message)
    
    def _on_error(self, error_message: str) -> None:
        self._generate_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText("生成失败")
        _logger.error(f"测试脚本生成失败: {error_message}")
        QMessageBox.critical(self, "错误", error_message)
    
    def _save_to_file(self) -> None:
        code = self._script_preview.toPlainText()
        if not code:
            QMessageBox.warning(self, "提示", "没有可保存的脚本")
            return

        if not self._validation_result:
            self._validate_and_display(code)

        if self._validation_result and not self._validation_result.valid:
            reply = QMessageBox.warning(
                self,
                "代码存在问题",
                f"代码验证发现 {len(self._validation_result.errors)} 个错误，是否仍要保存？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        import os
        from pathlib import Path

        default_dir = Path.home()
        if not default_dir.exists():
            default_dir = Path(".")

        default_path = str(default_dir / "test_api.py")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存测试脚本",
            default_path,
            "Python Files (*.py);;All Files (*)"
        )

        if file_path:
            try:
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)
                QMessageBox.information(self, "成功", f"脚本已保存到: {file_path}")
            except PermissionError:
                QMessageBox.critical(self, "错误", f"权限不足，无法保存到: {file_path}\n请选择其他目录或以管理员身份运行")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def _copy_script(self) -> None:
        from PyQt6.QtWidgets import QApplication
        code = self._script_preview.toPlainText()
        if not code:
            QMessageBox.warning(self, "提示", "没有可复制的脚本")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(code)
        QMessageBox.information(self, "成功", "脚本已复制到剪贴板")
    
    def refresh(self) -> None:
        self._load_ai_models()
        all_test_cases = get_test_cases()
        selected_indices = get_selected_indices()
        base_url = get_base_url()
        api_path = get_api_path()
        common_headers = get_common_headers()
        
        if selected_indices:
            selected_count = len([i for i in selected_indices if i < len(all_test_cases)])
            self._info_label.setText(f"已选中 {selected_count} 条测试用例（共 {len(all_test_cases)} 条）")
        else:
            self._info_label.setText(f"当前共有 {len(all_test_cases)} 条测试用例")
        
        config_parts = []
        if base_url and api_path:
            config_parts.append(f"URL: {base_url}{api_path}")
        elif base_url:
            config_parts.append(f"Base URL: {base_url}")
        elif api_path:
            config_parts.append(f"API路径: {api_path}")
        
        if common_headers:
            config_parts.append(f"请求头: {len(common_headers)} 项")
        
        self._config_label.setText(" | ".join(config_parts) if config_parts else "请在测试用例页面配置接口信息")
