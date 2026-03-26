from typing import Optional
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QStyle
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QLabel,
    QPushButton,
)

from ui.styles import style_manager
from ui.pages import (
    AIModelPage,
    TestCasePage,
    TestScriptPage,
    AuthConfigPage,
)
from models.ai_model import AIModel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._init_window()
        self._init_statusbar()
        self._init_central_widget()
        self._apply_styles()
        self._update_ai_model_status()
    
    def _init_window(self) -> None:
        self.setWindowTitle("AutoApiTest - API 自动化测试工具")
        self.setMinimumSize(1280, 800)
        self.resize(1400, 900)

        icon_path = Path(__file__).parent.parent.parent / "data" / "app_icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                icon = QIcon(pixmap)
                self.setWindowIcon(icon)
    
    def _init_statusbar(self) -> None:
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        self._status_label = QLabel("就绪")
        statusbar.addWidget(self._status_label, 1)
        
        self._ai_model_status = QLabel("AI 模型: 未配置")
        statusbar.addPermanentWidget(self._ai_model_status)
    
    def _init_central_widget(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter {
                border: none;
            }
            QSplitter::handle {
                background-color: transparent;
                border: none;
            }
            QSplitter::handle:horizontal {
                width: 4px;
                background-color: transparent;
                border: none;
            }
        """)
        main_layout.addWidget(splitter)
        
        nav_widget = self._create_navigation_widget()
        splitter.addWidget(nav_widget)
        
        content_widget = self._create_content_widget()
        splitter.addWidget(content_widget)
        
        splitter.setSizes([180, 1100])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
    
    def _create_navigation_widget(self) -> QWidget:
        nav_widget = QWidget()
        nav_widget.setFixedWidth(180)
        nav_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: none;
                outline: none;
            }
        """)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(8, 15, 8, 10)
        nav_layout.setSpacing(0)

        self._nav_list = QListWidget()
        self._nav_list.setFrameStyle(0)  # 移除边框
        self._nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 移除焦点
        self._nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 隐藏滚动条
        self._nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        style_manager.apply_style(self._nav_list, "navigation")

        nav_items = [
            ("AI 模型配置", 0, QStyle.StandardPixmap.SP_ComputerIcon),
            ("登录接口配置", 1, QStyle.StandardPixmap.SP_DialogYesButton),
            ("单接口测试用例", 2, QStyle.StandardPixmap.SP_FileDialogDetailedView),
            ("单接口测试脚本", 3, QStyle.StandardPixmap.SP_FileDialogContentsView),
        ]

        for text, index, icon_type in nav_items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setIcon(self.style().standardIcon(icon_type))
            self._nav_list.addItem(item)

        self._nav_list.setCurrentRow(0)
        self._nav_list.currentRowChanged.connect(self._on_nav_changed)

        nav_layout.addWidget(self._nav_list)

        # 底部关于按钮
        nav_layout.addStretch()
        about_btn = QPushButton("关于")
        about_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        about_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #757575;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                color: #424242;
            }
        """)
        about_btn.clicked.connect(self._on_about)
        nav_layout.addWidget(about_btn)

        return nav_widget
    
    def _create_content_widget(self) -> QWidget:
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.setTabsClosable(False)
        style_manager.apply_style(self._tab_widget, "tab_widget")
        
        self._ai_model_page = AIModelPage(self._on_model_changed)
        self._auth_config_page = AuthConfigPage()
        self._test_case_page = TestCasePage()
        self._test_script_page = TestScriptPage()
        
        self._tab_widget.addTab(self._ai_model_page, "AI 模型配置")
        self._tab_widget.addTab(self._auth_config_page, "登录接口配置")
        self._tab_widget.addTab(self._test_case_page, "单接口测试用例")
        self._tab_widget.addTab(self._test_script_page, "单接口测试脚本")
        
        self._tab_widget.tabBar().hide()
        
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        
        content_layout.addWidget(self._tab_widget)
        
        return content_widget
    
    def _apply_styles(self) -> None:
        self.setStyleSheet(style_manager.get_combined_style(
            "main_window",
            "menu_bar",
            "status_bar"
        ))
    
    def _on_nav_changed(self, current_row: int) -> None:
        self._tab_widget.setCurrentIndex(current_row)
    
    def _on_tab_changed(self, index: int) -> None:
        self._nav_list.setCurrentRow(index)
        current_page = self._tab_widget.widget(index)
        if hasattr(current_page, 'refresh'):
            current_page.refresh()
        self._update_ai_model_status()
    
    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 AutoApiTest",
            """<h3>AutoApiTest v1.0.0</h3>
            <p>API 自动化测试工具</p>
            <p>基于 AI 的智能测试用例生成和测试脚本生成工具</p>
            <p>© 2024 AutoApiTest Team</p>"""
        )
    
    def set_status(self, message: str) -> None:
        self._status_label.setText(message)
    
    def _update_ai_model_status(self) -> None:
        default_model = AIModel.get_default()
        if default_model:
            self._ai_model_status.setText(f"AI 模型: {default_model.name}")
        else:
            self._ai_model_status.setText("AI 模型: 未配置")
    
    def _on_model_changed(self) -> None:
        self._update_ai_model_status()
    
    def refresh_all_pages(self) -> None:
        for i in range(self._tab_widget.count()):
            page = self._tab_widget.widget(i)
            if hasattr(page, 'refresh'):
                page.refresh()
