"""
Welcome Screen - Modern first-time user experience
Shows on startup with quick actions and recent files
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor
import os
from pathlib import Path


class RecentFileItem(QFrame):
    """Single recent file item with hover effect"""
    clicked = pyqtSignal(str)

    def __init__(self, file_path: str, time_ago: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

        # Styling
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            RecentFileItem {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
            }
            RecentFileItem:hover {
                background-color: rgba(102, 126, 234, 0.2);
                border: 1px solid rgba(102, 126, 234, 0.5);
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # File icon
        icon_label = QLabel("📄")
        icon_label.setFont(QFont("Arial", 20))
        layout.addWidget(icon_label)

        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        filename = os.path.basename(file_path)
        name_label = QLabel(filename)
        name_label.setFont(QFont("Arial", 11, QFont.Bold))
        info_layout.addWidget(name_label)

        time_label = QLabel(time_ago)
        time_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 9px;")
        info_layout.addWidget(time_label)

        layout.addLayout(info_layout, stretch=1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)


class WelcomeScreen(QWidget):
    """Modern welcome screen shown on startup"""

    open_file_requested = pyqtSignal()
    open_project_requested = pyqtSignal()
    load_recent_requested = pyqtSignal(str)

    def __init__(self, recent_files=None, parent=None):
        super().__init__(parent)
        self.recent_files = recent_files or []
        self.init_ui()

    def init_ui(self):
        """Initialize the welcome screen UI"""
        # Main layout with centering
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Content container (centered, fixed width)
        content = QWidget()
        content.setMaximumWidth(600)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(30)
        content_layout.setContentsMargins(40, 40, 40, 40)

        # === HEADER ===
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(8)

        # App title
        title = QLabel("JSPR Beamer Setup")
        title.setFont(QFont("Arial", 32, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Paint-by-Numbers Generator")
        subtitle.setFont(QFont("Arial", 14))
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)

        content_layout.addLayout(header_layout)
        content_layout.addSpacing(20)

        # === PRIMARY ACTIONS ===
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)

        # Open Image button (primary)
        open_image_btn = QPushButton("Open Afbeelding")
        open_image_btn.setMinimumHeight(60)
        open_image_btn.setFont(QFont("Arial", 12, QFont.Bold))
        open_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #667EEA;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 16px 24px;
            }
            QPushButton:hover {
                background-color: #5568D3;
            }
            QPushButton:pressed {
                background-color: #4C5FC7;
            }
        """)
        open_image_btn.clicked.connect(self.open_file_requested.emit)
        actions_layout.addWidget(open_image_btn)

        # Open Project button (secondary)
        open_project_btn = QPushButton("Open Project")
        open_project_btn.setMinimumHeight(60)
        open_project_btn.setFont(QFont("Arial", 12))
        open_project_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 16px 24px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
        """)
        open_project_btn.clicked.connect(self.open_project_requested.emit)
        actions_layout.addWidget(open_project_btn)

        content_layout.addLayout(actions_layout)

        # === DROP ZONE ===
        drop_zone = QLabel("of sleep hier een afbeelding")
        drop_zone.setAlignment(Qt.AlignCenter)
        drop_zone.setMinimumHeight(80)
        drop_zone.setStyleSheet("""
            QLabel {
                border: 2px dashed rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.5);
                font-size: 12px;
                font-style: italic;
            }
        """)
        content_layout.addWidget(drop_zone)

        # === RECENT FILES ===
        if self.recent_files:
            content_layout.addSpacing(20)

            recent_label = QLabel("Recente Bestanden")
            recent_label.setFont(QFont("Arial", 13, QFont.Bold))
            recent_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
            content_layout.addWidget(recent_label)

            # Scroll area for recent files
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(200)
            scroll.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
            """)

            recent_widget = QWidget()
            recent_layout = QVBoxLayout(recent_widget)
            recent_layout.setSpacing(8)

            # Add recent file items
            for file_path, time_ago in self.recent_files[:5]:  # Max 5 recent
                item = RecentFileItem(file_path, time_ago)
                item.clicked.connect(self.load_recent_requested.emit)
                recent_layout.addWidget(item)

            recent_layout.addStretch()
            scroll.setWidget(recent_widget)
            content_layout.addWidget(scroll)

        content_layout.addStretch()

        # === FOOTER ===
        footer = QLabel("Versie 1.0 • JSPR")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 10px;")
        content_layout.addWidget(footer)

        main_layout.addWidget(content)
