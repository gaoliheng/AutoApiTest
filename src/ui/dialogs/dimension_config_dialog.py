from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QComboBox,
    QScrollArea,
    QFrame,
    QMessageBox,
    QInputDialog,
)

from ui.styles import style_manager
from utils.config import config, DEFAULT_TEST_DIMENSIONS
from utils.logger import get_logger

_logger = get_logger("ui.dimension_config_dialog")


class DimensionConfigDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dimension_widgets: dict[str, dict] = {}
        self._init_ui()
        self._load_config()

    def _init_ui(self) -> None:
        self.setWindowTitle("测试维度配置")
        self.setMinimumSize(700, 500)
        self.resize(750, 550)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("配置 AI 生成测试用例时的测试维度")
        title_label.setStyleSheet("font-size: 14px; color: #424242;")
        layout.addWidget(title_label)

        desc_label = QLabel("勾选需要启用的维度，设置优先级。AI 会根据配置的维度生成测试用例。")
        desc_label.setStyleSheet("font-size: 12px; color: #757575;")
        layout.addWidget(desc_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #fafafa;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdbdbd;
                border-radius: 4px;
                min-height: 20px;
            }
        """)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        self._dimension_container = QWidget()
        self._dimension_layout = QVBoxLayout(self._dimension_container)
        self._dimension_layout.setContentsMargins(0, 0, 0, 0)
        self._dimension_layout.setSpacing(8)
        scroll_layout.addWidget(self._dimension_container)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        add_btn = QPushButton("+ 添加自定义维度")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                color: #1565c0;
                border: 1px solid #90caf9;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
        """)
        add_btn.clicked.connect(self._add_custom_dimension)
        footer_layout.addWidget(add_btn)

        footer_layout.addStretch()

        reset_btn = QPushButton("重置默认")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #fff3e0;
                color: #e65100;
                border: 1px solid #ffcc80;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ffe0b2;
            }
        """)
        reset_btn.clicked.connect(self._reset_config)
        footer_layout.addWidget(reset_btn)

        layout.addLayout(footer_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #424242;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #eeeeee;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(100)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e88e5;
            }
        """)
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _load_config(self) -> None:
        for i in range(self._dimension_layout.count()):
            item = self._dimension_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        self._dimension_widgets.clear()

        dimensions = config.test_dimensions
        for dim in dimensions:
            self._add_dimension_widget(dim)

    def _add_dimension_widget(self, dim_data: dict) -> None:
        dim_id = dim_data.get("id", str(id(dim_data)))
        is_system = dim_id in ["happy_path", "boundary", "error_case", "performance"]

        row_widget = QWidget()
        row_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(12, 10, 12, 10)
        row_layout.setSpacing(15)

        enabled_cb = QCheckBox()
        enabled_cb.setChecked(dim_data.get("enabled", True))
        enabled_cb.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #bdbdbd;
            }
            QCheckBox::indicator:checked {
                background-color: #2196f3;
                border-color: #2196f3;
            }
        """)
        enabled_cb.stateChanged.connect(self._on_dimension_changed)
        row_layout.addWidget(enabled_cb)

        name_label = QLabel(dim_data.get("name", ""))
        name_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #424242; min-width: 100px;")
        row_layout.addWidget(name_label)

        desc_label = QLabel(dim_data.get("description", ""))
        desc_label.setStyleSheet("color: #757575; font-size: 12px;")
        desc_label.setWordWrap(True)
        row_layout.addWidget(desc_label, 1)

        priority_combo = QComboBox()
        priority_combo.addItems(["high", "medium", "low"])
        priority_combo.setCurrentText(dim_data.get("priority", "medium"))
        priority_combo.currentTextChanged.connect(self._on_dimension_changed)
        priority_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
        """)
        row_layout.addWidget(priority_combo)

        if is_system:
            lock_label = QLabel("系统")
            lock_label.setStyleSheet("color: #9e9e9e; font-size: 11px; padding: 4px 8px; background-color: #f5f5f5; border-radius: 4px;")
            row_layout.addWidget(lock_label)
        else:
            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffebee;
                    color: #c62828;
                    border: 1px solid #ef9a9a;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #ffcdd2;
                }
            """)
            delete_btn.clicked.connect(lambda: self._delete_dimension(row_widget, dim_id))
            row_layout.addWidget(delete_btn)

        self._dimension_layout.addWidget(row_widget)
        self._dimension_widgets[dim_id] = {
            "widget": row_widget,
            "enabled_cb": enabled_cb,
            "priority_combo": priority_combo,
            "data": dim_data,
        }

    def _on_dimension_changed(self) -> None:
        self._save_config()

    def _save_config(self) -> None:
        dimensions = []
        for dim_id, widgets in self._dimension_widgets.items():
            data = widgets["data"].copy()
            data["enabled"] = widgets["enabled_cb"].isChecked()
            data["priority"] = widgets["priority_combo"].currentText()
            dimensions.append(data)
        config.test_dimensions = dimensions

    def _delete_dimension(self, widget: QWidget, dim_id: str) -> None:
        if dim_id in self._dimension_widgets:
            del self._dimension_widgets[dim_id]
        widget.deleteLater()
        self._save_config()

    def _add_custom_dimension(self) -> None:
        name, ok = QInputDialog.getText(self, "添加自定义维度", "请输入维度名称：")
        if not ok or not name.strip():
            return

        desc, ok = QInputDialog.getText(self, "添加自定义维度", "请输入维度描述：")
        if not ok:
            return

        custom_dim = {
            "id": f"custom_{len(self._dimension_widgets) + 1}",
            "name": name.strip(),
            "description": desc.strip() if desc.strip() else "用户自定义测试维度",
            "enabled": True,
            "priority": "medium",
        }

        self._add_dimension_widget(custom_dim)
        self._save_config()

    def _reset_config(self) -> None:
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有维度配置到默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            config.reset_test_dimensions()
            self._load_config()

    def _on_ok(self) -> None:
        self._save_config()
        self.accept()
