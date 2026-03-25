import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QLineEdit,
    QComboBox,
    QFileDialog,
    QInputDialog,
    QMenu,
    QAbstractItemView,
)

from models.test_case_history import TestCaseHistory
from ui.styles import style_manager
from utils.logger import get_logger

_logger = get_logger("ui.test_case_history_dialog")


class TestCaseHistoryDialog(QDialog):
    """测试用例历史记录管理弹窗"""
    
    def __init__(
        self,
        on_load_history: Optional[Callable[[TestCaseHistory], None]] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._on_load_history = on_load_history
        self._histories: list[TestCaseHistory] = []
        self._init_ui()
        self._load_histories()
    
    def _init_ui(self) -> None:
        self.setWindowTitle("测试用例历史记录")
        self.setMinimumSize(1200, 700)
        self.resize(1300, 800)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(15)
        
        # 左侧：筛选
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        filter_label = QLabel("筛选:")
        filter_label.setStyleSheet("font-size: 13px; color: #424242;")
        filter_layout.addWidget(filter_label)
        
        self._filter_combo = QComboBox()
        self._filter_combo.addItem("全部记录", "all")
        self._filter_combo.addItem("普通记录", "normal")
        self._filter_combo.addItem("收藏记录", "favorite")
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._filter_combo.setMinimumWidth(120)
        self._filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #bdbdbd;
            }
        """)
        filter_layout.addWidget(self._filter_combo)
        
        toolbar_layout.addLayout(filter_layout)
        toolbar_layout.addStretch()
        
        # 中间：统计信息
        stats_widget = QWidget()
        stats_widget.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-radius: 4px;
                padding: 4px 12px;
            }
        """)
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(10, 4, 10, 4)
        stats_layout.setSpacing(15)
        
        self._normal_stats_label = QLabel("普通: 0/50")
        self._normal_stats_label.setStyleSheet("font-size: 13px; color: #616161;")
        stats_layout.addWidget(self._normal_stats_label)
        
        stats_sep = QLabel("|")
        stats_sep.setStyleSheet("color: #bdbdbd;")
        stats_layout.addWidget(stats_sep)
        
        self._favorite_stats_label = QLabel("收藏: 0")
        self._favorite_stats_label.setStyleSheet("font-size: 13px; color: #f57c00; font-weight: bold;")
        stats_layout.addWidget(self._favorite_stats_label)
        
        toolbar_layout.addWidget(stats_widget)
        toolbar_layout.addStretch()
        
        # 右侧：导入按钮
        import_btn = QPushButton("📥 导入记录")
        import_btn.clicked.connect(self._import_history)
        import_btn.setMinimumWidth(100)
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e9;
                color: #2e7d32;
                border: 1px solid #a5d6a7;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
        """)
        toolbar_layout.addWidget(import_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 历史记录表格
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(["收藏", "名称", "用例数", "Base URL", "接口路径", "描述", "创建时间", "操作"])
        
        # 设置列宽和拉伸模式
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)       # 收藏
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)     # 名称
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)       # 用例数
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # Base URL
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive) # 接口路径
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)     # 描述
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)       # 创建时间
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)       # 操作
        
        self._table.setColumnWidth(0, 50)    # 收藏
        self._table.setColumnWidth(2, 65)    # 用例数
        self._table.setColumnWidth(3, 220)   # Base URL
        self._table.setColumnWidth(4, 180)   # 接口路径
        self._table.setColumnWidth(5, 150)   # 描述
        self._table.setColumnWidth(6, 140)   # 创建时间
        self._table.setColumnWidth(7, 240)   # 操作
        
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.verticalHeader().setDefaultSectionSize(50)
        style_manager.apply_style(self._table, "table")
        
        layout.addWidget(self._table)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        close_btn.setMinimumWidth(100)
        style_manager.apply_style(close_btn, "button_secondary")
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_histories(self) -> None:
        """加载历史记录列表"""
        filter_type = self._filter_combo.currentData()
        
        if filter_type == "favorite":
            self._histories = TestCaseHistory.get_all(favorite_only=True)
        elif filter_type == "normal":
            all_histories = TestCaseHistory.get_all()
            self._histories = [h for h in all_histories if not h.is_favorite]
        else:
            self._histories = TestCaseHistory.get_all()
        
        self._refresh_table()
        self._update_stats()
    
    def _refresh_table(self) -> None:
        """刷新表格显示"""
        self._table.setRowCount(len(self._histories))
        
        for row, history in enumerate(self._histories):
            self._table.setRowHeight(row, 55)
            # 收藏状态
            favorite_btn = QPushButton("★" if history.is_favorite else "☆")
            favorite_btn.setFixedSize(40, 28)
            favorite_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    font-size: 18px;
                    color: {'#ffc107' if history.is_favorite else '#bdbdbd'};
                }}
                QPushButton:hover {{
                    color: #ffc107;
                }}
            """)
            favorite_btn.clicked.connect(lambda checked, h=history: self._toggle_favorite(h))
            self._table.setCellWidget(row, 0, favorite_btn)
            
            # 名称
            name_item = QTableWidgetItem(history.name)
            name_item.setData(Qt.ItemDataRole.UserRole, history.id)
            name_item.setToolTip(history.name)
            self._table.setItem(row, 1, name_item)
            
            # 用例数
            case_count = len(history.test_cases) if history.test_cases else 0
            count_item = QTableWidgetItem(str(case_count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, count_item)
            
            # Base URL
            base_url_text = history.base_url if history.base_url else "-"
            base_url_item = QTableWidgetItem(base_url_text)
            base_url_item.setToolTip(base_url_text)
            self._table.setItem(row, 3, base_url_item)
            
            # 接口路径
            api_path_text = history.api_path if history.api_path else "-"
            api_path_item = QTableWidgetItem(api_path_text)
            api_path_item.setToolTip(api_path_text)
            self._table.setItem(row, 4, api_path_item)
            
            # 描述
            desc_text = history.description if history.description else "-"
            desc_item = QTableWidgetItem(desc_text)
            desc_item.setToolTip(desc_text)
            self._table.setItem(row, 5, desc_item)
            
            # 创建时间
            time_str = history.created_at.strftime("%Y-%m-%d %H:%M") if history.created_at else ""
            self._table.setItem(row, 6, QTableWidgetItem(time_str))
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(3, 8, 3, 8)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            load_btn = QPushButton("加载")
            load_btn.setFixedSize(50, 26)
            load_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e3f2fd;
                    color: #1565c0;
                    border: 1px solid #90caf9;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #bbdefb;
                }
            """)
            load_btn.clicked.connect(lambda checked, h=history: self._load_history(h))
            action_layout.addWidget(load_btn)
            
            export_btn = QPushButton("导出")
            export_btn.setFixedSize(50, 26)
            export_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e8f5e9;
                    color: #2e7d32;
                    border: 1px solid #a5d6a7;
                    border-radius: 4px;
                    font-size: 12px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #c8e6c9;
                }
            """)
            export_btn.clicked.connect(lambda checked, h=history: self._export_history(h))
            action_layout.addWidget(export_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.setFixedSize(50, 26)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffebee;
                    color: #c62828;
                    border: 1px solid #ef9a9a;
                    border-radius: 4px;
                    font-size: 12px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #ffcdd2;
                }
            """)
            delete_btn.clicked.connect(lambda checked, h=history: self._delete_history(h))
            action_layout.addWidget(delete_btn)
            
            action_layout.addStretch()
            self._table.setCellWidget(row, 7, action_widget)
    
    def _update_stats(self) -> None:
        """更新统计信息"""
        normal_count = TestCaseHistory.get_normal_count()
        favorite_count = TestCaseHistory.get_favorite_count()
        self._normal_stats_label.setText(f"普通: {normal_count}/50")
        self._favorite_stats_label.setText(f"收藏: {favorite_count}")
    
    def _on_filter_changed(self) -> None:
        """筛选条件改变"""
        self._load_histories()
    
    def _toggle_favorite(self, history: TestCaseHistory) -> None:
        """切换收藏状态"""
        history.toggle_favorite()
        self._load_histories()
        _logger.info(f"历史记录 {'收藏' if history.is_favorite else '取消收藏'}: {history.name}")
    
    def _load_history(self, history: TestCaseHistory) -> None:
        """加载历史记录到测试用例页面"""
        reply = QMessageBox.question(
            self,
            "确认加载",
            f"确定要加载历史记录 '{history.name}' 吗？\n当前表格中的用例将被替换。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self._on_load_history:
                self._on_load_history(history)
            self.accept()
            _logger.info(f"加载历史记录: {history.name}")
    
    def _export_history(self, history: TestCaseHistory) -> None:
        """导出历史记录"""
        default_filename = f"test_case_history_{history.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出历史记录",
            str(Path.home() / default_filename),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            export_data = {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "type": "test_case_history"
                },
                "history": history.to_dict()
            }
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "成功", f"历史记录已导出到:\n{file_path}")
            _logger.info(f"导出历史记录成功: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
            _logger.error(f"导出历史记录失败: {str(e)}")
    
    def _import_history(self) -> None:
        """导入历史记录"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入历史记录",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                export_data = json.load(f)
            
            # 验证文件格式
            if "history" not in export_data:
                raise ValueError("无效的文件格式")
            
            history_data = export_data["history"]
            
            # 询问是否设置为收藏
            reply = QMessageBox.question(
                self,
                "导入设置",
                "是否将此记录标记为收藏？\n（收藏记录不受50条限制）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            
            is_favorite = reply == QMessageBox.StandardButton.Yes
            
            # 创建新的历史记录
            history = TestCaseHistory.from_dict(history_data)
            history.is_favorite = is_favorite
            
            # 生成新名称避免重复
            timestamp = datetime.now().strftime("%m%d_%H%M")
            history.name = f"{history.name}_导入_{timestamp}"
            
            history.save()
            
            self._load_histories()
            
            QMessageBox.information(
                self, 
                "成功", 
                f"历史记录导入成功！\n名称: {history.name}\n用例数: {len(history.test_cases)}"
            )
            _logger.info(f"导入历史记录成功: {history.name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
            _logger.error(f"导入历史记录失败: {str(e)}")
    
    def _delete_history(self, history: TestCaseHistory) -> None:
        """删除历史记录"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除历史记录 '{history.name}' 吗？\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            history.delete()
            self._load_histories()
            _logger.info(f"删除历史记录: {history.name}")
    
    def _show_context_menu(self, position) -> None:
        """显示右键菜单"""
        row = self._table.rowAt(position.y())
        if row < 0 or row >= len(self._histories):
            return
        
        history = self._histories[row]
        
        menu = QMenu(self)
        
        rename_action = menu.addAction("✏️ 重命名")
        rename_action.triggered.connect(lambda: self._rename_history(history))
        
        menu.addSeparator()
        
        favorite_action = menu.addAction("取消收藏" if history.is_favorite else "⭐ 收藏")
        favorite_action.triggered.connect(lambda: self._toggle_favorite(history))
        
        menu.addSeparator()
        
        load_action = menu.addAction("📂 加载到表格")
        load_action.triggered.connect(lambda: self._load_history(history))
        
        export_action = menu.addAction("📤 导出")
        export_action.triggered.connect(lambda: self._export_history(history))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(lambda: self._delete_history(history))
        
        menu.exec(self._table.viewport().mapToGlobal(position))
    
    def _rename_history(self, history: TestCaseHistory) -> None:
        """重命名历史记录"""
        new_name, ok = QInputDialog.getText(
            self,
            "重命名",
            "请输入新的名称:",
            QLineEdit.EchoMode.Normal,
            history.name
        )
        
        if ok and new_name.strip():
            history.name = new_name.strip()
            history.save()
            self._load_histories()
            _logger.info(f"重命名历史记录: {history.name}")
