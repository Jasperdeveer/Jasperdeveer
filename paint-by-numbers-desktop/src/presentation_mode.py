"""
Presentation Mode - Fullscreen viewer for paint-by-numbers
Keyboard-controlled interface for beamer projection
"""

import numpy as np
from typing import Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen
import logging

logger = logging.getLogger(__name__)


class PresentationMode(QWidget):
    """Fullscreen presentation mode for beamer projection"""

    # Signals
    closed = pyqtSignal()
    toggle_numbers_requested = pyqtSignal()
    cycle_mode_requested = pyqtSignal()
    toggle_outlines_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image: Optional[np.ndarray] = None
        self.original_image: Optional[np.ndarray] = None
        self.show_numbers = True
        self.show_grid = False
        self.grid_size = 4  # 4x4 grid (A1, A2, B1, B2, etc.)
        self.grid_color_index = 0  # 0=neon green, 1=magenta
        self.grid_colors = [
            (0, 255, 0),      # Neon green / Gifgroen
            (255, 0, 255),    # Magenta
            (0, 255, 255),    # Cyan
            (255, 255, 0)     # Yellow
        ]
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0

        # Mouse drag state
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_pan_x = 0
        self.drag_start_pan_y = 0

        # Keyboard shortcuts overlay
        self.show_shortcuts = True
        self.shortcuts_opacity = 1.0
        self.fade_timer = QTimer()
        self.fade_timer.timeout.connect(self.fade_shortcuts)

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Presentatie Mode - JSPR Beamer Setup")
        self.setStyleSheet("background-color: black;")

        # Start fade timer (fade out after 3 seconds)
        self.fade_timer.start(3000)

    def set_image(self, image: np.ndarray):
        """Set image to display"""
        self.image = image
        self.update()

    def set_original_image(self, original: np.ndarray):
        """Set original image for reference"""
        self.original_image = original

    def toggle_numbers(self):
        """Toggle number visibility"""
        self.show_numbers = not self.show_numbers
        logger.info(f"Numbers: {'ON' if self.show_numbers else 'OFF'}")

    def toggle_grid(self):
        """Toggle grid overlay"""
        self.show_grid = not self.show_grid
        logger.info(f"Grid: {'ON' if self.show_grid else 'OFF'}")
        self.update()

    def cycle_grid_color(self):
        """Cycle through grid colors"""
        self.grid_color_index = (self.grid_color_index + 1) % len(self.grid_colors)
        color_names = ["Gifgroen", "Magenta", "Cyaan", "Geel"]
        logger.info(f"Grid kleur: {color_names[self.grid_color_index]}")
        self.update()

    def increase_grid_size(self):
        """Increase grid size"""
        self.grid_size = min(12, self.grid_size + 1)
        logger.info(f"Grid: {self.grid_size}x{self.grid_size}")
        self.update()

    def decrease_grid_size(self):
        """Decrease grid size"""
        self.grid_size = max(2, self.grid_size - 1)
        logger.info(f"Grid: {self.grid_size}x{self.grid_size}")
        self.update()

    def toggle_shortcuts(self):
        """Toggle keyboard shortcuts overlay"""
        self.show_shortcuts = not self.show_shortcuts
        if self.show_shortcuts:
            self.shortcuts_opacity = 1.0
            self.fade_timer.start(3000)
        else:
            self.fade_timer.stop()
        self.update()

    def fade_shortcuts(self):
        """Gradually fade out shortcuts overlay"""
        if self.shortcuts_opacity > 0:
            self.shortcuts_opacity -= 0.1
            if self.shortcuts_opacity < 0:
                self.shortcuts_opacity = 0
                self.fade_timer.stop()
            self.update()

    def reset_shortcuts_fade(self):
        """Reset shortcuts fade timer"""
        if self.show_shortcuts:
            self.shortcuts_opacity = 1.0
            self.fade_timer.start(3000)
            self.update()

    def zoom_in(self):
        """Zoom in"""
        self.zoom_level = min(5.0, self.zoom_level + 0.25)
        logger.info(f"Zoom: {int(self.zoom_level * 100)}%")
        self.update()

    def zoom_out(self):
        """Zoom out"""
        self.zoom_level = max(0.25, self.zoom_level - 0.25)
        logger.info(f"Zoom: {int(self.zoom_level * 100)}%")
        self.update()

    def reset_zoom(self):
        """Reset zoom and pan"""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        logger.info("Reset zoom and pan")
        self.update()

    def pan(self, dx: int, dy: int):
        """Pan the view"""
        self.pan_x += dx
        self.pan_y += dy
        self.update()

    def mousePressEvent(self, event):
        """Handle mouse press for drag start"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_start_x = event.x()
            self.drag_start_y = event.y()
            self.drag_start_pan_x = self.pan_x
            self.drag_start_pan_y = self.pan_y
            self.setCursor(Qt.ClosedHandCursor)
            logger.debug("Started dragging")

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if self.is_dragging:
            # Calculate delta from drag start
            dx = event.x() - self.drag_start_x
            dy = event.y() - self.drag_start_y

            # Update pan position
            self.pan_x = self.drag_start_pan_x + dx
            self.pan_y = self.drag_start_pan_y + dy

            self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release for drag end"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.setCursor(Qt.ArrowCursor)
            logger.debug(f"Stopped dragging - pan position: ({self.pan_x}, {self.pan_y})")

    def wheelEvent(self, event):
        """Handle mouse wheel for zoom"""
        # Get the angle delta (usually 120 for one notch)
        delta = event.angleDelta().y()

        # Determine zoom increment based on Shift key
        if event.modifiers() & Qt.ShiftModifier:
            zoom_factor = 0.10  # 10% per scroll
        else:
            zoom_factor = 0.02  # 2% per scroll

        # Apply zoom
        if delta > 0:
            # Scroll up = zoom in
            self.zoom_level *= (1 + zoom_factor)
        else:
            # Scroll down = zoom out
            self.zoom_level *= (1 - zoom_factor)

        # Clamp zoom level
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))

        # Update display
        self.update()
        logger.debug(f"Zoom: {int(self.zoom_level * 100)}%")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        key = event.key()

        # Reset fade on any key press
        self.reset_shortcuts_fade()

        # ESC or Q: Return to main interface
        if key in (Qt.Key_Escape, Qt.Key_Q):
            self.close()

        # F11: Toggle fullscreen
        elif key == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

        # N: Toggle numbers
        elif key == Qt.Key_N:
            self.toggle_numbers_requested.emit()

        # G: Toggle grid
        elif key == Qt.Key_G:
            self.toggle_grid()

        # C: Cycle grid color
        elif key == Qt.Key_C:
            self.cycle_grid_color()

        # O: Toggle outlines
        elif key == Qt.Key_O:
            self.toggle_outlines_requested.emit()

        # H: Toggle shortcuts help
        elif key == Qt.Key_H:
            self.toggle_shortcuts()

        # +/=: Zoom in (or increase grid size with Shift)
        elif key in (Qt.Key_Plus, Qt.Key_Equal):
            if event.modifiers() & Qt.ShiftModifier:
                self.increase_grid_size()
            else:
                self.zoom_in()

        # -: Zoom out (or decrease grid size with Shift)
        elif key == Qt.Key_Minus:
            if event.modifiers() & Qt.ShiftModifier:
                self.decrease_grid_size()
            else:
                self.zoom_out()

        # 0: Reset zoom
        elif key == Qt.Key_0:
            self.reset_zoom()

        # Arrow keys: Pan
        elif key == Qt.Key_Left:
            self.pan(50, 0)
        elif key == Qt.Key_Right:
            self.pan(-50, 0)
        elif key == Qt.Key_Up:
            self.pan(0, 50)
        elif key == Qt.Key_Down:
            self.pan(0, -50)

        # Space: Toggle between modes (original/paintByNumbers/lineDrawing)
        elif key == Qt.Key_Space:
            self.cycle_mode_requested.emit()

        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """Paint the canvas"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        if self.image is not None:
            # Convert numpy array to QImage
            height, width, channel = self.image.shape
            bytes_per_line = 3 * width

            q_image = QImage(
                self.image.data,
                width,
                height,
                bytes_per_line,
                QImage.Format_RGB888
            )

            # Calculate scaled size
            scaled_width = int(width * self.zoom_level)
            scaled_height = int(height * self.zoom_level)

            # Center image in widget with pan offset
            x = (self.width() - scaled_width) // 2 + self.pan_x
            y = (self.height() - scaled_height) // 2 + self.pan_y

            # Draw scaled image
            from PyQt5.QtCore import QRect
            target_rect = QRect(x, y, scaled_width, scaled_height)
            painter.drawImage(target_rect, q_image)

            # Draw grid overlay
            if self.show_grid:
                self.draw_grid(painter, x, y, scaled_width, scaled_height)

        # Draw keyboard shortcuts overlay
        if self.show_shortcuts and self.shortcuts_opacity > 0:
            self.draw_shortcuts(painter)

        # Draw status info
        self.draw_status(painter)

    def draw_grid(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """Draw grid overlay (A1, A2, B1, etc.)"""
        painter.save()

        # Get current grid color
        r, g, b = self.grid_colors[self.grid_color_index]

        # Grid lines
        pen = QPen(QColor(r, g, b, 255))  # Full opacity for visibility
        pen.setWidth(3)  # Thicker for beamer visibility
        painter.setPen(pen)

        cell_width = width / self.grid_size
        cell_height = height / self.grid_size

        # Draw vertical lines
        for i in range(1, self.grid_size):
            line_x = int(x + i * cell_width)
            painter.drawLine(line_x, y, line_x, y + height)

        # Draw horizontal lines
        for i in range(1, self.grid_size):
            line_y = int(y + i * cell_height)
            painter.drawLine(x, line_y, x + width, line_y)

        # Draw labels (A1, A2, B1, etc.)
        font = QFont("Arial", 20, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(r, g, b, 255))  # Match grid color

        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                label = f"{letters[row]}{col + 1}"
                label_x = int(x + col * cell_width + 10)
                label_y = int(y + row * cell_height + 30)
                painter.drawText(label_x, label_y, label)

        painter.restore()

    def draw_shortcuts(self, painter: QPainter):
        """Draw keyboard shortcuts overlay"""
        painter.save()

        # Semi-transparent background - larger for more shortcuts
        bg_color = QColor(0, 0, 0, int(150 * self.shortcuts_opacity))
        painter.fillRect(10, 10, 320, 450, bg_color)

        # White text
        painter.setPen(QColor(255, 255, 255, int(255 * self.shortcuts_opacity)))

        # Title
        font = QFont("Arial", 14, QFont.Bold)
        painter.setFont(font)
        painter.drawText(20, 35, "Toetsenbord Shortcuts")

        # Shortcuts list
        font = QFont("Arial", 11)
        painter.setFont(font)

        shortcuts = [
            ("ESC / Q", "Afsluiten"),
            ("F11", "Volledig scherm"),
            ("N", "Nummers aan/uit"),
            ("O", "Outlines aan/uit"),
            ("G", "Grid aan/uit"),
            ("C", "Grid kleur"),
            ("Shift +/-", "Grid grootte"),
            ("H", "Deze hulp aan/uit"),
            ("+/-", "Zoom in/uit"),
            ("0", "Reset zoom"),
            ("←↑↓→", "Pan beeld"),
            ("Space", "Wissel modus"),
        ]

        y = 60
        for key, description in shortcuts:
            painter.drawText(20, y, f"{key:<15} {description}")
            y += 30

        painter.restore()

    def draw_status(self, painter: QPainter):
        """Draw status information"""
        painter.save()

        # Bottom right corner
        painter.setPen(QColor(255, 255, 255, 180))
        font = QFont("Arial", 10)
        painter.setFont(font)

        status_text = f"Zoom: {int(self.zoom_level * 100)}%"
        if self.show_numbers:
            status_text += " | Nummers: ON"
        if self.show_grid:
            color_names = ["Gifgroen", "Magenta", "Cyaan", "Geel"]
            status_text += f" | Grid: {self.grid_size}x{self.grid_size} ({color_names[self.grid_color_index]})"

        painter.drawText(
            self.width() - 400,
            self.height() - 20,
            status_text
        )

        painter.restore()

    def closeEvent(self, event):
        """Handle window close"""
        self.fade_timer.stop()
        self.closed.emit()
        super().closeEvent(event)
