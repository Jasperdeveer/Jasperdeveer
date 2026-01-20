"""
Collapsible Section Widget - Like Photoshop/Figma panels
Professional collapsible group box with smooth animations
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QLabel, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont


class CollapsibleSection(QWidget):
    """Collapsible section widget like in Photoshop"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.is_collapsed = False

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 8)

        # Header (always visible)
        self.header = QFrame()
        self.header.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 2px;
            }
            QFrame:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        self.header.setCursor(Qt.PointingHandCursor)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)

        # Toggle arrow
        self.toggle_btn = QLabel("▼")
        self.toggle_btn.setFont(QFont("Arial", 10))
        self.toggle_btn.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        self.toggle_btn.setFixedWidth(12)
        header_layout.addWidget(self.toggle_btn)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.95);")
        header_layout.addWidget(title_label, stretch=1)

        main_layout.addWidget(self.header)

        # Content container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(8)
        self.content_layout.setContentsMargins(16, 12, 8, 12)

        main_layout.addWidget(self.content_widget)

        # Connect click event
        self.header.mousePressEvent = self.toggle_collapsed

    def add_widget(self, widget):
        """Add widget to content area"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add layout to content area"""
        self.content_layout.addLayout(layout)

    def toggle_collapsed(self, event=None):
        """Toggle collapsed state"""
        self.is_collapsed = not self.is_collapsed

        if self.is_collapsed:
            self.toggle_btn.setText("▶")
            self.content_widget.hide()
        else:
            self.toggle_btn.setText("▼")
            self.content_widget.show()

    def set_collapsed(self, collapsed: bool):
        """Set collapsed state"""
        if collapsed != self.is_collapsed:
            self.toggle_collapsed()
