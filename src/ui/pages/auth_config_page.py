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
    QDialogButtonBox,
    QCheckBox,
    QMessageBox,
    QTextEdit,
    QGroupBox,
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
        self.setMinimumWidth(750)
        self.setMinimumHeight(650)
        self.setModal(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        style_manager.apply_style(scroll_area, "scroll_area")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)

        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(12)
        basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例如: 用户登录认证")
        self._name_edit.setMinimumWidth(400)
        basic_layout.addRow("配置名称:", self._name_edit)

        self._is_enabled_checkbox = QCheckBox("启用此配置")
        self._is_enabled_checkbox.setChecked(True)
        basic_layout.addRow("", self._is_enabled_checkbox)

        content_layout.addWidget(basic_group)

        api_group = QGroupBox("登录接口配置")
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(12)
        api_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText("例如: http://192.168.1.100:8080")
        self._base_url_edit.setMinimumWidth(400)
        api_layout.addRow("Base URL:", self._base_url_edit)

        self._login_path_edit = QLineEdit()
        self._login_path_edit.setPlaceholderText("例如: /api/auth/login")
        self._login_path_edit.setMinimumWidth(400)
        api_layout.addRow("登录路径:", self._login_path_edit)

        self._method_combo = QComboBox()
        self._method_combo.addItems(["POST", "GET", "PUT", "PATCH"])
        self._method_combo.setCurrentText("POST")
        self._method_combo.setMinimumWidth(150)
        api_layout.addRow("请求方法:", self._method_combo)

        content_layout.addWidget(api_group)

        request_group = QGroupBox("请求参数")
        request_layout = QVBoxLayout(request_group)
        request_layout.setSpacing(10)

        headers_label = QLabel("请求头 (JSON格式，可选):")
        request_layout.addWidget(headers_label)

        self._headers_edit = QTextEdit()
        self._headers_edit.setPlaceholderText('{\n  "Content-Type": "application/json"\n}')
        self._headers_edit.setMinimumHeight(80)
        self._headers_edit.setMaximumHeight(120)
        request_layout.addWidget(self._headers_edit)

        body_label = QLabel("请求体 (JSON格式):")
        request_layout.addWidget(body_label)

        self._body_edit = QTextEdit()
        self._body_edit.setPlaceholderText('{\n  "username": "admin",\n  "password": "123456"\n}')
        self._body_edit.setMinimumHeight(100)
        self._body_edit.setMaximumHeight(150)
        request_layout.addWidget(self._body_edit)

        content_layout.addWidget(request_group)

        token_group = QGroupBox("Token 提取配置")
        token_layout = QFormLayout(token_group)
        token_layout.setSpacing(12)
        token_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._token_path_edit = QLineEdit()
        self._token_path_edit.setPlaceholderText("$.data.access_token")
        self._token_path_edit.setText("$.data.access_token")
        self._token_path_edit.setMinimumWidth(400)
        token_layout.addRow("Token 路径:", self._token_path_edit)

        self._token_prefix_edit = QLineEdit()
        self._token_prefix_edit.setPlaceholderText("（可选）例如：Bearer")
        self._token_prefix_edit.setMinimumWidth(150)
        token_layout.addRow("Token 前缀:", self._token_prefix_edit)

        self._header_name_edit = QLineEdit()
        self._header_name_edit.setPlaceholderText("Authorization")
        self._header_name_edit.setText("Authorization")
        self._header_name_edit.setMinimumWidth(200)
        token_layout.addRow("Header 名称:", self._header_name_edit)

        content_layout.addWidget(token_group)

        test_group = QGroupBox("测试登录")
        test_layout = QVBoxLayout(test_group)
        test_layout.setSpacing(10)

        test_btn_layout = QHBoxLayout()
        self._test_btn = QPushButton("测试登录")
        self._test_btn.clicked.connect(self._test_login)
        self._test_btn.setMinimumWidth(120)
        style_manager.apply_style(self._test_btn, "button_secondary")
        test_btn_layout.addWidget(self._test_btn)
        test_btn_layout.addStretch()
        test_layout.addLayout(test_btn_layout)

        self._test_result_text = QTextEdit()
        self._test_result_text.setReadOnly(True)
        self._test_result_text.setMinimumHeight(100)
        self._test_result_text.setMaximumHeight(150)
        self._test_result_text.setPlaceholderText("点击测试登录按钮验证配置...")
        style_manager.apply_style(self._test_result_text, "input")
        test_layout.addWidget(self._test_result_text)

        content_layout.addWidget(test_group)

        scroll_layout.addLayout(content_layout)
        scroll_area.setWidget(scroll_content)

        main_layout.addWidget(scroll_area)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.setMinimumWidth(200)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        main_layout.addLayout(button_layout)
        
        style_manager.apply_style(self._name_edit, "input")
        style_manager.apply_style(self._base_url_edit, "input")
        style_manager.apply_style(self._login_path_edit, "input")
        style_manager.apply_style(self._method_combo, "combo")
        style_manager.apply_style(self._token_path_edit, "input")
        style_manager.apply_style(self._token_prefix_edit, "input")
        style_manager.apply_style(self._header_name_edit, "input")
        style_manager.apply_style(self._is_enabled_checkbox, "checkbox")
        style_manager.apply_style(basic_group, "group_box")
        style_manager.apply_style(api_group, "group_box")
        style_manager.apply_style(request_group, "group_box")
        style_manager.apply_style(token_group, "group_box")
        style_manager.apply_style(test_group, "group_box")
    
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
            self._test_result_text.setStyleSheet("color: #2e7d32;")
        else:
            self._test_result_text.setText(f"❌ 登录失败:\n{result.error_message}")
            self._test_result_text.setStyleSheet("color: #c62828;")
        
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
        btn_layout = QHBoxLayout()
        
        self._add_btn = QPushButton("添加配置")
        self._add_btn.clicked.connect(self._show_add_dialog)
        style_manager.apply_style(self._add_btn, "button_primary")
        btn_layout.addWidget(self._add_btn)
        
        self._edit_btn = QPushButton("编辑")
        self._edit_btn.clicked.connect(self._edit_selected_config)
        style_manager.apply_style(self._edit_btn, "button_secondary")
        btn_layout.addWidget(self._edit_btn)
        
        self._delete_btn = QPushButton("删除")
        self._delete_btn.clicked.connect(self._delete_selected_config)
        style_manager.apply_style(self._delete_btn, "button_danger")
        btn_layout.addWidget(self._delete_btn)
        
        btn_layout.addStretch()
        
        self.add_layout(btn_layout)
        
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["名称", "登录接口", "请求方法", "Token路径", "启用", "创建时间"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        
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
        
        style_manager.apply_style(self._table, "table")
        self.add_widget(self._table)
        
        action_layout = QHBoxLayout()
        
        self._test_btn = QPushButton("测试登录")
        self._test_btn.clicked.connect(self._test_selected_config)
        style_manager.apply_style(self._test_btn, "button_secondary")
        action_layout.addWidget(self._test_btn)
        
        self._toggle_btn = QPushButton("启用/禁用")
        self._toggle_btn.clicked.connect(self._toggle_enabled)
        style_manager.apply_style(self._toggle_btn, "button_secondary")
        action_layout.addWidget(self._toggle_btn)
        
        action_layout.addStretch()
        
        self.add_layout(action_layout)
        
        tip_label = QLabel("提示: 双击表格行可编辑配置，在测试用例页面可获取 Token")
        tip_label.setStyleSheet("color: #757575; font-size: 12px;")
        self.add_widget(tip_label)
        
        self._table.doubleClicked.connect(self._edit_selected_config)
    
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
