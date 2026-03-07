import json
import re
from typing import Optional
from dataclasses import dataclass, field, asdict

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QComboBox,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QLineEdit,
    QDialog,
    QCheckBox,
)

from models.ai_model import AIModel
from ai.client import AIClient, AIModelConfig, ChatMessage, MessageRole
from ui.styles import style_manager
from ui.pages.base_page import BasePage
from utils.logger import get_logger

_logger = get_logger("ui.test_case_page")


@dataclass
class TestCaseData:
    name: str = ""
    method: str = "GET"
    params: str = ""
    body: str = ""
    expected_status: int = 200
    assertions: str = ""
    
    def to_dict(self) -> dict:
        result = asdict(self)
        try:
            if self.params.strip():
                result["params"] = json.loads(self.params)
            else:
                result["params"] = {}
        except:
            result["params"] = {}
        
        try:
            if self.body.strip():
                result["body"] = json.loads(self.body)
            else:
                result["body"] = {}
        except:
            result["body"] = {}
        
        return result


class TextEditDialog(QDialog):
    def __init__(self, title: str, content: str, placeholder: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 350)
        self._result = content
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        self._text_edit = QTextEdit()
        self._text_edit.setPlainText(content)
        self._text_edit.setPlaceholderText(placeholder)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                background: #fafafa;
            }
        """)
        layout.addWidget(self._text_edit)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        style_manager.apply_style(cancel_btn, "button_secondary")
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self._on_ok)
        style_manager.apply_style(ok_btn, "button_primary")
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_ok(self) -> None:
        self._result = self._text_edit.toPlainText()
        self.accept()
    
    def get_result(self) -> str:
        return self._result


class GenerateThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list, str, str)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        ai_model: AIModel,
        doc_content: str,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._ai_model = ai_model
        self._doc_content = doc_content
    
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
            
            self.progress.emit("正在分析接口文档...")
            
            system_prompt = """你是一个专业的API测试工程师。你的任务是根据用户提供的API接口文档生成测试用例。

请按照以下JSON格式输出测试用例列表：
```json
{
    "base_url": "http://api.example.com:8080",
    "api_path": "/api/v1/users",
    "test_cases": [
        {
            "name": "测试用例名称",
            "method": "GET/POST/PUT/DELETE",
            "params": "page=1&size=10 或 JSON格式",
            "body": "请求体JSON字符串",
            "expected_status": 200,
            "assertions": "断言描述，如：响应状态码为200，data.list长度大于0，msg等于成功"
        }
    ]
}
```

