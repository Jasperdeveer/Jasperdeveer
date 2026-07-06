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


class ImageCanvas(QWidget):
    """Canvas widget for displaying and interacting with the image"""

    # Signal emitted when image is clicked: (img_x, img_y)
    image_clicked = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.display_image = None
        self.setMinimumSize(800, 600)
        self.setCursor(QCursor(Qt.CrossCursor))
        self.last_scale = 1.0
        self.last_offset_x = 0
        self.last_offset_y = 0

        # Magnifier settings
        self.show_magnifier = True
        self.magnifier_size = 100
        self.magnifier_grid_size = 5
        self.current_mouse_pos = None

        # Enable mouse tracking for magnifier
        self.setMouseTracking(True)

    def set_image(self, image: np.ndarray):
        """Set the image to display"""
        self.display_image = image
        self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move for magnifier"""
        self.current_mouse_pos = event.pos()
        self.update()

    def mousePressEvent(self, event):
        """Handle mouse clicks on the canvas"""
        if event.button() != Qt.LeftButton or self.display_image is None:
            return

        # Get click position
        click_pos = event.pos()

        # Get image dimensions
        height, width = self.display_image.shape[:2]

        # Convert widget coordinates to image coordinates using last known scale
        img_x = int((click_pos.x() - self.last_offset_x) / self.last_scale)
        img_y = int((click_pos.y() - self.last_offset_y) / self.last_scale)

        # Check bounds and emit signal
        if 0 <= img_x < width and 0 <= img_y < height:
            logger.info(f"Canvas clicked at widget ({click_pos.x()}, {click_pos.y()}) -> image ({img_x}, {img_y})")
            self.image_clicked.emit(img_x, img_y)
        else:
            logger.debug(f"Click outside image bounds: ({img_x}, {img_y})")

    def paintEvent(self, event):
        """Paint the image"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        if self.display_image is not None:
            try:
                # Ensure image is contiguous in memory
                display_img = np.ascontiguousarray(self.display_image)

                height, width, channel = display_img.shape
                bytes_per_line = 3 * width

                # Convert numpy array to QImage
                q_image = QImage(
                    display_img.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format_RGB888
                )

                # Calculate scaled size (fit to widget)
                widget_width = self.width()
                widget_height = self.height()

                scale = min(widget_width / width, widget_height / height)
                scaled_width = int(width * scale)
                scaled_height = int(height * scale)

                # Center image in widget
                x_offset = (widget_width - scaled_width) // 2
                y_offset = (widget_height - scaled_height) // 2

                # Store for coordinate conversion in mouse events
                self.last_scale = scale
                self.last_offset_x = x_offset
                self.last_offset_y = y_offset

                # Draw scaled image
                from PyQt5.QtCore import QRect
                target_rect = QRect(x_offset, y_offset, scaled_width, scaled_height)
                painter.drawImage(target_rect, q_image)

                # Draw magnifier on top
                if self.show_magnifier and self.current_mouse_pos:
                    self.draw_magnifier(painter)

                logger.debug(f"Canvas painted image: {width}x{height} at ({x_offset}, {y_offset}), scale: {scale:.2f}")
            except Exception as e:
                logger.error(f"Error painting image: {e}", exc_info=True)
                # Draw error message
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(self.rect(), Qt.AlignCenter, f"Error: {str(e)}")

    def draw_magnifier(self, painter: QPainter):
        """Draw circular magnifier showing 5x5 pixel grid at cursor position"""
        from PyQt5.QtCore import QRectF, QPointF
        from PyQt5.QtGui import QPainterPath

        if self.display_image is None:
            return

        # Get original image from parent
        parent = self.parent()
        if not hasattr(parent, 'original_image'):
            return

        original_image = parent.original_image

        # Get cursor position in image coordinates
        cursor_x = self.current_mouse_pos.x()
        cursor_y = self.current_mouse_pos.y()

        # Convert to image coordinates
        img_x = int((cursor_x - self.last_offset_x) / self.last_scale)
        img_y = int((cursor_y - self.last_offset_y) / self.last_scale)

        # Check bounds
        height, width = original_image.shape[:2]
        if not (0 <= img_x < width and 0 <= img_y < height):
            return

        # Sample 5x5 grid around cursor
        grid_half = self.magnifier_grid_size // 2
        sample_x_start = max(0, img_x - grid_half)
        sample_y_start = max(0, img_y - grid_half)
        sample_x_end = min(width, img_x + grid_half + 1)
        sample_y_end = min(height, img_y + grid_half + 1)

        # Extract sample region
        sample_region = original_image[sample_y_start:sample_y_end, sample_x_start:sample_x_end]
        if sample_region.size == 0:
            return

        # Make contiguous
        sample_region = np.ascontiguousarray(sample_region)

        # Convert to QImage
        sample_height, sample_width = sample_region.shape[:2]
        bytes_per_line = 3 * sample_width
        sample_qimage = QImage(
            sample_region.data,
            sample_width,
            sample_height,
            bytes_per_line,
            QImage.Format_RGB888
        )

        # Position magnifier
        mag_offset_x = 20
        mag_offset_y = -120
        mag_x = cursor_x + mag_offset_x
        mag_y = cursor_y + mag_offset_y

        # Keep within bounds
        if mag_x + self.magnifier_size > self.width():
            mag_x = cursor_x - self.magnifier_size - mag_offset_x
        if mag_y < 0:
            mag_y = cursor_y + mag_offset_x

        # Save painter state
        painter.save()

        # Create circular clip
        circle_path = QPainterPath()
        circle_center = QPointF(mag_x + self.magnifier_size / 2, mag_y + self.magnifier_size / 2)
        circle_path.addEllipse(circle_center, self.magnifier_size / 2, self.magnifier_size / 2)
        painter.setClipPath(circle_path)

        # Draw magnified sample
        mag_rect = QRectF(mag_x, mag_y, self.magnifier_size, self.magnifier_size)
        painter.drawImage(mag_rect, sample_qimage)

        # Remove clip for border
        painter.setClipping(False)

        # Draw black border
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(circle_center, self.magnifier_size / 2, self.magnifier_size / 2)

        painter.restore()


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

        # Step-based selection state
        self.current_step = 'SELECTING_BLACK'  # SELECTING_BLACK -> SELECTING_WHITE -> SELECTING_COLORS
        self.black_colors: List[Color] = []
        self.white_colors: List[Color] = []

        # Mask of selected pixels
        self.selection_mask = np.zeros(original_image.shape[:2], dtype=bool)

        logger.info(f"ManualColorPicker: Image shape: {self.original_image.shape}, dtype: {self.original_image.dtype}")

        self.init_ui()

        logger.info("ManualColorPicker initialized")

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Handmatige Kleur Selectie - Klik op kleuren om toe te voegen")
        self.setStyleSheet("background-color: black;")

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar for palette
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        # Right side: Image canvas
        self.canvas = ImageCanvas(self)
        self.canvas.set_image(self.display_image)
        self.canvas.image_clicked.connect(self.on_canvas_clicked)
        main_layout.addWidget(self.canvas, stretch=1)

        # Force initial paint
        logger.info("init_ui complete, image canvas created")
        self.canvas.update()

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

        # Instruction label (shows current step)
        self.instruction_label = QLabel("STAP 1: Selecteer alle zwarte gebieden")
        self.instruction_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
            background: rgba(76, 175, 80, 150);
            padding: 10px;
            border-radius: 5px;
        """)
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)

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

        # Skip button (for black/white steps)
        skip_btn = QPushButton("→ Overslaan")
        skip_btn.setMinimumHeight(45)
        skip_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100, 100, 100, 150);
                color: white;
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(120, 120, 120, 180);
            }
        """)
        skip_btn.clicked.connect(self.skip_current_step)
        self.skip_btn = skip_btn
        button_layout.addWidget(skip_btn)

        # Next/Done button
        next_btn = QPushButton("→ Volgende")
        next_btn.setMinimumHeight(50)
        next_btn.setStyleSheet("""
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
        next_btn.clicked.connect(self.next_step)
        self.next_btn = next_btn
        button_layout.addWidget(next_btn)

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

    def on_canvas_clicked(self, img_x: int, img_y: int):
        """Handle canvas click event with image coordinates"""
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
            # Merge the masks
            if hasattr(new_color, 'mask'):
                new_color.mask = new_color.mask | mask
            else:
                new_color.mask = mask.copy()
        else:
            # Generate intelligent color name
            color_name = get_color_name(r, g, b)

            # Determine is_black and is_white based on current step
            is_black = (self.current_step == 'SELECTING_BLACK')
            is_white = (self.current_step == 'SELECTING_WHITE')

            new_color = Color(r, g, b, len(self.selected_colors) + 1, color_name, is_black=is_black, is_white=is_white)

            # Store the mask in the color for later use
            new_color.mask = mask.copy()

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

        # Auto-advance to next step after selecting a color
        if not merge_with_existing:  # Only auto-advance for new colors
            if self.current_step == 'SELECTING_BLACK':
                # Auto-advance to white selection
                logger.info("Auto-advancing to white selection step")
                self.black_colors = [c for c in self.selected_colors if c.is_black]
                self.current_step = 'SELECTING_WHITE'
                self.update_ui_for_step()
            elif self.current_step == 'SELECTING_WHITE':
                # Auto-advance to color selection
                logger.info("Auto-advancing to color selection step")
                self.white_colors = [c for c in self.selected_colors if c.is_white]
                self.current_step = 'SELECTING_COLORS'
                self.update_ui_for_step()

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
        self.canvas.set_image(self.display_image)

    def cleanup_unselected_pixels(self):
        """Assign all unselected pixels to nearest selected color"""
        # Get mask of unselected pixels
        unselected_mask = ~self.selection_mask

        if not np.any(unselected_mask):
            logger.info("No unselected pixels to cleanup")
            return

        # Get unselected pixel positions
        unselected_coords = np.where(unselected_mask)
        num_unselected = len(unselected_coords[0])

        logger.info(f"Cleaning up {num_unselected} unselected pixels...")

        # For each unselected pixel, find closest color
        for i in range(num_unselected):
            y = unselected_coords[0][i]
            x = unselected_coords[1][i]

            # Get pixel color from original image
            pixel_color = self.original_image[y, x]
            r, g, b = int(pixel_color[0]), int(pixel_color[1]), int(pixel_color[2])

            # Find closest selected color
            min_distance = float('inf')
            closest_color = None

            for color in self.selected_colors:
                distance = calculate_color_distance(r, g, b, color.r, color.g, color.b)
                if distance < min_distance:
                    min_distance = distance
                    closest_color = color

            # Assign pixel to closest color
            if closest_color:
                self.working_image[y, x] = [closest_color.r, closest_color.g, closest_color.b]

        # Update selection mask - everything is now selected
        self.selection_mask[:] = True

        # Apply morphological operations to smooth edges
        logger.info("Applying morphological smoothing...")
        self.smooth_color_regions()

        # Update display
        self.update_display_image()

        logger.info("Cleanup complete")

    def smooth_color_regions(self):
        """Apply morphological operations to smooth color region boundaries"""
        # Convert to individual color masks and smooth each
        for color in self.selected_colors:
            # Create mask for this color
            color_mask = np.all(
                self.working_image == [color.r, color.g, color.b],
                axis=2
            ).astype(np.uint8) * 255

            # Apply morphological closing (removes small holes)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            closed = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

            # Apply opening (removes small noise)
            opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)

            # Update working image where mask is set
            self.working_image[opened > 0] = [color.r, color.g, color.b]

        logger.info("Morphological smoothing complete")

    def detect_black_white_regions(self):
        """Detect and handle black and white regions"""
        # Ask user if they want to detect black/white
        msg = QMessageBox(self)
        msg.setWindowTitle("Zwart/Wit Detecteren")
        msg.setText("Wil je automatisch zwart en wit gebieden detecteren?")
        msg.setInformativeText(
            "Zwart wordt volledig gevuld met spuitbus (geen outline in lijntekening).\n"
            "Wit krijgt geen cijfers (alleen outline).\n\n"
            "Thresholds: Zwart < 30, Wit > 225"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)

        if msg.exec_() != QMessageBox.Yes:
            logger.info("Black/white detection skipped")
            return

        BLACK_THRESHOLD = 30
        WHITE_THRESHOLD = 225

        # Detect black regions in original image
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2GRAY)
        black_mask = gray < BLACK_THRESHOLD
        white_mask = gray > WHITE_THRESHOLD

        black_pixels = np.sum(black_mask)
        white_pixels = np.sum(white_mask)

        logger.info(f"Detected {black_pixels} black pixels, {white_pixels} white pixels")

        # Check if we have significant black/white regions
        total_pixels = self.original_image.shape[0] * self.original_image.shape[1]
        black_percentage = (black_pixels / total_pixels) * 100
        white_percentage = (white_pixels / total_pixels) * 100

        # Add or merge black color
        if black_pixels > 0 and black_percentage > 0.5:  # At least 0.5% coverage
            self.add_or_merge_special_color(0, 0, 0, "Zwart", is_black=True, mask=black_mask)

        # Add or merge white color
        if white_pixels > 0 and white_percentage > 0.5:  # At least 0.5% coverage
            self.add_or_merge_special_color(255, 255, 255, "Wit", is_white=True, mask=white_mask)

        # Update display
        self.update_display_image()
        logger.info("Black/white detection complete")

    def add_or_merge_special_color(self, r: int, g: int, b: int, name: str, is_black: bool = False, is_white: bool = False, mask: np.ndarray = None):
        """Add or merge a special color (black/white) with existing colors"""
        # Check if similar color already exists
        existing_color = None
        for color in self.selected_colors:
            # Check if very similar (within 50 distance for black/white merging)
            from color_naming import calculate_color_distance
            distance = calculate_color_distance(r, g, b, color.r, color.g, color.b)
            if distance < 50:
                existing_color = color
                break

        if existing_color:
            # Merge with existing color - update its special flags
            logger.info(f"Merging {name} with existing color: {existing_color.name}")
            existing_color.is_black = is_black
            existing_color.is_white = is_white
            existing_color.name = name  # Rename to Zwart/Wit

            # Update pixels to exact black/white
            if mask is not None:
                self.working_image[mask] = [r, g, b]
        else:
            # Add as new color
            new_color = Color(r, g, b, len(self.selected_colors) + 1, name, is_black=is_black, is_white=is_white)
            self.selected_colors.append(new_color)
            logger.info(f"Added new special color: {name}")

            # Update pixels
            if mask is not None:
                self.working_image[mask] = [r, g, b]
                self.selection_mask |= mask

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
        # Combine all colors: black + white + regular colors
        all_colors = self.black_colors + self.white_colors + self.selected_colors

        if not all_colors:
            QMessageBox.warning(
                self,
                "Geen kleuren",
                "Selecteer minimaal één kleur voordat je klikt op Klaar"
            )
            return

        # Check if there are unselected pixels
        total_pixels = self.selection_mask.size
        selected_pixels = np.sum(self.selection_mask)
        unselected_pixels = total_pixels - selected_pixels

        if unselected_pixels > 0:
            # Ask user if they want to cleanup
            coverage = (selected_pixels / total_pixels) * 100
            msg = QMessageBox(self)
            msg.setWindowTitle("Opschonen")
            msg.setText(f"Je hebt {coverage:.1f}% van de afbeelding geselecteerd.")
            msg.setInformativeText(
                f"{unselected_pixels} pixels zijn nog niet toegewezen.\n\n"
                "Wil je deze automatisch toewijzen aan de dichtstbijzijnde kleuren?\n"
                "Dit verwijdert ruis en maakt de lijnen strakker."
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)

            if msg.exec_() == QMessageBox.Yes:
                logger.info("Cleaning up unselected pixels...")
                # Update selected_colors temporarily for cleanup
                temp_colors = self.selected_colors
                self.selected_colors = all_colors
                self.cleanup_unselected_pixels()
                self.selected_colors = temp_colors

        # Renumber all colors sequentially
        for i, color in enumerate(all_colors):
            color.number = i + 1

        logger.info(f"Finished manual color selection: {len(all_colors)} colors ({len(self.black_colors)} black, {len(self.white_colors)} white, {len(self.selected_colors)} regular)")
        self.colors_selected.emit(all_colors)
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

    def skip_current_step(self):
        """Skip the current step (black or white selection)"""
        if self.current_step == 'SELECTING_BLACK':
            logger.info("Skipped black selection")
            self.current_step = 'SELECTING_WHITE'
            self.update_ui_for_step()
        elif self.current_step == 'SELECTING_WHITE':
            logger.info("Skipped white selection")
            self.current_step = 'SELECTING_COLORS'
            self.update_ui_for_step()

    def next_step(self):
        """Move to next step"""
        if self.current_step == 'SELECTING_BLACK':
            # Save black colors
            self.black_colors = self.selected_colors.copy()
            logger.info(f"Black selection complete: {len(self.black_colors)} colors")

            # Move to white selection
            self.current_step = 'SELECTING_WHITE'
            self.update_ui_for_step()

        elif self.current_step == 'SELECTING_WHITE':
            # Save white colors
            self.white_colors = self.selected_colors.copy()
            logger.info(f"White selection complete: {len(self.white_colors)} colors")

            # Move to regular color selection
            self.current_step = 'SELECTING_COLORS'
            self.update_ui_for_step()

        elif self.current_step == 'SELECTING_COLORS':
            # Finish selection
            self.finish_selection()

    def update_ui_for_step(self):
        """Update UI elements based on current step"""
        if self.current_step == 'SELECTING_BLACK':
            self.instruction_label.setText("STAP 1: Selecteer alle zwarte gebieden")
            self.instruction_label.setStyleSheet("""
                color: white;
                font-size: 14px;
                font-weight: bold;
                background: rgba(50, 50, 50, 200);
                padding: 10px;
                border-radius: 5px;
            """)
            self.next_btn.setText("→ Volgende")
            self.skip_btn.setVisible(True)

            # Clear previous selections
            self.selected_colors = []
            self.color_history = []
            self.selection_mask = np.zeros(self.original_image.shape[:2], dtype=bool)
            self.working_image = self.original_image.copy()
            self.display_image = self.original_image.copy()
            self.canvas.set_image(self.display_image)
            self.update_color_list()

        elif self.current_step == 'SELECTING_WHITE':
            self.instruction_label.setText("STAP 2: Selecteer alle witte gebieden")
            self.instruction_label.setStyleSheet("""
                color: black;
                font-size: 14px;
                font-weight: bold;
                background: rgba(255, 255, 255, 200);
                padding: 10px;
                border-radius: 5px;
            """)
            self.next_btn.setText("→ Volgende")
            self.skip_btn.setVisible(True)

            # Clear previous selections but keep black colors in working image
            self.selected_colors = []
            self.color_history = []
            self.selection_mask = np.zeros(self.original_image.shape[:2], dtype=bool)

            # Restore black colors to working image
            for color in self.black_colors:
                if hasattr(color, 'mask'):
                    self.working_image[color.mask] = [color.r, color.g, color.b]
                    self.selection_mask |= color.mask

            self.display_image = self.working_image.copy()
            self.canvas.set_image(self.display_image)
            self.update_color_list()

        elif self.current_step == 'SELECTING_COLORS':
            self.instruction_label.setText("STAP 3: Selecteer overige kleuren")
            self.instruction_label.setStyleSheet("""
                color: white;
                font-size: 14px;
                font-weight: bold;
                background: rgba(76, 175, 80, 150);
                padding: 10px;
                border-radius: 5px;
            """)
            self.next_btn.setText("✓ Klaar")
            self.skip_btn.setVisible(False)

            # Clear previous selections
            self.selected_colors = []
            self.color_history = []
            self.selection_mask = np.zeros(self.original_image.shape[:2], dtype=bool)

            # Start with original image
            self.working_image = self.original_image.copy()

            # Hide black and white regions by replacing them with neutral gray
            neutral_color = [200, 200, 200]  # Light gray to indicate already processed areas

            # Hide black regions
            for color in self.black_colors:
                if hasattr(color, 'mask'):
                    self.working_image[color.mask] = neutral_color
                    self.selection_mask |= color.mask

            # Hide white regions
            for color in self.white_colors:
                if hasattr(color, 'mask'):
                    self.working_image[color.mask] = neutral_color
                    self.selection_mask |= color.mask

            self.display_image = self.working_image.copy()
            self.canvas.set_image(self.display_image)
            self.update_color_list()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            self.cancel_selection()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.next_step()  # Use next_step instead of finish_selection
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.undo_last_color()
        elif event.key() == Qt.Key_M:
            # Toggle magnifier
            self.canvas.show_magnifier = not self.canvas.show_magnifier
            status = "aan" if self.canvas.show_magnifier else "uit"
            logger.info(f"Magnifier toggled in manual picker: {self.canvas.show_magnifier}")
            self.canvas.update()
        else:
            super().keyPressEvent(event)
