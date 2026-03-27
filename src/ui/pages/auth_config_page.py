import json
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QLineEdit,
    QFormLayout,
    QCheckBox,
    QMessageBox,
    QTextEdit,
    QComboBox,
    QApplication,
    QScrollArea,
    QSizePolicy,
)

from models.auth_config import AuthConfig
from services.auth_service import AuthService
from ui.styles import style_manager
from ui.pages.base_page import BasePage
from utils.logger import get_logger

_logger = get_logger("ui.auth_config_page")


class AuthConfigDialog(QDialog):
    def __init__(self, auth_config: Optional[AuthConfig] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._auth_config = auth_config
        self._is_edit_mode = auth_config is not None
        self._init_ui()
        if auth_config:
            self._load_config_data()

    def _init_ui(self) -> None:
        title = "编辑登录配置" if self._is_edit_mode else "添加登录配置"
        self.setWindowTitle(title)
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # 基本信息卡片
        basic_card = self._create_card("基本信息")
        basic_layout = QFormLayout(basic_card)
        basic_layout.setSpacing(12)
        basic_layout.setContentsMargins(20, 20, 20, 20)
        basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例如: 用户登录认证")
        self._name_edit.setStyleSheet(self._input_style())
        basic_layout.addRow(self._form_label("配置名称:"), self._name_edit)

        self._is_enabled_checkbox = QCheckBox("启用此配置")
        self._is_enabled_checkbox.setChecked(True)
        self._is_enabled_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #424242;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #bdbdbd;
            }
            QCheckBox::indicator:checked {
                background-color: #2196f3;
                border-color: #2196f3;
            }
        """)
        basic_layout.addRow("", self._is_enabled_checkbox)

        scroll_layout.addWidget(basic_card)

        # 登录接口配置卡片
        api_card = self._create_card("登录接口配置")
        api_layout = QFormLayout(api_card)
        api_layout.setSpacing(12)
        api_layout.setContentsMargins(20, 20, 20, 20)
        api_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText("例如: http://192.168.1.100:8080")
        self._base_url_edit.setStyleSheet(self._input_style())
        api_layout.addRow(self._form_label("Base URL:"), self._base_url_edit)

        self._login_path_edit = QLineEdit()
        self._login_path_edit.setPlaceholderText("例如: /api/auth/login")
        self._login_path_edit.setStyleSheet(self._input_style())
        api_layout.addRow(self._form_label("登录路径:"), self._login_path_edit)

        self._method_combo = QComboBox()
        self._method_combo.addItems(["POST", "GET", "PUT", "PATCH"])
        self._method_combo.setCurrentText("POST")
        self._method_combo.setStyleSheet(self._combo_style())
        api_layout.addRow(self._form_label("请求方法:"), self._method_combo)

        scroll_layout.addWidget(api_card)

        # 请求参数卡片
        request_card = self._create_card("请求参数")
        request_layout = QVBoxLayout(request_card)
        request_layout.setSpacing(10)
        request_layout.setContentsMargins(20, 20, 20, 20)

        headers_label = QLabel("请求头 (JSON格式，可选):")
        headers_label.setStyleSheet("font-size: 13px; color: #616161; font-weight: 500;")
        request_layout.addWidget(headers_label)

        self._headers_edit = QTextEdit()
        self._headers_edit.setPlaceholderText('{\n  "Content-Type": "application/json"\n}')
        self._headers_edit.setMinimumHeight(80)
        self._headers_edit.setMaximumHeight(100)
        self._headers_edit.setStyleSheet(self._text_edit_style())
        request_layout.addWidget(self._headers_edit)

        body_label = QLabel("请求体 (JSON格式):")
        body_label.setStyleSheet("font-size: 13px; color: #616161; font-weight: 500;")
        request_layout.addWidget(body_label)

        self._body_edit = QTextEdit()
        self._body_edit.setPlaceholderText('{\n  "username": "admin",\n  "password": "123456"\n}')
        self._body_edit.setMinimumHeight(100)
        self._body_edit.setMaximumHeight(130)
        self._body_edit.setStyleSheet(self._text_edit_style())
        request_layout.addWidget(self._body_edit)

        scroll_layout.addWidget(request_card)

        # Token 提取配置卡片
        token_card = self._create_card("Token 提取配置")
        token_layout = QFormLayout(token_card)
        token_layout.setSpacing(12)
        token_layout.setContentsMargins(20, 20, 20, 20)
        token_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._token_path_edit = QLineEdit()
        self._token_path_edit.setPlaceholderText("$.data.access_token")
        self._token_path_edit.setText("$.data.access_token")
        self._token_path_edit.setStyleSheet(self._input_style())
        token_layout.addRow(self._form_label("Token 路径:"), self._token_path_edit)

        self._token_prefix_edit = QLineEdit()
        self._token_prefix_edit.setPlaceholderText("（可选）例如：Bearer")
        self._token_prefix_edit.setStyleSheet(self._input_style())
        token_layout.addRow(self._form_label("Token 前缀:"), self._token_prefix_edit)

        self._header_name_edit = QLineEdit()
        self._header_name_edit.setPlaceholderText("Authorization")
        self._header_name_edit.setText("Authorization")
        self._header_name_edit.setStyleSheet(self._input_style())
        token_layout.addRow(self._form_label("Header 名称:"), self._header_name_edit)

        scroll_layout.addWidget(token_card)

        # 测试登录卡片
        test_card = self._create_card("测试登录")
        test_layout = QVBoxLayout(test_card)
        test_layout.setSpacing(12)
        test_layout.setContentsMargins(20, 20, 20, 20)

        test_header = QHBoxLayout()
        test_title = QLabel("验证配置")
        test_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #424242;")
        test_header.addWidget(test_title)

        self._test_btn = QPushButton("测试登录")
        self._test_btn.setStyleSheet(self._secondary_button_style())
        self._test_btn.clicked.connect(self._test_login)
        test_header.addWidget(self._test_btn)
        test_layout.addLayout(test_header)

        self._test_result_text = QTextEdit()
        self._test_result_text.setReadOnly(True)
        self._test_result_text.setMinimumHeight(80)
        self._test_result_text.setMaximumHeight(100)
        self._test_result_text.setPlaceholderText("点击测试登录按钮验证配置...")
        self._test_result_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
                color: #616161;
            }
        """)
        test_layout.addWidget(self._test_result_text)

        scroll_layout.addWidget(test_card)
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(self._secondary_button_style())
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(self._primary_button_style())
        save_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(save_btn)

        main_layout.addLayout(button_layout)

    def _create_card(self, title: str) -> QWidget:
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
            }
        """)
        return card

    def _form_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 13px; color: #616161; font-weight: 500;")
        return label

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
                color: #424242;
            }
            QLineEdit:focus {
                border-color: #e0e0e0;
            }
            QLineEdit::placeholder {
                color: #9e9e9e;
            }
        """

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: #424242;
                min-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """

    def _text_edit_style(self) -> str:
        return """
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
                color: #424242;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QTextEdit:focus {
                border-color: #e0e0e0;
            }
        """

    def _primary_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
        """

    def _secondary_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #ffffff;
                color: #424242;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-color: #bdbdbd;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """

    def _load_config_data(self) -> None:
        if self._auth_config:
            self._name_edit.setText(self._auth_config.name)
            self._is_enabled_checkbox.setChecked(self._auth_config.is_enabled)
            self._base_url_edit.setText(self._auth_config.base_url)
            self._login_path_edit.setText(self._auth_config.login_path)
            self._method_combo.setCurrentText(self._auth_config.method)

            if self._auth_config.headers:
                self._headers_edit.setPlainText(json.dumps(self._auth_config.headers, ensure_ascii=False, indent=2))

            if self._auth_config.body:
                self._body_edit.setPlainText(json.dumps(self._auth_config.body, ensure_ascii=False, indent=2))

            self._token_path_edit.setText(self._auth_config.token_path)
            self._token_prefix_edit.setText(self._auth_config.token_prefix if self._auth_config.token_prefix else "")
            self._header_name_edit.setText(self._auth_config.header_name or "Authorization")

    def _test_login(self) -> None:
        if not self._validate_input():
            return

        self._test_btn.setEnabled(False)
        self._test_result_text.setText("正在执行登录请求...")
        self._test_result_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
                color: #616161;
            }
        """)
        QApplication.processEvents()

        config = self._get_temp_config()
        result = AuthService.execute_login(config)

        if result.success:
            self._test_result_text.setText(
                f"✅ 登录成功!\n\n"
                f"状态码: {result.status_code}\n"
                f"Header 名称: {result.header_name}\n"
                f"Header 值: {result.header_value}\n\n"
                f"Token: {result.token}"
            )
            self._test_result_text.setStyleSheet("""
                QTextEdit {
                    background-color: #e8f5e9;
                    border: 1px solid #a5d6a7;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 13px;
                    color: #2e7d32;
                }
            """)
        else:
            self._test_result_text.setText(f"❌ 登录失败:\n{result.error_message}")
            self._test_result_text.setStyleSheet("""
                QTextEdit {
                    background-color: #ffebee;
                    border: 1px solid #ef9a9a;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 13px;
                    color: #c62828;
                }
            """)

        self._test_btn.setEnabled(True)

    def _get_temp_config(self) -> AuthConfig:
        headers = {}
        headers_text = self._headers_edit.toPlainText().strip()
        if headers_text:
            try:
                headers = json.loads(headers_text)
            except:
                headers = {}

        body = {}
        body_text = self._body_edit.toPlainText().strip()
        if body_text:
            try:
                body = json.loads(body_text)
            except:
                body = {}

        return AuthConfig(
            name=self._name_edit.text().strip(),
            base_url=self._base_url_edit.text().strip(),
            login_path=self._login_path_edit.text().strip(),
            method=self._method_combo.currentText(),
            headers=headers,
            body=body,
            token_path=self._token_path_edit.text().strip(),
            token_prefix=self._token_prefix_edit.text().strip(),
            header_name=self._header_name_edit.text().strip(),
            is_enabled=self._is_enabled_checkbox.isChecked(),
        )

    def _validate_input(self) -> bool:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入配置名称")
            return False
        if not self._base_url_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入 Base URL")
            return False
        if not self._login_path_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入登录路径")
            return False
        if not self._token_path_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入 Token 路径")
            return False

        headers_text = self._headers_edit.toPlainText().strip()
        if headers_text:
            try:
                json.loads(headers_text)
            except:
                QMessageBox.warning(self, "验证失败", "请求头格式错误，请输入有效的 JSON")
                return False

        body_text = self._body_edit.toPlainText().strip()
        if body_text:
            try:
                json.loads(body_text)
            except:
                QMessageBox.warning(self, "验证失败", "请求体格式错误，请输入有效的 JSON")
                return False

        return True

    def _on_accept(self) -> None:
        if not self._validate_input():
            return
        self.accept()

    def get_config_data(self) -> dict:
        headers = {}
        headers_text = self._headers_edit.toPlainText().strip()
        if headers_text:
            try:
                headers = json.loads(headers_text)
            except:
                headers = {}

        body = {}
        body_text = self._body_edit.toPlainText().strip()
        if body_text:
            try:
                body = json.loads(body_text)
            except:
                body = {}

        return {
            "name": self._name_edit.text().strip(),
            "base_url": self._base_url_edit.text().strip(),
            "login_path": self._login_path_edit.text().strip(),
            "method": self._method_combo.currentText(),
            "headers": headers,
            "body": body,
            "token_path": self._token_path_edit.text().strip(),
            "token_prefix": self._token_prefix_edit.text().strip(),
            "header_name": self._header_name_edit.text().strip(),
            "is_enabled": self._is_enabled_checkbox.isChecked(),
        }


class AuthConfigPage(BasePage):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("登录配置", parent)
        self._init_content()
        self._load_configs()

    def _init_content(self) -> None:
        # 顶部工具栏
        toolbar = QWidget()
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setSpacing(12)
        toolbar_layout.setContentsMargins(16, 12, 16, 12)

        self._add_btn = QPushButton("+ 添加配置")
        self._add_btn.setStyleSheet(self._primary_button_style())
        self._add_btn.clicked.connect(self._show_add_dialog)
        toolbar_layout.addWidget(self._add_btn)

        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setStyleSheet(self._secondary_button_style())
        self._edit_btn.clicked.connect(self._edit_selected_config)
        toolbar_layout.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("删除")
        self._delete_btn.setStyleSheet(self._danger_button_style())
        self._delete_btn.clicked.connect(self._delete_selected_config)
        toolbar_layout.addWidget(self._delete_btn)

        toolbar_layout.addStretch()

        # 提示文字
        tip_label = QLabel("提示: 双击表格行可编辑配置，在测试用例页面可获取 Token")
        tip_label.setStyleSheet("color: #757575; font-size: 12px;")
        toolbar_layout.addWidget(tip_label)

        self.add_widget(toolbar)

        # 表格区域
        table_container = QWidget()
        table_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["名称", "登录接口", "请求方法", "Token路径", "启用", "创建时间"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
                gridline-color: #f5f5f5;
                font-size: 13px;
                outline: none;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #f5f5f5;
                outline: none;
            }
            QTableWidget::item:selected {
                background-color: #f5f5f5;
                color: #424242;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
            QTableWidget:focus {
                outline: none;
            }
            QHeaderView::section {
                background-color: #fafafa;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                padding: 12px 8px;
                font-weight: 600;
                font-size: 13px;
                color: #424242;
            }
        """)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(0, 150)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 180)
        self._table.setColumnWidth(4, 60)
        self._table.setColumnWidth(5, 150)

        table_layout.addWidget(self._table)
        self.add_widget(table_container, stretch=1)

        # 底部操作栏
        action_bar = QWidget()
        action_bar.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
            }
        """)
        action_layout = QHBoxLayout(action_bar)
        action_layout.setSpacing(12)
        action_layout.setContentsMargins(16, 12, 16, 12)

        self._test_btn = QPushButton("测试登录")
        self._test_btn.setStyleSheet(self._secondary_button_style())
        self._test_btn.clicked.connect(self._test_selected_config)
        action_layout.addWidget(self._test_btn)

        self._toggle_btn = QPushButton("启用/禁用")
        self._toggle_btn.setStyleSheet(self._secondary_button_style())
        self._toggle_btn.clicked.connect(self._toggle_enabled)
        action_layout.addWidget(self._toggle_btn)

        action_layout.addStretch()

        self.add_widget(action_bar)

        self._table.doubleClicked.connect(self._edit_selected_config)

    def _primary_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
        """

    def _secondary_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #ffffff;
                color: #424242;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-color: #bdbdbd;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """

    def _danger_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #ffffff;
                color: #f44336;
                border: 1px solid #ffcdd2;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ffebee;
                border-color: #ef9a9a;
            }
            QPushButton:pressed {
                background-color: #ffcdd2;
            }
        """

    def _load_configs(self) -> None:
        configs = AuthConfig.get_all()
        self._table.setRowCount(len(configs))

        for row, config in enumerate(configs):
            name_item = QTableWidgetItem(config.name)
            name_item.setData(Qt.ItemDataRole.UserRole, config.id)
            self._table.setItem(row, 0, name_item)

            login_url = f"{config.base_url}{config.login_path}"
            self._table.setItem(row, 1, QTableWidgetItem(login_url))

            self._table.setItem(row, 2, QTableWidgetItem(config.method))

            self._table.setItem(row, 3, QTableWidgetItem(config.token_path))

            enabled_item = QTableWidgetItem("✓" if config.is_enabled else "")
            enabled_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 4, enabled_item)

            created_at = config.created_at.strftime("%Y-%m-%d %H:%M") if config.created_at else ""
            self._table.setItem(row, 5, QTableWidgetItem(created_at))

    def _show_add_dialog(self) -> None:
        dialog = AuthConfigDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_config_data()
            config = AuthConfig(**data)
            config.save()
            self._load_configs()
            QMessageBox.information(self, "成功", "登录配置添加成功")

    def _edit_selected_config(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的配置")
            return

        row = selected_rows[0].row()
        config_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        config = AuthConfig.get_by_id(config_id)

        if config:
            dialog = AuthConfigDialog(config, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_config_data()
                config.name = data["name"]
                config.base_url = data["base_url"]
                config.login_path = data["login_path"]
                config.method = data["method"]
                config.headers = data["headers"]
                config.body = data["body"]
                config.token_path = data["token_path"]
                config.token_prefix = data["token_prefix"]
                config.header_name = data["header_name"]
                config.is_enabled = data["is_enabled"]
                config.save()
                self._load_configs()
                QMessageBox.information(self, "成功", "登录配置更新成功")

    def _delete_selected_config(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的配置")
            return

        row = selected_rows[0].row()
        config_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        config = AuthConfig.get_by_id(config_id)

        if config:
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除配置 '{config.name}' 吗?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                config.delete()
                self._load_configs()
                QMessageBox.information(self, "成功", "登录配置已删除")

    def _test_selected_config(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要测试的配置")
            return

        row = selected_rows[0].row()
        config_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        config = AuthConfig.get_by_id(config_id)

        if config:
            result = AuthService.execute_login(config)
            if result.success:
                QMessageBox.information(
                    self,
                    "登录成功",
                    f"Token 已获取!\n\n"
                    f"Header 名称: {result.header_name}\n"
                    f"Header 值: {result.header_value}\n\n"
                    f"Token: {result.token}"
                )
            else:
                QMessageBox.critical(self, "登录失败", result.error_message)

    def _toggle_enabled(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要操作的配置")
            return

        row = selected_rows[0].row()
        config_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        config = AuthConfig.get_by_id(config_id)

        if config:
            config.is_enabled = not config.is_enabled
            config.save()
            self._load_configs()
            status = "已启用" if config.is_enabled else "已禁用"
            QMessageBox.information(self, "成功", f"配置 '{config.name}' {status}")

    def refresh(self) -> None:
        self._load_configs()
