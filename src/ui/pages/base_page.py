from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)


class BasePage(QWidget):
    def __init__(self, title: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._title = title
        self._init_ui()
    
    def _init_ui(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(15, 15, 15, 15)
        self._main_layout.setSpacing(12)
    
    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        self._main_layout.addWidget(widget, stretch)
    
    def add_layout(self, layout: QHBoxLayout | QVBoxLayout) -> None:
        self._main_layout.addLayout(layout)
    
    def add_stretch(self) -> None:
        self._main_layout.addStretch()
    
    def refresh(self) -> None:
        pass
