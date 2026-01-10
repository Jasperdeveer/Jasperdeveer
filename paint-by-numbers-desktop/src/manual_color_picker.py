"""
Manual Color Picker - Interactive fullscreen color selection
Allows manual color palette creation with visual feedback
"""

import numpy as np
import cv2
from typing import List, Optional, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QFont, QCursor
import logging

from color_naming import get_color_name, are_colors_similar, calculate_color_distance
from color_manager import Color

logger = logging.getLogger(__name__)


class ColorSelectionDialog(QDialog):
    """Dialog to choose between automatic and manual color selection"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selection_mode = None  # 'automatic' or 'manual'
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Kleur Selectie Methode")
        self.setModal(True)
        self.setFixedSize(500, 300)

        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Title
        title = QLabel("<h2>Hoe wil je de kleuren selecteren?</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Kies tussen automatische detectie of handmatige selectie met de pipet."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(10)

        # Buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)

        # Automatic button
        auto_btn = QPushButton("🤖 Automatisch")
        auto_btn.setMinimumHeight(60)
        auto_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(100, 150, 255, 200),
                    stop:1 rgba(150, 100, 255, 200));
                border: 2px solid rgba(255, 255, 255, 100);
                border-radius: 10px;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(120, 170, 255, 230),
                    stop:1 rgba(170, 120, 255, 230));
            }
        """)
        auto_btn.clicked.connect(self.select_automatic)
        button_layout.addWidget(auto_btn)

        # Manual button
        manual_btn = QPushButton("🎨 Handmatig (Pipet)")
        manual_btn.setMinimumHeight(60)
        manual_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 100, 150, 200),
                    stop:1 rgba(255, 150, 100, 200));
                border: 2px solid rgba(255, 255, 255, 100);
                border-radius: 10px;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 120, 170, 230),
                    stop:1 rgba(255, 170, 120, 230));
            }
        """)
        manual_btn.clicked.connect(self.select_manual)
        button_layout.addWidget(manual_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        self.setLayout(layout)

    def select_automatic(self):
        """Select automatic mode"""
        logger.info("User selected AUTOMATIC color detection")
        self.selection_mode = 'automatic'
        self.accept()

    def select_manual(self):
        """Select manual mode"""
        logger.info("User selected MANUAL color picker")
        self.selection_mode = 'manual'
        self.accept()


class ManualColorPicker(QWidget):
    """Fullscreen manual color picker with flood fill selection"""

    # Signals
    colors_selected = pyqtSignal(list)  # List of Color objects
    cancelled = pyqtSignal()

    def __init__(self, original_image: np.ndarray, parent=None):
        super().__init__(parent)

        # Set window flags to make it a standalone window
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        self.original_image = original_image.copy()
        self.working_image = original_image.copy()
        self.display_image = original_image.copy()

        # State
        self.selected_colors: List[Color] = []
        self.color_history: List[Tuple[Color, np.ndarray]] = []  # For undo: (color, mask)
        self.tolerance = 20  # Color tolerance for flood fill
        self.merge_threshold = 30  # Threshold for suggesting merge

        # Mask of selected pixels
        self.selection_mask = np.zeros(original_image.shape[:2], dtype=bool)

        self.init_ui()

        logger.info("ManualColorPicker initialized")

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Handmatige Kleur Selectie - Klik op kleuren om toe te voegen")
        self.setStyleSheet("background-color: black;")
        self.setCursor(QCursor(Qt.CrossCursor))

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar for palette
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        # Center: Image canvas (will be drawn in paintEvent)
        canvas = QWidget()
        canvas.setMinimumSize(800, 600)
        main_layout.addWidget(canvas, stretch=1)

    def create_sidebar(self) -> QWidget:
        """Create left sidebar with palette and controls"""
        sidebar = QWidget()
        sidebar.setFixedWidth(350)
        sidebar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(20, 20, 20, 250),
                    stop:1 rgba(40, 40, 40, 250));
                border-right: 2px solid rgba(255, 255, 255, 50);
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title = QLabel("<h2>🎨 Kleuren Palet</h2>")
        title.setStyleSheet("color: white; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Stats
        self.stats_label = QLabel("Klik op de afbeelding om te beginnen")
        self.stats_label.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

        # Tolerance slider
        tolerance_layout = QVBoxLayout()
        tolerance_label = QLabel(f"Tolerantie: {self.tolerance}")
        tolerance_label.setStyleSheet("color: white; background: transparent;")
        self.tolerance_label = tolerance_label
        tolerance_layout.addWidget(tolerance_label)

        tolerance_slider = QSlider(Qt.Horizontal)
        tolerance_slider.setRange(5, 50)
        tolerance_slider.setValue(self.tolerance)
        tolerance_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 50);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #45a049);
                border: 2px solid white;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
        """)
        tolerance_slider.valueChanged.connect(self.on_tolerance_changed)
        tolerance_layout.addWidget(tolerance_slider)
        layout.addLayout(tolerance_layout)

        # Color list (scrollable)
        from PyQt5.QtWidgets import QScrollArea
        self.color_list_widget = QWidget()
        self.color_list_layout = QVBoxLayout(self.color_list_widget)
        self.color_list_layout.setSpacing(5)
        self.color_list_widget.setStyleSheet("background: transparent;")

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.color_list_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 20);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 100);
                border-radius: 5px;
            }
        """)
        layout.addWidget(scroll_area, stretch=1)

        # Control buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)

        # Undo button
        undo_btn = QPushButton("↶ Ongedaan maken")
        undo_btn.setMinimumHeight(40)
        undo_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 152, 0, 180);
                color: white;
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 152, 0, 220);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """)
        undo_btn.clicked.connect(self.undo_last_color)
        self.undo_btn = undo_btn
        button_layout.addWidget(undo_btn)

        # Done button
        done_btn = QPushButton("✓ Klaar")
        done_btn.setMinimumHeight(50)
        done_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(76, 175, 80, 200),
                    stop:1 rgba(69, 160, 73, 200));
                color: white;
                border: 2px solid rgba(255, 255, 255, 150);
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(86, 185, 90, 230),
                    stop:1 rgba(79, 170, 83, 230));
            }
        """)
        done_btn.clicked.connect(self.finish_selection)
        button_layout.addWidget(done_btn)

        # Cancel button
        cancel_btn = QPushButton("✕ Annuleren")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(244, 67, 54, 180);
                color: white;
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(244, 67, 54, 220);
            }
        """)
        cancel_btn.clicked.connect(self.cancel_selection)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        return sidebar

    def on_tolerance_changed(self, value: int):
        """Handle tolerance slider change"""
        self.tolerance = value
        self.tolerance_label.setText(f"Tolerantie: {value}")

    def update_color_list(self):
        """Update the color palette display"""
        # Clear existing
        while self.color_list_layout.count():
            child = self.color_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add color items
        for color in self.selected_colors:
            item = self.create_color_item(color)
            self.color_list_layout.addWidget(item)

        self.color_list_layout.addStretch()

        # Update stats
        if self.selected_colors:
            total_pixels = self.original_image.shape[0] * self.original_image.shape[1]
            selected_pixels = np.sum(self.selection_mask)
            coverage = (selected_pixels / total_pixels) * 100
            self.stats_label.setText(
                f"{len(self.selected_colors)} kleuren geselecteerd\n"
                f"{coverage:.1f}% van afbeelding"
            )
        else:
            self.stats_label.setText("Klik op de afbeelding om te beginnen")

        # Update undo button
        self.undo_btn.setEnabled(len(self.color_history) > 0)

    def create_color_item(self, color: Color) -> QWidget:
        """Create a color item widget for the palette"""
        item = QWidget()
        layout = QHBoxLayout(item)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Number
        num_label = QLabel(f"<b>{color.number}</b>")
        num_label.setFixedWidth(30)
        num_label.setStyleSheet("color: white; background: transparent; font-size: 14px;")
        layout.addWidget(num_label)

        # Color swatch
        swatch = QLabel()
        swatch.setFixedSize(40, 40)
        swatch.setStyleSheet(f"""
            background-color: {color.to_hex()};
            border: 2px solid white;
            border-radius: 4px;
        """)
        layout.addWidget(swatch)

        # Color info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(color.name)
        name_label.setStyleSheet("color: white; background: transparent; font-weight: bold;")
        info_layout.addWidget(name_label)

        rgb_label = QLabel(f"RGB({color.r}, {color.g}, {color.b})")
        rgb_label.setStyleSheet("color: #aaa; background: transparent; font-size: 10px;")
        info_layout.addWidget(rgb_label)

        layout.addLayout(info_layout, stretch=1)

        item.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 30);
                border-radius: 6px;
            }
        """)

        return item

    def mousePressEvent(self, event):
        """Handle mouse click on image"""
        if event.button() != Qt.LeftButton:
            return

        # Get click position relative to displayed image
        click_pos = event.pos()

        # Calculate image position and scale
        height, width = self.display_image.shape[:2]
        widget_width = self.width() - 350  # Minus sidebar
        widget_height = self.height()

        # Calculate scaled size (fit to window)
        scale = min(widget_width / width, widget_height / height)
        scaled_width = int(width * scale)
        scaled_height = int(height * scale)

        # Calculate image offset
        x_offset = 350 + (widget_width - scaled_width) // 2
        y_offset = (widget_height - scaled_height) // 2

        # Convert to image coordinates
        img_x = int((click_pos.x() - x_offset) / scale)
        img_y = int((click_pos.y() - y_offset) / scale)

        # Check bounds
        if 0 <= img_x < width and 0 <= img_y < height:
            # Check if clicking on already selected pixel
            if self.selection_mask[img_y, img_x]:
                logger.info("Clicked on already selected pixel, ignoring")
                return

            # Get clicked color
            r, g, b = self.working_image[img_y, img_x]
            self.select_color_at_pixel(img_x, img_y, r, g, b)

    def select_color_at_pixel(self, x: int, y: int, r: int, g: int, b: int):
        """Select all similar pixels and add color to palette"""
        logger.info(f"Selecting color RGB({r}, {g}, {b}) at pixel ({x}, {y})")

        # Check for similar existing colors
        similar_color = None
        merge_with_existing = False

        for existing_color in self.selected_colors:
            if are_colors_similar(r, g, b, existing_color.r, existing_color.g, existing_color.b, self.merge_threshold):
                similar_color = existing_color
                break

        if similar_color:
            # Ask user if they want to merge
            msg = QMessageBox(self)
            msg.setWindowTitle("Vergelijkbare kleur gevonden")
            msg.setText(f"Deze kleur lijkt op '{similar_color.name}'")
            msg.setInformativeText("Wil je deze kleuren samenvoegen?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)

            result = msg.exec_()
            if result == QMessageBox.Yes:
                # Merge - use the existing color but select similar pixels
                merge_with_existing = True
                logger.info(f"Merging with existing color: {similar_color.name}")
                r, g, b = similar_color.r, similar_color.g, similar_color.b

        # Perform flood fill to find all similar pixels
        mask = self.flood_fill_similar_pixels(r, g, b)

        # Check if any pixels were selected
        if not np.any(mask):
            logger.warning("No similar pixels found")
            return

        # Create new color (or use existing if merging)
        if merge_with_existing and similar_color:
            # Don't add a new color, just update the mask
            new_color = similar_color
        else:
            # Generate intelligent color name
            color_name = get_color_name(r, g, b)
            new_color = Color(r, g, b, len(self.selected_colors) + 1, color_name)
            self.selected_colors.append(new_color)

        # Save for undo
        self.color_history.append((new_color, mask.copy()))

        # Update selection mask
        self.selection_mask |= mask

        # Apply hatching to selected pixels
        self.apply_hatching(mask)

        # Update display
        self.update_color_list()
        self.update_display_image()
        self.update()

        logger.info(f"Added color: {new_color.name} ({np.sum(mask)} pixels)")

    def flood_fill_similar_pixels(self, r: int, g: int, b: int) -> np.ndarray:
        """
        Find all similar pixels in the entire image using color tolerance

        Returns:
            Boolean mask of similar pixels
        """
        height, width = self.working_image.shape[:2]
        mask = np.zeros((height, width), dtype=bool)

        # Vectorized approach for speed
        img = self.working_image.astype(np.int16)  # Convert to int16 to avoid overflow

        # Calculate color distance for all pixels
        dr = np.abs(img[:, :, 0] - r)
        dg = np.abs(img[:, :, 1] - g)
        db = np.abs(img[:, :, 2] - b)

        # Simple RGB distance
        distance = np.sqrt(dr**2 + dg**2 + db**2)

        # Select pixels within tolerance that aren't already selected
        mask = (distance <= self.tolerance) & (~self.selection_mask)

        return mask

    def apply_hatching(self, mask: np.ndarray):
        """Apply gray hatching pattern to selected pixels"""
        height, width = mask.shape

        # Create hatching pattern (diagonal lines)
        hatching = np.zeros((height, width, 3), dtype=np.uint8)
        hatching[:, :] = [128, 128, 128]  # Gray base

        # Add diagonal line pattern (every 4th pixel)
        for i in range(height):
            for j in range(width):
                if (i + j) % 4 == 0 or (i + j) % 4 == 1:
                    hatching[i, j] = [90, 90, 90]  # Darker gray lines

        # Apply hatching where mask is True
        self.working_image[mask] = hatching[mask]

    def update_display_image(self):
        """Update the display image for rendering"""
        self.display_image = self.working_image.copy()

    def undo_last_color(self):
        """Undo the last color selection"""
        if not self.color_history:
            return

        # Get last color and mask
        last_color, last_mask = self.color_history.pop()

        # Remove from selected colors
        if last_color in self.selected_colors:
            self.selected_colors.remove(last_color)

        # Restore original pixels
        self.working_image[last_mask] = self.original_image[last_mask]

        # Update selection mask
        self.selection_mask[last_mask] = False

        # Update display
        self.update_color_list()
        self.update_display_image()
        self.update()

        logger.info(f"Undone color: {last_color.name}")

    def finish_selection(self):
        """Finish color selection and emit selected colors"""
        if not self.selected_colors:
            QMessageBox.warning(
                self,
                "Geen kleuren",
                "Selecteer minimaal één kleur voordat je klikt op Klaar"
            )
            return

        logger.info(f"Finished manual color selection: {len(self.selected_colors)} colors")
        self.colors_selected.emit(self.selected_colors)
        self.close()

    def cancel_selection(self):
        """Cancel color selection"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Annuleren")
        msg.setText("Weet je zeker dat je wilt annuleren?")
        msg.setInformativeText("Alle geselecteerde kleuren gaan verloren.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        if msg.exec_() == QMessageBox.Yes:
            logger.info("Manual color selection cancelled")
            self.cancelled.emit()
            self.close()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            self.cancel_selection()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.finish_selection()
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.undo_last_color()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """Paint the canvas with the image"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        if self.display_image is not None:
            # Convert numpy array to QImage
            height, width, channel = self.display_image.shape
            bytes_per_line = 3 * width

            q_image = QImage(
                self.display_image.data,
                width,
                height,
                bytes_per_line,
                QImage.Format_RGB888
            )

            # Calculate scaled size (fit to window, leaving room for sidebar)
            widget_width = self.width() - 350
            widget_height = self.height()

            scale = min(widget_width / width, widget_height / height)
            scaled_width = int(width * scale)
            scaled_height = int(height * scale)

            # Center image
            x_offset = 350 + (widget_width - scaled_width) // 2
            y_offset = (widget_height - scaled_height) // 2

            # Draw scaled image
            from PyQt5.QtCore import QRect
            target_rect = QRect(x_offset, y_offset, scaled_width, scaled_height)
            painter.drawImage(target_rect, q_image)