请确保：
1. 从文档中提取 base_url（包含协议、IP、端口），如果没有找到则设为空字符串
2. 从文档中提取 api_path（接口路径），如果没有找到则设为空字符串
3. 为该接口生成多个测试场景（正常、异常、边界值等）
4. params 和 body 使用自然语言或JSON格式描述
5. assertions 使用自然语言描述断言条件
6. 只输出JSON，不要包含其他说明文字"""
            
            user_message = f"以下是API接口文档：\n\n{self._doc_content}\n\n请根据以上接口文档生成测试用例。"
            
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_message),
            ]
            
            self.progress.emit("正在生成测试用例...")
            
            response = client.chat(messages, temperature=0.7, max_tokens=16384)
            
            content = response["choices"][0]["message"]["content"]
            
            test_cases, base_url, api_path = self._parse_response(content)
            
            client.close()
            
            self.progress.emit("测试用例生成完成!")
            self.finished.emit(test_cases, base_url, api_path)
            
        except Exception as e:
            self.error.emit(f"生成失败: {str(e)}")
    
    def _parse_response(self, content: str) -> tuple[list[dict], str, str]:
        json_str = content
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        
        data = json.loads(json_str)
        
        if isinstance(data, list):
            return data, "", ""
        
        base_url = data.get("base_url", "")
        api_path = data.get("api_path", "")
        test_cases = data.get("test_cases", [])
        
        if not isinstance(test_cases, list):
            test_cases = [test_cases]
        
        return test_cases, base_url, api_path


_test_cases_store: list[TestCaseData] = []
_base_url_store: str = ""
_api_path_store: str = ""
_common_headers_store: dict = {}
_selected_indices_store: list[int] = []
_api_doc_store: str = ""


def get_test_cases() -> list[TestCaseData]:
    return _test_cases_store


def set_test_cases(cases: list[TestCaseData]) -> None:
    global _test_cases_store
    _test_cases_store = cases


def get_base_url() -> str:
    return _base_url_store


def set_base_url(url: str) -> None:
    global _base_url_store
    _base_url_store = url


def get_api_path() -> str:
    return _api_path_store


def set_api_path(path: str) -> None:
    global _api_path_store
    _api_path_store = path


def get_common_headers() -> dict:
    return _common_headers_store


def set_common_headers(headers: dict) -> None:
    global _common_headers_store
    _common_headers_store = headers


def get_selected_indices() -> list[int]:
    return _selected_indices_store


def set_selected_indices(indices: list[int]) -> None:
    global _selected_indices_store
    _selected_indices_store = indices


def get_api_doc() -> str:
    return _api_doc_store


def set_api_doc(doc: str) -> None:
    global _api_doc_store
    _api_doc_store = doc


HTTP_STATUS_CODES = {
    "200": "200 OK - 请求成功",
    "201": "201 Created - 创建成功",
    "204": "204 No Content - 无内容",
    "400": "400 Bad Request - 请求参数错误",
    "401": "401 Unauthorized - 未授权",
    "403": "403 Forbidden - 禁止访问",
    "404": "404 Not Found - 资源不存在",
    "500": "500 Internal Server Error - 服务器错误",
    "502": "502 Bad Gateway - 网关错误",
    "503": "503 Service Unavailable - 服务不可用",
}


class TestCasePage(BasePage):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("测试用例", parent)
        self._generate_thread: Optional[GenerateThread] = None
        self._init_content()
        self._load_ai_models()
    
    def _init_content(self) -> None:
        config_group = QGroupBox("接口配置")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(6)
        
        row1 = QHBoxLayout()
        base_url_label = QLabel("Base URL:")
        base_url_label.setFixedWidth(70)
        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText("例如: http://192.168.1.100:8080")
        style_manager.apply_style(self._base_url_edit, "input")
        row1.addWidget(base_url_label)
        row1.addWidget(self._base_url_edit)
        config_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        api_path_label = QLabel("接口路径:")
        api_path_label.setFixedWidth(70)
        self._api_path_edit = QLineEdit()
        self._api_path_edit.setPlaceholderText("例如: /api/v1/users")
        style_manager.apply_style(self._api_path_edit, "input")
        row2.addWidget(api_path_label)
        row2.addWidget(self._api_path_edit)
        config_layout.addLayout(row2)
        
        row3 = QHBoxLayout()
        headers_label = QLabel("请求头:")
        headers_label.setFixedWidth(70)
        self._headers_edit = QLineEdit()
        self._headers_edit.setPlaceholderText('例如: {"Authorization": "Bearer token123"}')
        style_manager.apply_style(self._headers_edit, "input")
        self._headers_edit.textChanged.connect(self._save_config)
        row3.addWidget(headers_label)
        row3.addWidget(self._headers_edit)
        config_layout.addLayout(row3)
        
        style_manager.apply_style(config_group, "group_box")
        self.add_widget(config_group)
        
        input_group = QGroupBox("接口文档")
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(6)
        
        input_header = QHBoxLayout()
        self._upload_btn = QPushButton("上传文件")
        self._upload_btn.clicked.connect(self._upload_file)
        style_manager.apply_style(self._upload_btn, "button_secondary")
        input_header.addWidget(self._upload_btn)
        
        self._clear_btn = QPushButton("清空")
        self._clear_btn.clicked.connect(self._clear_input)
        style_manager.apply_style(self._clear_btn, "button_secondary")
        input_header.addWidget(self._clear_btn)
        
        input_header.addStretch()
        
        model_label = QLabel("AI模型:")
        input_header.addWidget(model_label)
        
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(150)
        style_manager.apply_style(self._model_combo, "combobox")
        input_header.addWidget(self._model_combo)
        
        self._generate_btn = QPushButton("生成测试用例")
        self._generate_btn.clicked.connect(self._generate_test_cases)
        style_manager.apply_style(self._generate_btn, "button_primary")
        input_header.addWidget(self._generate_btn)
        
        input_layout.addLayout(input_header)
        
        self._doc_input = QTextEdit()
        self._doc_input.setMaximumHeight(100)
        self._doc_input.setPlaceholderText(
            "请在此输入接口文档内容，或上传 Markdown 文件..."
        )
        style_manager.apply_style(self._doc_input, "input")
        input_layout.addWidget(self._doc_input)
        
        progress_layout = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)
        self._progress_bar.setFixedHeight(18)
        style_manager.apply_style(self._progress_bar, "progress_bar")
        progress_layout.addWidget(self._progress_bar)
        
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #757575;")
        progress_layout.addWidget(self._status_label)
        progress_layout.addStretch()
        input_layout.addLayout(progress_layout)
        
        style_manager.apply_style(input_group, "group_box")
        self.add_widget(input_group)
        
        table_group = QGroupBox("测试用例列表")
        table_layout = QVBoxLayout(table_group)
        
        table_btn_layout = QHBoxLayout()
        
        self._select_all_cb = QCheckBox("全选")
        self._select_all_cb.stateChanged.connect(self._on_select_all)
        table_btn_layout.addWidget(self._select_all_cb)
        
        self._add_row_btn = QPushButton("添加行")
        self._add_row_btn.clicked.connect(self._add_row)
        style_manager.apply_style(self._add_row_btn, "button_secondary")
        table_btn_layout.addWidget(self._add_row_btn)
        
        self._delete_row_btn = QPushButton("删除勾选")
        self._delete_row_btn.clicked.connect(self._delete_selected_rows)
        style_manager.apply_style(self._delete_row_btn, "button_secondary")
        table_btn_layout.addWidget(self._delete_row_btn)
        
        self._clear_table_btn = QPushButton("清空表格")
        self._clear_table_btn.clicked.connect(self._clear_table)
        style_manager.apply_style(self._clear_table_btn, "button_secondary")
        table_btn_layout.addWidget(self._clear_table_btn)
        
        table_btn_layout.addStretch()
        
        self._count_label = QLabel("共 0 条")
        self._count_label.setStyleSheet("color: #666;")
        table_btn_layout.addWidget(self._count_label)
        
        self._generate_script_btn = QPushButton("去生成脚本")
        self._generate_script_btn.clicked.connect(self._go_to_script_page)
        style_manager.apply_style(self._generate_script_btn, "button_primary")
        table_btn_layout.addWidget(self._generate_script_btn)
        
        table_layout.addLayout(table_btn_layout)
        
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["勾选", "用例名称", "方法", "请求参数", "请求体", "HTTP状态码", "断言"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(5, 120)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setDefaultSectionSize(30)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        style_manager.apply_style(self._table, "table")
        table_layout.addWidget(self._table)
        
        style_manager.apply_style(table_group, "group_box")
        self.add_widget(table_group)
    
    def _on_select_all(self, state: int) -> None:
        checked = state == Qt.CheckState.Checked.value
        for row in range(self._table.rowCount()):
            checkbox = self._table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)
    
    def _get_checked_rows(self) -> list[int]:
        checked_rows = []
        for row in range(self._table.rowCount()):
            checkbox = self._table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                checked_rows.append(row)
        return checked_rows
    
    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        if column == 3:
            current_text = self._table.item(row, column).text() if self._table.item(row, column) else ""
            dialog = TextEditDialog(
                "编辑请求参数",
                current_text,
                "请输入请求参数，支持自然语言或JSON格式：\n\n"
                "示例1（自然语言）：page=1, size=10, name包含'张三'\n\n"
                "示例2（JSON）：{\"page\": 1, \"size\": 10}",
                self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._table.setItem(row, column, QTableWidgetItem(dialog.get_result()))
                self._save_to_store()
        
        elif column == 4:
            current_text = self._table.item(row, column).text() if self._table.item(row, column) else ""
            dialog = TextEditDialog(
                "编辑请求体",
                current_text,
                "请输入请求体，支持自然语言或JSON格式：\n\n"
                "示例1（自然语言）：用户名为test，密码为123456\n\n"
                "示例2（JSON）：{\"username\": \"test\", \"password\": \"123456\"}",
                self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._table.setItem(row, column, QTableWidgetItem(dialog.get_result()))
                self._save_to_store()
        
        elif column == 6:
            current_text = self._table.item(row, column).text() if self._table.item(row, column) else ""
            dialog = TextEditDialog(
                "编辑断言",
                current_text,
                "请输入断言条件（自然语言）：\n\n"
                "示例：\n"
                "- 响应状态码为200\n"
                "- data.list长度大于0\n"
                "- msg等于'成功'\n"
                "- code为0",
                self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._table.setItem(row, column, QTableWidgetItem(dialog.get_result()))
                self._save_to_store()
    
    def _go_to_script_page(self) -> None:
        checked_rows = self._get_checked_rows()
        if checked_rows:
            set_selected_indices(checked_rows)
        else:
            set_selected_indices(list(range(self._table.rowCount())))
        
        from ui.main_window import MainWindow
        window = self.window()
        if isinstance(window, MainWindow):
            window._nav_list.setCurrentRow(2)
    
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
    
    def _upload_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Markdown 文件",
            "",
            "Markdown Files (*.md);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._doc_input.setText(content)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取文件失败: {str(e)}")
    
    def _clear_input(self) -> None:
        self._doc_input.clear()
        self._status_label.clear()
    
    def _save_config(self) -> None:
        set_base_url(self._base_url_edit.text().strip())
        set_api_path(self._api_path_edit.text().strip())
        try:
            headers_text = self._headers_edit.text().strip()
            if headers_text:
                headers = json.loads(headers_text)
                set_common_headers(headers)
            else:
                set_common_headers({})
        except json.JSONDecodeError:
            pass
    
    def _generate_test_cases(self) -> None:
        doc_content = self._doc_input.toPlainText().strip()
        if not doc_content:
            QMessageBox.warning(self, "提示", "请输入接口文档内容")
            return
        
        set_api_doc(doc_content)
        
        model_id = self._model_combo.currentData()
        if not model_id:
            QMessageBox.warning(self, "提示", "请选择 AI 模型")
            return
        
        ai_model = AIModel.get_by_id(model_id)
        if not ai_model:
            QMessageBox.warning(self, "提示", "AI 模型不存在")
            return
        
        _logger.info(f"开始生成测试用例: model={ai_model.name}, doc_length={len(doc_content)}")
        
        self._generate_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._status_label.setText("正在生成测试用例...")
        
        self._generate_thread = GenerateThread(
            ai_model=ai_model,
            doc_content=doc_content,
        )
        self._generate_thread.progress.connect(self._on_progress)
        self._generate_thread.finished.connect(self._on_finished)
        self._generate_thread.error.connect(self._on_error)
        self._generate_thread.start()
    
    def _on_progress(self, message: str) -> None:
        self._status_label.setText(message)
        _logger.debug(f"生成进度: {message}")
    
    def _on_finished(self, test_cases: list[dict], base_url: str, api_path: str) -> None:
        self._generate_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"成功生成 {len(test_cases)} 个测试用例")
        
        _logger.info(f"测试用例生成完成: count={len(test_cases)}, base_url={base_url}, api_path={api_path}")
        
        if base_url:
            self._base_url_edit.setText(base_url)
        if api_path:
            self._api_path_edit.setText(api_path)
        
        self._load_cases_to_table(test_cases)
        self._save_config()
    
    def _on_error(self, error_message: str) -> None:
        self._generate_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText("生成失败")
        _logger.error(f"测试用例生成失败: {error_message}")
        QMessageBox.critical(self, "错误", error_message)
    
    def _load_cases_to_table(self, cases: list[dict]) -> None:
        self._table.setRowCount(len(cases))
        
        for row, case_data in enumerate(cases):
            name = case_data.get("name", "")
            method = case_data.get("method", "GET")
            params = case_data.get("params", "")
            body = case_data.get("body", "")
            expected_status = case_data.get("expected_status", 200)
            assertions = case_data.get("assertions", "")
            
            checkbox = QCheckBox()
            checkbox.setStyleSheet("QCheckBox { margin-left: 15px; }")
            self._table.setCellWidget(row, 0, checkbox)
            
            self._table.setItem(row, 1, QTableWidgetItem(name))
            self._table.setItem(row, 2, QTableWidgetItem(method))
            self._table.setItem(row, 3, QTableWidgetItem(str(params) if params else ""))
            self._table.setItem(row, 4, QTableWidgetItem(str(body) if body else ""))
            
            status_combo = QComboBox()
            for code, desc in HTTP_STATUS_CODES.items():
                status_combo.addItem(desc, code)
            status_combo.setCurrentText(HTTP_STATUS_CODES.get(str(expected_status), str(expected_status)))
            status_combo.currentIndexChanged.connect(lambda _, r=row: self._on_status_changed(r))
            self._table.setCellWidget(row, 5, status_combo)
            
            self._table.setItem(row, 6, QTableWidgetItem(str(assertions) if assertions else ""))
        
        self._select_all_cb.setChecked(False)
        self._update_count()
        self._save_to_store()
    
    def _on_status_changed(self, row: int) -> None:
        self._save_to_store()
    
    def _add_row(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        
        checkbox = QCheckBox()
        checkbox.setStyleSheet("QCheckBox { margin-left: 15px; }")
        self._table.setCellWidget(row, 0, checkbox)
        
        self._table.setItem(row, 1, QTableWidgetItem(""))
        self._table.setItem(row, 2, QTableWidgetItem("GET"))
        self._table.setItem(row, 3, QTableWidgetItem(""))
        self._table.setItem(row, 4, QTableWidgetItem(""))
        
        status_combo = QComboBox()
        for code, desc in HTTP_STATUS_CODES.items():
            status_combo.addItem(desc, code)
        status_combo.setCurrentIndex(0)
        status_combo.currentIndexChanged.connect(lambda _, r=row: self._on_status_changed(r))
        self._table.setCellWidget(row, 5, status_combo)
        
        self._table.setItem(row, 6, QTableWidgetItem(""))
        self._update_count()
        self._save_to_store()
    
    def _delete_selected_rows(self) -> None:
        checked_rows = self._get_checked_rows()
        
        if not checked_rows:
            QMessageBox.warning(self, "提示", "请先勾选要删除的行")
            return
        
        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要删除选中的 {len(checked_rows)} 条测试用例吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for row in sorted(checked_rows, reverse=True):
                self._table.removeRow(row)
            
            self._select_all_cb.setChecked(False)
            self._update_count()
            self._save_to_store()
    
    def _clear_table(self) -> None:
        if self._table.rowCount() == 0:
            return
        
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清空所有测试用例吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._table.setRowCount(0)
            self._select_all_cb.setChecked(False)
            self._update_count()
            self._save_to_store()
    
    def _update_count(self) -> None:
        count = self._table.rowCount()
        self._count_label.setText(f"共 {count} 条")
    
    def _save_to_store(self) -> None:
        cases = []
        for row in range(self._table.rowCount()):
            status_widget = self._table.cellWidget(row, 5)
            status_code = status_widget.currentData() if status_widget else "200"
            
            case = TestCaseData(
                name=self._table.item(row, 1).text() if self._table.item(row, 1) else "",
                method=self._table.item(row, 2).text() if self._table.item(row, 2) else "GET",
                params=self._table.item(row, 3).text() if self._table.item(row, 3) else "",
                body=self._table.item(row, 4).text() if self._table.item(row, 4) else "",
                expected_status=int(status_code),
                assertions=self._table.item(row, 6).text() if self._table.item(row, 6) else "",
            )
            cases.append(case)
        
        set_test_cases(cases)
        self._save_config()
    
    def refresh(self) -> None:
        self._load_ai_models()
