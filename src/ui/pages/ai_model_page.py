from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
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
)

from models.ai_model import AIModel
from ai.client import AIClient, AIModelConfig, ConnectionTestResult
from ui.styles import style_manager
from ui.pages.base_page import BasePage


class AIModelDialog(QDialog):
    def __init__(self, model: Optional[AIModel] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model = model
        self._is_edit_mode = model is not None
        self._init_ui()
        if model:
            self._load_model_data()
    
    def _init_ui(self) -> None:
        title = "编辑 AI 模型" if self._is_edit_mode else "添加 AI 模型"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        form_group = QGroupBox("模型配置")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例如: GPT-4, Claude-3 等")
        form_layout.addRow("模型名称:", self._name_edit)
        
        self._api_base_edit = QLineEdit()
        self._api_base_edit.setPlaceholderText("例如: https://api.openai.com/v1")
        form_layout.addRow("API 地址:", self._api_base_edit)
        
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("输入 API Key")
        form_layout.addRow("API Key:", self._api_key_edit)
        
        self._model_name_edit = QLineEdit()
        self._model_name_edit.setPlaceholderText("例如: gpt-4, claude-3-opus 等")
        form_layout.addRow("模型标识:", self._model_name_edit)
        
        self._is_default_checkbox = QCheckBox("设为默认模型")
        form_layout.addRow("", self._is_default_checkbox)
        
        layout.addWidget(form_group)
        
        test_group = QGroupBox("连接测试")
        test_layout = QVBoxLayout(test_group)
        
        test_btn_layout = QHBoxLayout()
        self._test_btn = QPushButton("测试连接")
        self._test_btn.clicked.connect(self._test_connection)
        style_manager.apply_style(self._test_btn, "button_secondary")
        test_btn_layout.addWidget(self._test_btn)
        test_btn_layout.addStretch()
        test_layout.addLayout(test_btn_layout)
        
        self._test_result_text = QTextEdit()
        self._test_result_text.setReadOnly(True)
        self._test_result_text.setMaximumHeight(100)
        self._test_result_text.setPlaceholderText("点击测试连接按钮验证配置...")
        style_manager.apply_style(self._test_result_text, "input")
        test_layout.addWidget(self._test_result_text)
        
        layout.addWidget(test_group)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        style_manager.apply_style(self._name_edit, "input")
        style_manager.apply_style(self._api_base_edit, "input")
        style_manager.apply_style(self._api_key_edit, "input")
        style_manager.apply_style(self._model_name_edit, "input")
        style_manager.apply_style(self._is_default_checkbox, "checkbox")
        style_manager.apply_style(form_group, "group_box")
        style_manager.apply_style(test_group, "group_box")
    
    def _load_model_data(self) -> None:
        if self._model:
            self._name_edit.setText(self._model.name)
            self._api_base_edit.setText(self._model.api_base)
            self._api_key_edit.setText(self._model.api_key)
            self._model_name_edit.setText(self._model.model_name)
            self._is_default_checkbox.setChecked(self._model.is_default)
    
    def _test_connection(self) -> None:
        if not self._validate_input():
            return
        
        self._test_btn.setEnabled(False)
        self._test_result_text.setText("正在测试连接...")
        
        config = AIModelConfig(
            name=self._name_edit.text().strip(),
            api_base_url=self._api_base_edit.text().strip(),
            api_key=self._api_key_edit.text().strip(),
            model_name=self._model_name_edit.text().strip(),
        )
        
        client = AIClient(config)
        try:
            result: ConnectionTestResult = client.test_connection()
            if result.success:
                self._test_result_text.setText(
                    f"✅ 连接成功!\n"
                    f"模型: {result.model_info}\n"
                    f"延迟: {result.latency_ms} ms"
                )
                self._test_result_text.setStyleSheet("color: #2e7d32;")
            else:
                self._test_result_text.setText(f"❌ 连接失败:\n{result.message}")
                self._test_result_text.setStyleSheet("color: #c62828;")
        finally:
            client.close()
            self._test_btn.setEnabled(True)
    
    def _validate_input(self) -> bool:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入模型名称")
            return False
        if not self._api_base_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入 API 地址")
            return False
        if not self._api_key_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入 API Key")
            return False
        if not self._model_name_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入模型标识")
            return False
        return True
    
    def _on_accept(self) -> None:
        if not self._validate_input():
            return
        self.accept()
    
    def get_model_data(self) -> dict:
        return {
            "name": self._name_edit.text().strip(),
            "api_base": self._api_base_edit.text().strip(),
            "api_key": self._api_key_edit.text().strip(),
            "model_name": self._model_name_edit.text().strip(),
            "is_default": self._is_default_checkbox.isChecked(),
        }


class AIModelPage(BasePage):
    model_changed = pyqtSignal()
    
    def __init__(self, on_model_changed: Optional[callable] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__("AI 模型配置", parent)
        self._on_model_changed_callback = on_model_changed
        self._init_content()
        self._load_models()
    
    def _init_content(self) -> None:
        btn_layout = QHBoxLayout()
        
        self._add_btn = QPushButton("添加模型")
        self._add_btn.clicked.connect(self.show_add_dialog)
        style_manager.apply_style(self._add_btn, "button_primary")
        btn_layout.addWidget(self._add_btn)
        
        self._edit_btn = QPushButton("编辑")
        self._edit_btn.clicked.connect(self._edit_selected_model)
        style_manager.apply_style(self._edit_btn, "button_secondary")
        btn_layout.addWidget(self._edit_btn)
        
        self._delete_btn = QPushButton("删除")
        self._delete_btn.clicked.connect(self._delete_selected_model)
        style_manager.apply_style(self._delete_btn, "button_danger")
        btn_layout.addWidget(self._delete_btn)
        
        btn_layout.addStretch()
        
        self.add_layout(btn_layout)
        
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["名称", "API 地址", "模型标识", "默认", "创建时间"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self._table.setColumnWidth(0, 150)
        self._table.setColumnWidth(2, 150)
        self._table.setColumnWidth(3, 80)
        self._table.setColumnWidth(4, 150)
        
        style_manager.apply_style(self._table, "table")
        self.add_widget(self._table)
        
        action_layout = QHBoxLayout()
        
        self._set_default_btn = QPushButton("设为默认")
        self._set_default_btn.clicked.connect(self._set_default_model)
        style_manager.apply_style(self._set_default_btn, "button_secondary")
        action_layout.addWidget(self._set_default_btn)
        
        self._test_btn = QPushButton("测试连接")
        self._test_btn.clicked.connect(self._test_selected_model)
        style_manager.apply_style(self._test_btn, "button_secondary")
        action_layout.addWidget(self._test_btn)
        
        action_layout.addStretch()
        
        self.add_layout(action_layout)
        
        tip_label = QLabel("提示: 双击表格行可编辑模型配置")
        tip_label.setStyleSheet("color: #757575; font-size: 12px;")
        self.add_widget(tip_label)
        
        self._table.doubleClicked.connect(self._edit_selected_model)
    
    def _load_models(self) -> None:
        models = AIModel.get_all()
        self._table.setRowCount(len(models))
        
        for row, model in enumerate(models):
            name_item = QTableWidgetItem(model.name)
            name_item.setData(Qt.ItemDataRole.UserRole, model.id)
            self._table.setItem(row, 0, name_item)
            
            self._table.setItem(row, 1, QTableWidgetItem(model.api_base))
            self._table.setItem(row, 2, QTableWidgetItem(model.model_name))
            
            default_item = QTableWidgetItem("✓" if model.is_default else "")
            default_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 3, default_item)
            
            created_at = model.created_at.strftime("%Y-%m-%d %H:%M") if model.created_at else ""
            self._table.setItem(row, 4, QTableWidgetItem(created_at))
    
    def show_add_dialog(self) -> None:
        dialog = AIModelDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_model_data()
            model = AIModel(**data)
            model.save()
            self._load_models()
            self.model_changed.emit()
            if self._on_model_changed_callback:
                self._on_model_changed_callback()
            QMessageBox.information(self, "成功", "AI 模型添加成功")
    
    def _edit_selected_model(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的模型")
            return
        
        row = selected_rows[0].row()
        model_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        model = AIModel.get_by_id(model_id)
        
        if model:
            dialog = AIModelDialog(model, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_model_data()
                model.name = data["name"]
                model.api_base = data["api_base"]
                model.api_key = data["api_key"]
                model.model_name = data["model_name"]
                model.is_default = data["is_default"]
                model.save()
                self._load_models()
                self.model_changed.emit()
                if self._on_model_changed_callback:
                    self._on_model_changed_callback()
                QMessageBox.information(self, "成功", "AI 模型更新成功")
    
    def _delete_selected_model(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的模型")
            return
        
        row = selected_rows[0].row()
        model_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        model = AIModel.get_by_id(model_id)
        
        if model:
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除模型 '{model.name}' 吗?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                model.delete()
                self._load_models()
                self.model_changed.emit()
                if self._on_model_changed_callback:
                    self._on_model_changed_callback()
                QMessageBox.information(self, "成功", "AI 模型已删除")
    
    def _set_default_model(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要设为默认的模型")
            return
        
        row = selected_rows[0].row()
        model_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        model = AIModel.get_by_id(model_id)
        
        if model:
            model.set_as_default()
            self._load_models()
            self.model_changed.emit()
            if self._on_model_changed_callback:
                self._on_model_changed_callback()
            QMessageBox.information(self, "成功", f"'{model.name}' 已设为默认模型")
    
    def _test_selected_model(self) -> None:
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要测试的模型")
            return
        
        row = selected_rows[0].row()
        model_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        model = AIModel.get_by_id(model_id)
        
        if model:
            config = AIModelConfig(
                name=model.name,
                api_base_url=model.api_base,
                api_key=model.api_key,
                model_name=model.model_name,
            )
            
            client = AIClient(config)
            try:
                result = client.test_connection()
                if result.success:
                    QMessageBox.information(
                        self,
                        "连接成功",
                        f"模型: {result.model_info}\n延迟: {result.latency_ms} ms"
                    )
                else:
                    QMessageBox.critical(self, "连接失败", result.message)
            finally:
                client.close()
    
    def refresh(self) -> None:
        self._load_models()
