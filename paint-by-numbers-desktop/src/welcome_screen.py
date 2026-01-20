"""
Welcome Screen - Modern first-time user experience
Shows on startup with quick actions and recent files
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QPainter, QIcon
import os
from pathlib import Path
import cv2
import numpy as np


class RecentProjectTile(QFrame):
    """Tile with thumbnail, name, date and remove button"""
    clicked = pyqtSignal(str)
    remove_requested = pyqtSignal(str)

    def __init__(self, file_path: str, last_opened: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

        # Styling
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            RecentProjectTile {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
            RecentProjectTile:hover {
                background-color: rgba(102, 126, 234, 0.15);
                border: 1px solid rgba(102, 126, 234, 0.4);
            }
        """)
        self.setFixedSize(180, 200)
        self.setCursor(Qt.PointingHandCursor)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Thumbnail container
        thumbnail_container = QFrame()
        thumbnail_container.setFixedSize(164, 120)
        thumbnail_container.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 4px;
            }
        """)

        thumb_layout = QVBoxLayout(thumbnail_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)

        # Thumbnail image
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFixedSize(164, 120)
        self.thumbnail_label.setScaledContents(False)

        # Load thumbnail
        thumbnail = self.load_thumbnail(file_path)
        if thumbnail:
            self.thumbnail_label.setPixmap(thumbnail)
        else:
            # Placeholder if no thumbnail
            self.thumbnail_label.setText("📷")
            self.thumbnail_label.setFont(QFont("Arial", 32))
            self.thumbnail_label.setStyleSheet("color: rgba(255, 255, 255, 0.3);")

        thumb_layout.addWidget(self.thumbnail_label)
        layout.addWidget(thumbnail_container)

        # File name
        filename = os.path.basename(file_path)
        if len(filename) > 20:
            filename = filename[:17] + "..."
        name_label = QLabel(filename)
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(32)
        layout.addWidget(name_label)

        # Last opened date
        date_label = QLabel(last_opened)
        date_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 9px;")
        date_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(date_label)

        # Remove button (X)
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 38, 38, 0.8);
                color: white;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 1);
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.file_path))
        self.remove_btn.hide()  # Hidden by default, shown on hover

        # Position remove button in top-right
        self.remove_btn.setParent(thumbnail_container)
        self.remove_btn.move(136, 4)

    def load_thumbnail(self, file_path: str) -> QPixmap:
        """Load or generate thumbnail for the project"""
        try:
            # Check if it's an image file directly
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                # Load image with OpenCV
                img = cv2.imread(file_path)
                if img is not None:
                    # Convert BGR to RGB
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                    # Resize to thumbnail size while maintaining aspect ratio
                    h, w = img_rgb.shape[:2]
                    target_w, target_h = 164, 120

                    # Calculate scaling
                    scale = min(target_w / w, target_h / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)

                    resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)

                    # Create black background
                    thumbnail = np.zeros((target_h, target_w, 3), dtype=np.uint8)

                    # Center the resized image
                    y_offset = (target_h - new_h) // 2
                    x_offset = (target_w - new_w) // 2
                    thumbnail[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

                    # Convert to QPixmap
                    h, w, ch = thumbnail.shape
                    bytes_per_line = ch * w
                    from PyQt5.QtGui import QImage
                    qt_image = QImage(thumbnail.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    return QPixmap.fromImage(qt_image)

            # TODO: For .jspr files, we could save a thumbnail with the project
            # For now, return None to show placeholder
            return None

        except Exception as e:
            print(f"Error loading thumbnail for {file_path}: {e}")
            return None

    def enterEvent(self, event):
        """Show remove button on hover"""
        self.remove_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide remove button when not hovering"""
        self.remove_btn.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle clicks on the tile (but not on remove button)"""
        if event.button() == Qt.LeftButton:
            # Check if click was on remove button
            if not self.remove_btn.geometry().contains(event.pos()):
                self.clicked.emit(self.file_path)


class WelcomeScreen(QWidget):
    """Modern welcome screen shown on startup"""

    open_file_requested = pyqtSignal()
    open_project_requested = pyqtSignal()
    load_recent_requested = pyqtSignal(str)
    remove_recent_requested = pyqtSignal(str)  # New signal for removing recent files

    def __init__(self, recent_files=None, parent=None):
        super().__init__(parent)
        self.recent_files = recent_files or []
        self.init_ui()

    def init_ui(self):
        """Initialize the welcome screen UI"""
        # Main layout with centering
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Content container (centered, wider for grid)
        content = QWidget()
        content.setMaximumWidth(700)  # Wider to fit 3 tiles
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

        # === RECENT PROJECTS GRID ===
        if self.recent_files:
            content_layout.addSpacing(20)

            recent_label = QLabel("Recente Projecten")
            recent_label.setFont(QFont("Arial", 13, QFont.Bold))
            recent_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
            content_layout.addWidget(recent_label)

            # Scroll area for recent projects grid
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(450)
            scroll.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
            """)

            recent_widget = QWidget()
            recent_grid = QGridLayout(recent_widget)
            recent_grid.setSpacing(12)
            recent_grid.setContentsMargins(0, 0, 0, 0)

            # Add recent project tiles in grid (3 columns)
            max_projects = 6  # Show max 6 recent projects
            for idx, (file_path, time_ago) in enumerate(self.recent_files[:max_projects]):
                row = idx // 3
                col = idx % 3

                tile = RecentProjectTile(file_path, time_ago)
                tile.clicked.connect(self.load_recent_requested.emit)
                tile.remove_requested.connect(self.remove_recent_requested.emit)
                recent_grid.addWidget(tile, row, col)

            # Add stretch to push tiles to top
            recent_grid.setRowStretch(100, 1)

            scroll.setWidget(recent_widget)
            content_layout.addWidget(scroll)

        content_layout.addStretch()

        # === FOOTER ===
        footer = QLabel("Versie 1.0 • JSPR")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 10px;")
        content_layout.addWidget(footer)

        main_layout.addWidget(content)
