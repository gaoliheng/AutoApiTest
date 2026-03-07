from typing import Optional

from PyQt6.QtWidgets import QWidget


class StyleManager:
    _instance: Optional["StyleManager"] = None
    
    def __new__(cls) -> "StyleManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._styles = self._load_styles()
    
    def _load_styles(self) -> dict[str, str]:
        return {
            "main_window": """
                QMainWindow {
                    background-color: #f5f6fa;
                }
            """,
            "menu_bar": """
                QMenuBar {
                    background-color: #ffffff;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 5px;
                    font-size: 13px;
                }
                QMenuBar::item {
                    padding: 5px 10px;
                    background-color: transparent;
                    border-radius: 4px;
                }
                QMenuBar::item:selected {
                    background-color: #e3f2fd;
                }
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 8px 25px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #e3f2fd;
                }
            """,
            "toolbar": """
                QToolBar {
                    background-color: #ffffff;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 5px;
                    spacing: 5px;
                }
                QToolBar QToolButton {
                    padding: 8px 12px;
                    border-radius: 4px;
                    background-color: transparent;
                    border: none;
                    font-size: 13px;
                }
                QToolBar QToolButton:hover {
                    background-color: #e3f2fd;
                }
                QToolBar QToolButton:pressed {
                    background-color: #bbdefb;
                }
            """,
            "status_bar": """
                QStatusBar {
                    background-color: #ffffff;
                    border-top: 1px solid #e0e0e0;
                    font-size: 12px;
                    padding: 5px;
                }
            """,
            "navigation": """
                QListWidget {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 5px;
                    font-size: 14px;
                }
                QListWidget::item {
                    padding: 12px 15px;
                    border-radius: 6px;
                    margin: 2px 0;
                }
                QListWidget::item:selected {
                    background-color: #2196f3;
                    color: white;
                }
                QListWidget::item:hover:!selected {
                    background-color: #e3f2fd;
                }
            """,
            "tab_widget": """
                QTabWidget::pane {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background-color: #ffffff;
                }
                QTabBar::tab {
                    background-color: #f5f6fa;
                    border: 1px solid #e0e0e0;
                    border-bottom: none;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    padding: 10px 20px;
                    margin-right: 2px;
                    font-size: 13px;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    border-bottom: 1px solid #ffffff;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #e3f2fd;
                }
            """,
            "button_primary": """
                QPushButton {
                    background-color: #2196f3;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976d2;
                }
                QPushButton:pressed {
                    background-color: #1565c0;
                }
                QPushButton:disabled {
                    background-color: #bdbdbd;
                }
            """,
            "button_secondary": """
                QPushButton {
                    background-color: #ffffff;
                    color: #424242;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #f5f6fa;
                    border-color: #bdbdbd;
                }
                QPushButton:pressed {
                    background-color: #e0e0e0;
                }
                QPushButton:disabled {
                    background-color: #f5f6fa;
                    color: #9e9e9e;
                }
            """,
            "button_danger": """
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
                QPushButton:pressed {
                    background-color: #c62828;
                }
            """,
            "input": """
                QLineEdit, QTextEdit, QPlainTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
                QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                    border-color: #2196f3;
                }
                QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
                    background-color: #f5f6fa;
                    color: #9e9e9e;
                }
            """,
            "combobox": """
                QComboBox {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 14px;
                    min-width: 150px;
                }
                QComboBox:hover {
                    border-color: #bdbdbd;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 30px;
                }
                QComboBox::down-arrow {
                    width: 12px;
                    height: 12px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    selection-background-color: #e3f2fd;
                    selection-color: #424242;
                }
            """,
            "table": """
                QTableWidget {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    gridline-color: #f5f6fa;
                    font-size: 13px;
                }
                QTableWidget::item {
                    padding: 8px;
                }
                QTableWidget::item:selected {
                    background-color: #e3f2fd;
                    color: #424242;
                }
                QHeaderView::section {
                    background-color: #f5f6fa;
                    border: none;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 10px;
                    font-weight: bold;
                    font-size: 13px;
                }
            """,
            "list_widget": """
                QListWidget {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 5px;
                    font-size: 13px;
                }
                QListWidget::item {
                    padding: 10px;
                    border-radius: 4px;
                }
                QListWidget::item:selected {
                    background-color: #e3f2fd;
                    color: #424242;
                }
                QListWidget::item:hover:!selected {
                    background-color: #f5f6fa;
                }
            """,
            "group_box": """
                QGroupBox {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    margin-top: 15px;
                    padding-top: 10px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 10px;
                    color: #424242;
                }
            """,
            "progress_bar": """
                QProgressBar {
                    background-color: #f5f6fa;
                    border: none;
                    border-radius: 4px;
                    text-align: center;
                    font-size: 12px;
                    height: 20px;
                }
                QProgressBar::chunk {
                    background-color: #2196f3;
                    border-radius: 4px;
                }
            """,
            "scroll_area": """
                QScrollArea {
                    background-color: transparent;
                    border: none;
                }
                QScrollArea > QWidget > QWidget {
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    background-color: #f5f6fa;
                    width: 12px;
                    border-radius: 6px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background-color: #bdbdbd;
                    border-radius: 6px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #9e9e9e;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0;
                }
            """,
            "label": """
                QLabel {
                    color: #424242;
                    font-size: 14px;
                }
            """,
            "checkbox": """
                QCheckBox {
                    spacing: 8px;
                    font-size: 14px;
                    color: #424242;
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
                QCheckBox::indicator:hover {
                    border-color: #2196f3;
                }
            """,
            "radio_button": """
                QRadioButton {
                    spacing: 8px;
                    font-size: 14px;
                    color: #424242;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 9px;
                    border: 2px solid #bdbdbd;
                }
                QRadioButton::indicator:checked {
                    background-color: #2196f3;
                    border-color: #2196f3;
                }
                QRadioButton::indicator:hover {
                    border-color: #2196f3;
                }
            """,
            "spinbox": """
                QSpinBox, QDoubleSpinBox {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
                QSpinBox:focus, QDoubleSpinBox:focus {
                    border-color: #2196f3;
                }
            """,
        }
    
    def get_style(self, name: str) -> str:
        return self._styles.get(name, "")
    
    def apply_style(self, widget: QWidget, style_name: str) -> None:
        style = self.get_style(style_name)
        if style:
            widget.setStyleSheet(style)
    
    def get_combined_style(self, *style_names: str) -> str:
        return "\n".join(self.get_style(name) for name in style_names)


style_manager = StyleManager()
