"""
Status Indicator Widget - Shows workflow progress and current state
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class StatusIndicator(QWidget):
    """Visual status indicator showing workflow progress"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.status_items = {}
        self.init_ui()

    def init_ui(self):
        """Initialize the status indicator UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel("Status")
        header.setFont(QFont("Arial", 11, QFont.Bold))
        header.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        layout.addWidget(header)

        # Status items container
        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(4)
        layout.addLayout(self.items_layout)

        # Define status steps
        self.add_status_item("image_loaded", "Afbeelding geladen", False)
        self.add_status_item("colors_detected", "Kleuren gedetecteerd", False)
        self.add_status_item("rendered", "Paint-by-numbers gegenereerd", False)
        self.add_status_item("exported", "Geëxporteerd", False)

        layout.addStretch()

        # Styling
        self.setStyleSheet("""
            StatusIndicator {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
        """)
        self.setMaximumWidth(250)

    def add_status_item(self, key: str, text: str, completed: bool = False):
        """Add a status item to the indicator"""
        item_layout = QHBoxLayout()
        item_layout.setSpacing(8)

        # Status icon
        icon = QLabel("✓" if completed else "○")
        icon.setFont(QFont("Arial", 12, QFont.Bold))
        icon.setFixedWidth(20)
        if completed:
            icon.setStyleSheet("color: #4CAF50;")
        else:
            icon.setStyleSheet("color: rgba(255, 255, 255, 0.3);")

        item_layout.addWidget(icon)

        # Status text
        label = QLabel(text)
        label.setFont(QFont("Arial", 10))
        if completed:
            label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        else:
            label.setStyleSheet("color: rgba(255, 255, 255, 0.5);")

        item_layout.addWidget(label, stretch=1)

        # Store references
        self.status_items[key] = {
            'icon': icon,
            'label': label,
            'completed': completed
        }

        self.items_layout.addLayout(item_layout)

    def set_status(self, key: str, completed: bool):
        """Update a status item"""
        if key in self.status_items:
            item = self.status_items[key]
            item['completed'] = completed

            if completed:
                item['icon'].setText("✓")
                item['icon'].setStyleSheet("color: #4CAF50;")
                item['label'].setStyleSheet("color: rgba(255, 255, 255, 0.9);")
            else:
                item['icon'].setText("○")
                item['icon'].setStyleSheet("color: rgba(255, 255, 255, 0.3);")
                item['label'].setStyleSheet("color: rgba(255, 255, 255, 0.5);")

    def get_status(self, key: str) -> bool:
        """Get the status of an item"""
        if key in self.status_items:
            return self.status_items[key]['completed']
        return False

    def reset(self):
        """Reset all statuses"""
        for key in self.status_items:
            self.set_status(key, False)
