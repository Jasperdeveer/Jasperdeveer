"""
Main Window - PyQt5 GUI for JSPR Beamer Setup
Native desktop interface for paint-by-numbers generation
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import List, Optional
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox, QFileDialog, QScrollArea,
    QGroupBox, QSplitter, QMessageBox, QProgressDialog, QCheckBox, QDialog,
    QLineEdit, QSizePolicy, QComboBox, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QEvent, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QFont, QCursor, QKeyEvent
import cv2
import numpy as np
import logging

from image_processor import ImageProcessor
from color_manager import ColorManager, Color
from visualizer import Visualizer
from presentation_mode import PresentationMode
from manual_color_picker import ColorSelectionDialog, ManualColorPicker
from project_manager import ProjectManager
from selection_tools import SelectionTools, SelectionMode
from welcome_screen import WelcomeScreen
from status_indicator import StatusIndicator
from collapsible_section import CollapsibleSection
# Lazy import for memory_manager to speed up startup
# from memory_manager import GlobalMemoryManager

logger = logging.getLogger(__name__)


class HoverWidget(QWidget):
    """Widget that detects mouse hover for color preview"""

    def __init__(self, color_index: int, main_window, parent=None):
        super().__init__(parent)
        self.color_index = color_index
        self.main_window = main_window
        self.setMouseTracking(True)

    def enterEvent(self, event):
        """Mouse entered the widget"""
        self.main_window.on_color_hover_enter(self.color_index)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse left the widget"""
        self.main_window.on_color_hover_leave()
        super().leaveEvent(event)


class BlackWhiteSelectionDialog(QDialog):
    """Dialog for selecting which colors should be treated as black or white"""

    def __init__(self, color_manager: ColorManager, parent=None):
        super().__init__(parent)
        self.color_manager = color_manager
        self.black_checkboxes = []
        self.white_checkboxes = []
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Zwart/Wit Kleuren Selecteren")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel(
            "Selecteer welke kleuren als zwart of wit behandeld moeten worden:\n"
            "• Zwart: volledig gevuld, geen cijfers\n"
            "• Wit: geen cijfers"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Scroll area for colors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Add checkbox row for each color
        colors = self.color_manager.get_colors()
        for color in colors:
            color_row = QHBoxLayout()

            # Color preview box
            color_preview = QLabel()
            color_preview.setFixedSize(30, 30)
            color_preview.setStyleSheet(
                f"background-color: rgb({color.r}, {color.g}, {color.b}); border: 1px solid black;"
            )
            color_row.addWidget(color_preview)

            # Color name and number
            color_label = QLabel(f"{color.number}. {color.name}")
            color_label.setMinimumWidth(150)
            color_row.addWidget(color_label)

            # Black checkbox
            black_cb = QCheckBox("Zwart")
            black_cb.setChecked(hasattr(color, 'is_black') and color.is_black)
            self.black_checkboxes.append((color, black_cb))
            color_row.addWidget(black_cb)

            # White checkbox
            white_cb = QCheckBox("Wit")
            white_cb.setChecked(hasattr(color, 'is_white') and color.is_white)
            self.white_checkboxes.append((color, white_cb))
            color_row.addWidget(white_cb)

            color_row.addStretch()
            scroll_layout.addLayout(color_row)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_btn = QPushButton("Annuleren")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Klaar")
        ok_btn.setObjectName("primaryButton")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_selections(self):
        """Get the selected black and white colors"""
        black_colors = [color for color, cb in self.black_checkboxes if cb.isChecked()]
        white_colors = [color for color, cb in self.white_checkboxes if cb.isChecked()]
        return black_colors, white_colors


class ProcessingThread(QThread):
    """Background thread for heavy processing tasks"""

    progress = pyqtSignal(int, str)  # percent, message
    finished = pyqtSignal(object)  # result
    error = pyqtSignal(str)  # error message

    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.task_func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            self.error.emit(str(e))


class CanvasWidget(QWidget):
    """Custom widget for displaying rendered image"""

    # Signal emitted when color is picked (r, g, b)
    color_picked = pyqtSignal(int, int, int)
    # Signal emitted when zoom level changes (float)
    zoom_changed = pyqtSignal(float)
    # Signal emitted when zoom crosses quality threshold (requires re-render)
    quality_change_needed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image: Optional[np.ndarray] = None
        self.original_image: Optional[np.ndarray] = None  # For eyedropper
        self.zoom_level = 1.0
        self.eyedropper_mode = False
        self.selection_tools: Optional[SelectionTools] = None
        self.selection_active = False
        self.is_brushing = False

        # Magnifier settings
        self.show_magnifier = True
        self.magnifier_size = 100  # Diameter in pixels
        self.magnifier_grid_size = 5  # 5x5 pixel grid
        self.current_mouse_pos = None

        # Grid overlay settings
        self.show_grid = False
        self.grid_size = 50  # pixels
        self.grid_color = QColor(255, 255, 255, 80)  # Semi-transparent white

        # Rendering cache for faster zoom/pan
        self.render_cache = {}  # {zoom_level: QImage}
        self.cache_max_size = 10  # Max cached zoom levels
        self.current_image_hash = None  # Track when image changes

        # Dynamic quality: track zoom level at last render
        self.last_render_zoom = 1.0
        # Quality thresholds: re-render when crossing these
        self.quality_thresholds = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]

        self.setMinimumSize(800, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)  # Track mouse for cursor changes

    def set_image(self, image: np.ndarray):
        """Set image to display (RGB numpy array)"""
        self.image = image
        # Clear cache when image changes
        self.clear_render_cache()
        # Reset quality tracking
        self.last_render_zoom = 1.0
        # Update image hash for cache management
        if image is not None:
            import hashlib
            self.current_image_hash = hashlib.md5(image.tobytes()).hexdigest()
        # Auto-fit to canvas when setting new image
        if image is not None:
            self.fit_to_canvas()
        self.update()  # Trigger repaint

    def fit_to_canvas(self):
        """Calculate zoom level to fit image in canvas"""
        if self.image is not None:
            height, width = self.image.shape[:2]
            widget_width = self.width()
            widget_height = self.height()

            # Calculate scale to fit
            scale = min(widget_width / width, widget_height / height)
            self.zoom_level = max(0.1, min(5.0, scale))
            self.zoom_changed.emit(self.zoom_level)

    def resizeEvent(self, event):
        """Handle widget resize - refit image"""
        super().resizeEvent(event)
        # Re-fit image when canvas is resized (only if significant size change)
        if self.image is not None:
            # Only refit if size changed by more than 10 pixels
            old_size = event.oldSize()
            new_size = event.size()
            if abs(old_size.width() - new_size.width()) > 10 or abs(old_size.height() - new_size.height()) > 10:
                self.fit_to_canvas()
            else:
                self.update()

    def paintEvent(self, event):
        """Paint the canvas"""
        painter = QPainter(self)

        if self.image is not None:
            # Get image with selection overlay if active
            display_image = self.image
            has_overlay = self.selection_active and self.selection_tools and self.selection_tools.is_selection_active()
            if has_overlay:
                display_image = self.selection_tools.get_visualization_overlay(self.image)

            # Try to use cached QImage if no overlay active
            q_image = None
            if not has_overlay:
                q_image = self.get_cached_qimage(self.zoom_level)

            # Create QImage if not cached
            if q_image is None:
                height, width, channel = display_image.shape
                bytes_per_line = 3 * width

                q_image = QImage(
                    display_image.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format_RGB888
                )

                # Cache if no overlay (overlays change dynamically)
                if not has_overlay:
                    self.cache_qimage(self.zoom_level, q_image)

            # Calculate scaled size
            height, width = display_image.shape[:2]
            scaled_width = int(width * self.zoom_level)
            scaled_height = int(height * self.zoom_level)

            # Center image in widget
            x = (self.width() - scaled_width) // 2
            y = (self.height() - scaled_height) // 2

            # Draw scaled image using target rectangle
            from PyQt5.QtCore import QRect
            target_rect = QRect(x, y, scaled_width, scaled_height)
            painter.drawImage(target_rect, q_image)

            # Draw polygon points if in polygon mode
            if (self.selection_active and self.selection_tools and
                self.selection_tools.mode == SelectionMode.POLYGON and
                len(self.selection_tools.polygon_points) > 0):
                painter.setPen(QPen(QColor(0, 255, 255), 2))  # Cyan

                # Draw lines between points
                points = self.selection_tools.polygon_points
                for i in range(len(points)):
                    p1 = points[i]
                    p2 = points[(i + 1) % len(points)] if i < len(points) - 1 else points[0]

                    # Convert image coords to widget coords
                    x1 = x + int(p1[0] * self.zoom_level)
                    y1 = y + int(p1[1] * self.zoom_level)
                    x2 = x + int(p2[0] * self.zoom_level)
                    y2 = y + int(p2[1] * self.zoom_level)

                    if i < len(points) - 1:
                        painter.drawLine(x1, y1, x2, y2)

                    # Draw point circles
                    painter.setBrush(QColor(0, 255, 255))
                    painter.drawEllipse(x1 - 4, y1 - 4, 8, 8)

            # Draw grid overlay if enabled
            if self.show_grid:
                self.draw_grid_overlay(painter, x, y, scaled_width, scaled_height)

            # Draw magnifier last (on top of everything)
            if self.show_magnifier and self.current_mouse_pos and self.original_image is not None:
                self.draw_magnifier(painter, x, y, scaled_width, scaled_height)
        else:
            # Draw placeholder
            painter.fillRect(self.rect(), QColor(50, 50, 50))
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Sleep een afbeelding hierheen of gebruik Bestand > Open"
            )

    def draw_magnifier(self, painter: QPainter, img_x_offset: int, img_y_offset: int,
                       img_scaled_width: int, img_scaled_height: int):
        """Draw circular magnifier showing 5x5 pixel grid at cursor position"""
        from PyQt5.QtCore import QRectF, QPointF
        from PyQt5.QtGui import QPainterPath

        # Get cursor position in image coordinates
        cursor_x = self.current_mouse_pos.x()
        cursor_y = self.current_mouse_pos.y()

        img_x, img_y = self.widget_to_image_coords(cursor_x, cursor_y)
        if img_x is None:
            return  # Cursor outside image bounds

        # Sample 5x5 grid around cursor position
        grid_half = self.magnifier_grid_size // 2  # 2 pixels on each side

        # Calculate sample region bounds
        sample_x_start = max(0, img_x - grid_half)
        sample_y_start = max(0, img_y - grid_half)
        sample_x_end = min(self.original_image.shape[1], img_x + grid_half + 1)
        sample_y_end = min(self.original_image.shape[0], img_y + grid_half + 1)

        # Extract the sample region
        sample_region = self.original_image[sample_y_start:sample_y_end, sample_x_start:sample_x_end]

        if sample_region.size == 0:
            return

        # Make sure the array is contiguous for QImage
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

        # Position magnifier (offset from cursor to avoid covering it)
        mag_offset_x = 20
        mag_offset_y = -120  # Above cursor
        mag_x = cursor_x + mag_offset_x
        mag_y = cursor_y + mag_offset_y

        # Keep magnifier within widget bounds
        if mag_x + self.magnifier_size > self.width():
            mag_x = cursor_x - self.magnifier_size - mag_offset_x
        if mag_y < 0:
            mag_y = cursor_y + mag_offset_x  # Below cursor if not enough space above

        # Save painter state
        painter.save()

        # Create circular clipping path
        circle_path = QPainterPath()
        circle_center = QPointF(mag_x + self.magnifier_size / 2, mag_y + self.magnifier_size / 2)
        circle_path.addEllipse(circle_center, self.magnifier_size / 2, self.magnifier_size / 2)

        # Apply clip
        painter.setClipPath(circle_path)

        # Draw magnified sample
        mag_rect = QRectF(mag_x, mag_y, self.magnifier_size, self.magnifier_size)
        painter.drawImage(mag_rect, sample_qimage)

        # Draw crosshair and center pixel indicator (BEFORE removing clip)
        # Calculate center of magnifier (which represents the selected pixel)
        center_x = mag_x + self.magnifier_size / 2
        center_y = mag_y + self.magnifier_size / 2

        # Calculate size of one pixel in the magnified view
        pixel_size = self.magnifier_size / sample_width

        # Draw center pixel box (highlight the exact pixel being sampled)
        pixel_box_half = pixel_size / 2
        painter.setPen(QPen(QColor(255, 255, 0), 2))  # Yellow outline
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(
            int(center_x - pixel_box_half),
            int(center_y - pixel_box_half),
            int(pixel_size),
            int(pixel_size)
        )

        # Draw crosshair lines
        crosshair_length = self.magnifier_size / 3  # Length of crosshair arms

        # Black shadow for contrast
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        # Horizontal line
        painter.drawLine(
            int(center_x - crosshair_length / 2), int(center_y),
            int(center_x + crosshair_length / 2), int(center_y)
        )
        # Vertical line
        painter.drawLine(
            int(center_x), int(center_y - crosshair_length / 2),
            int(center_x), int(center_y + crosshair_length / 2)
        )

        # Bright crosshair on top
        painter.setPen(QPen(QColor(0, 255, 0), 1))  # Neon green
        # Horizontal line
        painter.drawLine(
            int(center_x - crosshair_length / 2), int(center_y),
            int(center_x + crosshair_length / 2), int(center_y)
        )
        # Vertical line
        painter.drawLine(
            int(center_x), int(center_y - crosshair_length / 2),
            int(center_x), int(center_y + crosshair_length / 2)
        )

        # Remove clip for border
        painter.setClipping(False)

        # Draw black border (1px)
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(circle_center, self.magnifier_size / 2, self.magnifier_size / 2)

        # Draw RGB value label below magnifier
        if 0 <= img_y < self.original_image.shape[0] and 0 <= img_x < self.original_image.shape[1]:
            r, g, b = self.original_image[img_y, img_x]
            rgb_text = f"RGB: ({r}, {g}, {b})"

            # Draw background for text
            font = painter.font()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)

            text_rect = painter.boundingRect(0, 0, 200, 30, Qt.AlignLeft, rgb_text)
            text_x = int(circle_center.x() - text_rect.width() / 2)
            text_y = int(mag_y + self.magnifier_size + 5)

            # Draw semi-transparent background
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(
                text_x - 4, text_y - 2,
                text_rect.width() + 8, text_rect.height() + 4,
                3, 3
            )

            # Draw text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_x, text_y + text_rect.height() - 2, rgb_text)

        # Restore painter state
        painter.restore()

    def draw_grid_overlay(self, painter: QPainter, img_x_offset: int, img_y_offset: int,
                         img_scaled_width: int, img_scaled_height: int):
        """Draw grid overlay over the image"""
        painter.save()

        # Set grid pen
        painter.setPen(QPen(self.grid_color, 1, Qt.SolidLine))

        # Draw vertical lines
        scaled_grid_size = int(self.grid_size * self.zoom_level)
        for x in range(0, img_scaled_width, scaled_grid_size):
            painter.drawLine(
                img_x_offset + x, img_y_offset,
                img_x_offset + x, img_y_offset + img_scaled_height
            )

        # Draw horizontal lines
        for y in range(0, img_scaled_height, scaled_grid_size):
            painter.drawLine(
                img_x_offset, img_y_offset + y,
                img_x_offset + img_scaled_width, img_y_offset + y
            )

        painter.restore()

    def clear_render_cache(self):
        """Clear all cached rendered images"""
        self.render_cache.clear()
        logger.debug("Render cache cleared")

    def get_cached_qimage(self, zoom_level: float) -> Optional[QImage]:
        """Get cached QImage for this zoom level"""
        # Round zoom to 2 decimals for cache key
        cache_key = round(zoom_level, 2)
        return self.render_cache.get(cache_key)

    def cache_qimage(self, zoom_level: float, q_image: QImage):
        """Cache a QImage for this zoom level"""
        # Round zoom to 2 decimals for cache key
        cache_key = round(zoom_level, 2)

        # Limit cache size
        if len(self.render_cache) >= self.cache_max_size:
            # Remove oldest entry (first key)
            oldest_key = next(iter(self.render_cache))
            del self.render_cache[oldest_key]
            logger.debug(f"Cache full, removed zoom level {oldest_key}")

        # Cache a copy to avoid data changes
        self.render_cache[cache_key] = q_image.copy()
        logger.debug(f"Cached QImage at zoom {cache_key} (cache size: {len(self.render_cache)})")

    def get_quality_level(self, zoom: float) -> float:
        """Get the nearest quality threshold for a zoom level"""
        # Find the nearest threshold
        nearest = self.quality_thresholds[0]
        for threshold in self.quality_thresholds:
            if abs(zoom - threshold) < abs(zoom - nearest):
                nearest = threshold
        return nearest

    def check_quality_change(self, new_zoom: float):
        """Check if zoom crossed a quality threshold"""
        old_quality = self.get_quality_level(self.last_render_zoom)
        new_quality = self.get_quality_level(new_zoom)

        if old_quality != new_quality:
            logger.info(f"Quality threshold crossed: {old_quality} -> {new_quality}")
            self.last_render_zoom = new_zoom
            self.render_cache.clear()  # Clear cache since we're re-rendering
            self.quality_change_needed.emit(new_zoom)

    def set_zoom(self, zoom: float):
        """Set zoom level"""
        old_zoom = self.zoom_level
        self.zoom_level = max(0.1, min(5.0, zoom))
        self.zoom_changed.emit(self.zoom_level)

        # Check if we need to re-render at different quality
        self.check_quality_change(self.zoom_level)

        self.update()

    def set_eyedropper_mode(self, enabled: bool):
        """Enable/disable eyedropper mode"""
        self.eyedropper_mode = enabled
        if enabled:
            self.setCursor(QCursor(Qt.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))

    def set_original_image(self, image: np.ndarray):
        """Set original image for eyedropper sampling"""
        self.original_image = image

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

        # Check if we need to re-render at different quality
        self.check_quality_change(self.zoom_level)

        # Emit zoom changed signal
        self.zoom_changed.emit(self.zoom_level)

        # Update display
        self.update()

        # Update parent's zoom label if it exists
        parent = self.parent()
        if parent and hasattr(parent, 'zoom_label'):
            parent.zoom_label.setText(f"{int(self.zoom_level * 100)}%")

    def widget_to_image_coords(self, widget_x, widget_y):
        """Convert widget coordinates to image coordinates"""
        if self.image is None:
            return None, None

        height, width = self.image.shape[:2]
        scaled_width = int(width * self.zoom_level)
        scaled_height = int(height * self.zoom_level)

        # Calculate image position in widget
        x_offset = (self.width() - scaled_width) // 2
        y_offset = (self.height() - scaled_height) // 2

        # Convert to image coordinates
        img_x = int((widget_x - x_offset) / self.zoom_level)
        img_y = int((widget_y - y_offset) / self.zoom_level)

        # Check bounds
        if 0 <= img_x < width and 0 <= img_y < height:
            return img_x, img_y
        return None, None

    def mousePressEvent(self, event):
        """Handle mouse clicks for eyedropper and selection tools"""
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        # Get image coordinates
        img_x, img_y = self.widget_to_image_coords(event.x(), event.y())
        if img_x is None:
            super().mousePressEvent(event)
            return

        # Handle eyedropper mode
        if self.eyedropper_mode and self.original_image is not None:
            color = self.original_image[img_y, img_x]
            r, g, b = int(color[0]), int(color[1]), int(color[2])
            self.color_picked.emit(r, g, b)
            return

        # Handle selection tools
        if self.selection_active and self.selection_tools:
            if self.selection_tools.mode == SelectionMode.MAGIC_WAND:
                # Check if shift is pressed for additive selection
                add_to_selection = event.modifiers() & Qt.ShiftModifier
                self.selection_tools.magic_wand_select(self.original_image, img_x, img_y, add_to_selection)
                self.update()
                # Update stats in parent window
                parent = self.parent()
                if parent and hasattr(parent, 'update_selection_stats'):
                    parent.update_selection_stats()

            elif self.selection_tools.mode == SelectionMode.BRUSH:
                self.is_brushing = True
                # Check if Ctrl is pressed for erasing
                add = not (event.modifiers() & Qt.ControlModifier)
                self.selection_tools.brush_select(img_x, img_y, add)
                self.update()

            elif self.selection_tools.mode == SelectionMode.POLYGON:
                self.selection_tools.add_polygon_point(img_x, img_y)
                self.update()

            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for brush tool and magnifier"""
        # Update mouse position for magnifier
        self.current_mouse_pos = event.pos()

        if self.is_brushing and self.selection_tools:
            img_x, img_y = self.widget_to_image_coords(event.x(), event.y())
            if img_x is not None:
                add = not (event.modifiers() & Qt.ControlModifier)
                self.selection_tools.brush_select(img_x, img_y, add)

        # Always update to redraw magnifier
        self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            self.is_brushing = False
            # Update stats after brushing
            if self.selection_tools:
                parent = self.parent()
                if parent and hasattr(parent, 'update_selection_stats'):
                    parent.update_selection_stats()
        super().mouseReleaseEvent(event)


class JSPRBeamerSetup(QMainWindow):
    """Main application window"""

    # Config file path
    CONFIG_PATH = Path.home() / '.jspr_config.json'
    MAX_RECENT_FILES = 10

    def __init__(self):
        super().__init__()

        # Initialize components
        self.image_processor = ImageProcessor()
        self.color_manager = ColorManager(use_smart_naming=True)  # Smart naming enabled
        self.visualizer = Visualizer()
        self.memory_manager = None  # Lazy load when needed

        # Connect components
        self.visualizer.set_image_processor(self.image_processor)
        self.visualizer.set_color_manager(self.color_manager)

        # State
        self.current_mode = 'original'
        self.current_file_path = None
        self.presentation_window = None
        self.manual_picker = None

        # UI components
        self.welcome_screen = None
        self.status_indicator = None
        self.main_ui_widget = None

        # Auto-save state
        self.has_unsaved_changes = False
        self.auto_save_enabled = True
        self.auto_save_interval = 120000  # 120 seconds (2 minutes) in milliseconds
        self.auto_save_timer = None

        # Recent files
        self.recent_files: List[str] = []
        self.recent_files_menu = None
        self.load_config()

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Setup UI
        self.init_ui()

        # Setup auto-save
        self.setup_auto_save()

        # Check for auto-save file after window is fully shown (delayed more for faster startup)
        # QTimer.singleShot(2000, self.load_auto_save_if_exists)  # Disabled for faster startup

        logger.info("JSPR Beamer Setup initialized")

    def get_memory_manager(self):
        """Lazy load memory manager"""
        if self.memory_manager is None:
            from memory_manager import GlobalMemoryManager
            self.memory_manager = GlobalMemoryManager.get_instance(max_versions=20, max_cache_mb=500)
        return self.memory_manager

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle('JSPR Beamer Setup v1.0')
        self.setGeometry(100, 100, 1600, 900)

        # Apply modern stylesheet for better readability
        self.setStyleSheet("""
            QWidget {
                font-size: 11pt;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }
            QLabel {
                font-size: 11pt;
                color: rgba(255, 255, 255, 0.9);
            }
            QPushButton {
                font-size: 11pt;
                padding: 8px 12px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QPushButton:checked {
                background-color: rgba(102, 126, 234, 0.5);
                border: 1px solid rgba(102, 126, 234, 0.7);
            }
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QSpinBox, QDoubleSpinBox, QLineEdit {
                font-size: 11pt;
                padding: 6px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                background-color: rgba(0, 0, 0, 0.3);
                min-height: 24px;
            }
            QCheckBox {
                font-size: 11pt;
                spacing: 8px;
            }
            QComboBox {
                font-size: 11pt;
                padding: 6px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                background-color: rgba(0, 0, 0, 0.3);
                min-height: 28px;
            }
        """)

        # Create central widget with stacked layout
        from PyQt5.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Create welcome screen
        self.welcome_screen = WelcomeScreen(recent_files=self.get_recent_files_with_time())
        self.welcome_screen.open_file_requested.connect(self.open_image)
        self.welcome_screen.open_project_requested.connect(self.load_project)
        self.welcome_screen.load_recent_requested.connect(self.open_recent_file)
        self.welcome_screen.remove_recent_requested.connect(self.remove_recent_file)
        self.stacked_widget.addWidget(self.welcome_screen)

        # Create main UI widget
        self.main_ui_widget = QWidget()
        main_layout = QHBoxLayout(self.main_ui_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for resizable panels
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)  # Prevent panels from collapsing
        self.splitter.setHandleWidth(2)  # Slim splitter handle

        # Left panel: Controls
        left_panel = self.create_control_panel()
        left_panel.setMinimumWidth(320)  # Wider for larger text
        left_panel.setMaximumWidth(480)
        self.splitter.addWidget(left_panel)

        # Center panel: Canvas
        center_panel = self.create_canvas_panel()
        center_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.splitter.addWidget(center_panel)
        self.splitter.setStretchFactor(1, 1)  # Canvas should stretch

        # Right panel: Legend
        right_panel = self.create_legend_panel()
        right_panel.setMinimumWidth(250)
        right_panel.setMaximumWidth(400)
        self.splitter.addWidget(right_panel)

        # Set splitter sizes (proportions)
        # Use proportional sizing: left 20%, center 60%, right 20%
        total_width = self.width()
        self.splitter.setSizes([int(total_width * 0.20), int(total_width * 0.60), int(total_width * 0.20)])

        main_layout.addWidget(self.splitter)
        self.stacked_widget.addWidget(self.main_ui_widget)

        # Show welcome screen by default
        self.stacked_widget.setCurrentWidget(self.welcome_screen)

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.statusBar().showMessage('Klaar')

        # Set initial button states (all disabled except open)
        self.update_button_states()

    def switch_to_main_ui(self):
        """Switch from welcome screen to main UI"""
        if self.stacked_widget.currentWidget() == self.welcome_screen:
            self.stacked_widget.setCurrentWidget(self.main_ui_widget)
            logger.info("Switched to main UI")

    def update_button_states(self):
        """Update enabled/disabled state of buttons based on workflow state"""
        has_image = self.image_processor.original_image is not None
        has_colors = len(self.color_manager.get_colors()) > 0
        has_rendered = self.canvas.image is not None

        # File operations - always enabled
        self.open_btn.setEnabled(True)

        # Color detection - requires image
        self.detect_colors_btn.setEnabled(has_image)
        self.detect_colors_btn.setToolTip(
            "Detecteer kleuren in de afbeelding" if has_image
            else "Open eerst een afbeelding"
        )

        # Mode buttons - require colors
        self.mode_original_btn.setEnabled(has_colors)
        self.mode_pbn_btn.setEnabled(has_colors)
        self.mode_line_btn.setEnabled(has_colors)

        # Visualization controls - require colors
        if hasattr(self, 'realtime_checkbox'):
            self.realtime_checkbox.setEnabled(has_colors)
        if hasattr(self, 'show_outlines_checkbox'):
            self.show_outlines_checkbox.setEnabled(has_colors)
        if hasattr(self, 'hide_black_checkbox'):
            self.hide_black_checkbox.setEnabled(has_colors)
        if hasattr(self, 'recalc_btn'):
            self.recalc_btn.setEnabled(has_colors)

        # Drawing parameters - require colors
        if hasattr(self, 'line_width_spin'):
            self.line_width_spin.setEnabled(has_colors)
        if hasattr(self, 'number_size_spin'):
            self.number_size_spin.setEnabled(has_colors)
        if hasattr(self, 'region_size_spin'):
            self.region_size_spin.setEnabled(has_colors)

        # Tools - require image
        if hasattr(self, 'presentation_btn'):
            self.presentation_btn.setEnabled(has_rendered)
            self.presentation_btn.setToolTip(
                "Open in fullscreen presentatiemodus" if has_rendered
                else "Render eerst de afbeelding"
            )
        if hasattr(self, 'magnifier_toggle_btn'):
            self.magnifier_toggle_btn.setEnabled(has_image)

        # Selection tools - require image and colors
        if hasattr(self, 'magic_wand_btn'):
            self.magic_wand_btn.setEnabled(has_colors)
        if hasattr(self, 'brush_btn'):
            self.brush_btn.setEnabled(has_colors)
        if hasattr(self, 'polygon_btn'):
            self.polygon_btn.setEnabled(has_colors)

        # Color management - require colors
        if hasattr(self, 'black_white_btn'):
            self.black_white_btn.setEnabled(has_colors)
            self.black_white_btn.setToolTip(
                "Selecteer welke kleuren als zwart of wit behandeld moeten worden" if has_colors
                else "Detecteer eerst kleuren"
            )

    def open_recent_file(self, file_path: str):
        """Open a recent file from the welcome screen"""
        if Path(file_path).exists():
            self.load_image(file_path)
        else:
            QMessageBox.warning(
                self,
                "Bestand niet gevonden",
                f"Het bestand kan niet worden gevonden:\n{file_path}"
            )
            # Remove from recent files
            if file_path in self.recent_files:
                self.recent_files.remove(file_path)
                self.save_config()

    def remove_recent_file(self, file_path: str):
        """Remove a file from recent files list"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
            self.save_config()

            # Refresh welcome screen
            self.welcome_screen.recent_files = self.get_recent_files_with_time()
            # Force UI refresh by recreating the welcome screen
            self.stacked_widget.removeWidget(self.welcome_screen)
            self.welcome_screen.deleteLater()

            self.welcome_screen = WelcomeScreen(recent_files=self.get_recent_files_with_time())
            self.welcome_screen.open_file_requested.connect(self.open_image)
            self.welcome_screen.open_project_requested.connect(self.load_project)
            self.welcome_screen.load_recent_requested.connect(self.open_recent_file)
            self.welcome_screen.remove_recent_requested.connect(self.remove_recent_file)
            self.stacked_widget.insertWidget(0, self.welcome_screen)
            self.stacked_widget.setCurrentWidget(self.welcome_screen)

            logger.info(f"Removed from recent files: {file_path}")

    def setup_auto_save(self):
        """Setup automatic saving"""
        # Create timer
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.perform_auto_save)
        self.auto_save_timer.start(self.auto_save_interval)
        logger.info(f"Auto-save enabled with {self.auto_save_interval/1000:.0f}s interval")

    def perform_auto_save(self):
        """Perform automatic save if there are unsaved changes"""
        if not self.auto_save_enabled or not self.has_unsaved_changes:
            return

        if self.image_processor.original_image is None:
            return

        # Create auto-save directory
        auto_save_dir = Path.home() / '.jspr_autosave'
        auto_save_dir.mkdir(exist_ok=True)

        # Generate auto-save file path
        auto_save_path = auto_save_dir / 'autosave.jspr'

        try:
            # Save project data
            project_data = {
                'original_image': self.image_processor.original_image,
                'colors': self.color_manager.get_colors(),
                'parameters': {
                    'color_count': self.color_count_spin.value(),
                    'line_width': self.line_width_spin.value(),
                    'number_size': self.number_size_spin.value(),
                    'region_size': self.region_size_spin.value(),
                },
                'timestamp': time.time()
            }

            success = ProjectManager.save_project(str(auto_save_path), project_data)

            if success:
                logger.info(f"Auto-saved to {auto_save_path}")
                # Update status bar briefly
                current_status = self.statusBar().currentMessage()
                self.statusBar().showMessage("💾 Auto-opgeslagen", 2000)
                QTimer.singleShot(2000, lambda: self.statusBar().showMessage(current_status))
            else:
                logger.warning("Auto-save failed")

        except Exception as e:
            logger.error(f"Auto-save error: {e}", exc_info=True)

    def mark_unsaved_changes(self):
        """Mark that there are unsaved changes"""
        self.has_unsaved_changes = True
        if self.current_file_path:
            self.setWindowTitle(f'JSPR Beamer Setup v1.0 - {Path(self.current_file_path).name}*')
        else:
            self.setWindowTitle('JSPR Beamer Setup v1.0*')

    def mark_saved(self):
        """Mark that all changes are saved"""
        self.has_unsaved_changes = False
        if self.current_file_path:
            self.setWindowTitle(f'JSPR Beamer Setup v1.0 - {Path(self.current_file_path).name}')
        else:
            self.setWindowTitle('JSPR Beamer Setup v1.0')

    def load_auto_save_if_exists(self):
        """Check for and load auto-save file if it exists"""
        auto_save_path = Path.home() / '.jspr_autosave' / 'autosave.jspr'

        if not auto_save_path.exists():
            return

        try:
            # Check file age
            import time
            file_age = time.time() - auto_save_path.stat().st_mtime

            # If auto-save is less than 1 hour old, offer to restore
            if file_age < 3600:
                result = QMessageBox.question(
                    self,
                    "Auto-opgeslagen bestand gevonden",
                    f"Er is een auto-opgeslagen bestand gevonden van {int(file_age/60)} minuten geleden.\n\n"
                    "Wil je dit herstellen?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if result == QMessageBox.Yes:
                    project_data = ProjectManager.load_project(str(auto_save_path))
                    if project_data:
                        self.apply_loaded_project(project_data)
                        self.statusBar().showMessage("Auto-opgeslagen bestand hersteld")
                        logger.info("Restored from auto-save")
                else:
                    # Delete auto-save if user declines
                    auto_save_path.unlink()
                    logger.info("Auto-save declined and removed")
            else:
                # Delete old auto-save
                auto_save_path.unlink()
                logger.info("Old auto-save file removed")

        except Exception as e:
            logger.error(f"Error loading auto-save: {e}", exc_info=True)

    def create_menu_bar(self):
        """Create application menu bar"""
        import time
        start = time.time()

        menubar = self.menuBar()
        logger.info(f"Menu: menuBar() took {time.time() - start:.2f}s")

        # File menu
        file_menu = menubar.addMenu('Bestand')

        open_action = file_menu.addAction('Open Afbeelding...')
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_image)

        file_menu.addSeparator()

        save_project_action = file_menu.addAction('Opslaan Project...')
        save_project_action.setShortcut('Ctrl+S')
        save_project_action.triggered.connect(self.save_project)

        load_project_action = file_menu.addAction('Open Project...')
        load_project_action.setShortcut('Ctrl+Shift+O')
        load_project_action.triggered.connect(self.load_project)

        file_menu.addSeparator()

        # Recent files submenu
        self.recent_files_menu = file_menu.addMenu('Recente Projecten')
        self.update_recent_files_menu()

        clear_recent_action = file_menu.addAction('Wis Recente Projecten')
        clear_recent_action.triggered.connect(self.clear_recent_files)

        file_menu.addSeparator()

        logger.info(f"Menu: File menu created {time.time() - start:.2f}s")

        # Export submenu
        export_menu = file_menu.addMenu('Export')

        # Advanced single export with options
        advanced_export_action = export_menu.addAction('Geavanceerde Export...')
        advanced_export_action.setShortcut('Ctrl+E')
        advanced_export_action.setToolTip('Exporteer met keuze voor modus, cijfers, grid en legenda')
        advanced_export_action.triggered.connect(self.advanced_export)

        export_menu.addSeparator()

        export_png_action = export_menu.addAction('Snelle PNG Export...')
        export_png_action.setShortcut('Ctrl+Shift+P')
        export_png_action.triggered.connect(self.export_png)

        export_with_legend_action = export_menu.addAction('Exporteer met Legenda...')
        export_with_legend_action.setShortcut('Ctrl+L')
        export_with_legend_action.triggered.connect(self.export_with_legend)

        export_all_action = export_menu.addAction('Export All Varianten...')
        export_all_action.setShortcut('Ctrl+Shift+E')
        export_all_action.setToolTip('Exporteer alle modi en varianten (cijfers, grid, legenda)')
        export_all_action.triggered.connect(self.export_all_variants)

        export_menu.addSeparator()

        batch_export_action = export_menu.addAction('Batch Export (Alle Modi)...')
        batch_export_action.triggered.connect(self.batch_export)

        export_svg_action = export_menu.addAction('Exporteer SVG...')
        export_svg_action.triggered.connect(self.export_svg)

        export_pdf_action = export_menu.addAction('Exporteer PDF met Grid...')
        export_pdf_action.triggered.connect(self.export_pdf_with_grid)

        file_menu.addSeparator()

        quit_action = file_menu.addAction('Afsluiten')
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(self.close)

        logger.info(f"Menu: File menu complete {time.time() - start:.2f}s")

        # Edit menu
        edit_menu = menubar.addMenu('Bewerken')

        undo_action = edit_menu.addAction('Ongedaan maken')
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.undo_color_change)

        redo_action = edit_menu.addAction('Opnieuw')
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.redo_color_change)

        edit_menu.addSeparator()

        auto_merge_action = edit_menu.addAction('⚡ Auto-Merge Vergelijkbare Kleuren...')
        auto_merge_action.setShortcut('Ctrl+Shift+M')
        auto_merge_action.setToolTip('Detecteer en voeg automatisch zeer vergelijkbare kleuren samen (>90%)')
        auto_merge_action.triggered.connect(self.auto_merge_similar_colors)

        smart_merge_action = edit_menu.addAction('🤖 Slimme Samenvoeg Suggesties...')
        smart_merge_action.setShortcut('Ctrl+M')
        smart_merge_action.triggered.connect(self.suggest_smart_merges)

        logger.info(f"Menu: Edit menu complete {time.time() - start:.2f}s")

        # View menu
        view_menu = menubar.addMenu('Weergave')

        presentation_action = view_menu.addAction('🖥 Presentatie Mode')
        presentation_action.setShortcut('F11')
        presentation_action.triggered.connect(self.enter_presentation_mode)

        view_menu.addSeparator()

        # Grid overlay toggle (checkable)
        self.grid_toggle_action = view_menu.addAction('📐 Grid Overlay')
        self.grid_toggle_action.setCheckable(True)
        self.grid_toggle_action.setChecked(False)
        self.grid_toggle_action.setShortcut('Ctrl+G')
        self.grid_toggle_action.triggered.connect(self.toggle_grid_overlay)

        magnifier_toggle_action = view_menu.addAction('🔍 Vergrootglas')
        magnifier_toggle_action.setCheckable(True)
        magnifier_toggle_action.setChecked(True)
        magnifier_toggle_action.setShortcut('M')
        magnifier_toggle_action.triggered.connect(self.toggle_magnifier)

        logger.info(f"Menu: View menu complete {time.time() - start:.2f}s")

        # Help menu
        help_menu = menubar.addMenu('❓ Help')

        shortcuts_action = help_menu.addAction('⌨️ Sneltoetsen Overzicht')
        shortcuts_action.setShortcut('F1')
        shortcuts_action.setToolTip("Bekijk alle beschikbare sneltoetsen")
        shortcuts_action.triggered.connect(self.show_shortcuts)

        help_menu.addSeparator()

        documentation_action = help_menu.addAction('📚 Documentatie')
        documentation_action.setToolTip("Open online documentatie")
        documentation_action.triggered.connect(self.open_documentation)

        tips_action = help_menu.addAction('💡 Tips & Tricks')
        tips_action.setToolTip("Leer handige tips")
        tips_action.triggered.connect(self.show_tips)

        help_menu.addSeparator()

        about_action = help_menu.addAction('ℹ️ Over JSPR Beamer Setup')
        about_action.triggered.connect(self.show_about)

        logger.info(f"Menu: Help menu complete {time.time() - start:.2f}s")

    def create_control_panel(self) -> QWidget:
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)  # More spacing between sections
        layout.setContentsMargins(12, 12, 12, 12)  # More padding

        # === BESTAND SECTION ===
        file_group = QGroupBox("Bestand")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(10)  # More spacing within section

        # Open button
        self.open_btn = QPushButton("Open Afbeelding...")
        self.open_btn.setMinimumHeight(32)
        self.open_btn.clicked.connect(self.open_image)
        file_layout.addWidget(self.open_btn)

        # Image preview
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(260, 120)
        self.image_preview.setStyleSheet("border: 2px dashed rgba(255,255,255,0.3); padding: 4px; border-radius: 8px;")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setText("Geen afbeelding")
        file_layout.addWidget(self.image_preview)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # === KLEUREN SECTION ===
        colors_group = QGroupBox("Kleuren")
        colors_layout = QVBoxLayout()
        colors_layout.setSpacing(10)

        # Color count
        color_count_layout = QHBoxLayout()
        color_count_layout.addWidget(QLabel("Aantal:"))
        self.color_count_spin = QSpinBox()
        self.color_count_spin.setRange(2, 32)
        self.color_count_spin.setValue(8)
        self.color_count_spin.setMaximumWidth(60)
        color_count_layout.addWidget(self.color_count_spin)
        colors_layout.addLayout(color_count_layout)

        # Detect colors button
        self.detect_colors_btn = QPushButton("Detecteer Kleuren")
        self.detect_colors_btn.clicked.connect(self.show_color_selection_dialog)
        colors_layout.addWidget(self.detect_colors_btn)

        # Black/White selection button
        self.black_white_btn = QPushButton("Markeer Zwart/Wit...")
        self.black_white_btn.setToolTip("Selecteer welke kleuren als zwart of wit behandeld moeten worden")
        self.black_white_btn.clicked.connect(self.open_black_white_dialog)
        colors_layout.addWidget(self.black_white_btn)

        colors_group.setLayout(colors_layout)
        layout.addWidget(colors_group)

        # === VISUALISATIE SECTION ===
        mode_group = QGroupBox("Visualisatie")
        mode_layout = QVBoxLayout()
        mode_layout.setSpacing(10)

        self.mode_original_btn = QPushButton("Origineel")
        self.mode_original_btn.setCheckable(True)
        self.mode_original_btn.setChecked(True)
        self.mode_original_btn.clicked.connect(lambda: self.set_mode('original'))
        mode_layout.addWidget(self.mode_original_btn)

        self.mode_pbn_btn = QPushButton("Paint-by-Numbers")
        self.mode_pbn_btn.setCheckable(True)
        self.mode_pbn_btn.clicked.connect(lambda: self.set_mode('paintByNumbers'))
        mode_layout.addWidget(self.mode_pbn_btn)

        self.mode_line_btn = QPushButton("Lijntekening")
        self.mode_line_btn.setCheckable(True)
        self.mode_line_btn.clicked.connect(lambda: self.set_mode('lineDrawing'))
        mode_layout.addWidget(self.mode_line_btn)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # === WEERGAVE SECTION ===
        display_group = QGroupBox("Weergave")
        display_layout = QVBoxLayout()
        display_layout.setSpacing(10)

        # Real-time updates checkbox
        self.realtime_checkbox = QCheckBox("Live voorvertoning")
        self.realtime_checkbox.setChecked(True)
        self.realtime_checkbox.setToolTip("Automatisch updaten bij parameter wijzigingen")
        self.realtime_checkbox.stateChanged.connect(self.on_realtime_toggled)
        display_layout.addWidget(self.realtime_checkbox)

        # Show outlines checkbox
        self.show_outlines_checkbox = QCheckBox("Toon contouren")
        self.show_outlines_checkbox.setChecked(False)
        self.show_outlines_checkbox.setToolTip("Toon/verberg omtreklijnen")
        self.show_outlines_checkbox.stateChanged.connect(self.on_parameter_changed)
        display_layout.addWidget(self.show_outlines_checkbox)

        # Hide black fill checkbox (only for line drawing mode)
        self.hide_black_checkbox = QCheckBox("Verberg zwart (alleen contouren)")
        self.hide_black_checkbox.setChecked(False)
        self.hide_black_checkbox.setToolTip("Verberg zwarte vulling en toon alleen contouren (lijntekening modus)")
        self.hide_black_checkbox.stateChanged.connect(self.on_parameter_changed)
        display_layout.addWidget(self.hide_black_checkbox)

        # Herbereken button (hidden when real-time is on)
        self.recalc_btn = QPushButton("Herbereken")
        self.recalc_btn.setToolTip("Handmatig updaten (Ctrl+R)")
        self.recalc_btn.clicked.connect(self.update_parameters)
        self.recalc_btn.setVisible(False)
        display_layout.addWidget(self.recalc_btn)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # === TEKENING PARAMETERS SECTION ===
        drawing_group = QGroupBox("Tekening")
        drawing_layout = QVBoxLayout()
        drawing_layout.setSpacing(10)

        # Line width
        line_width_layout = QHBoxLayout()
        line_width_layout.addWidget(QLabel("Lijndikte:"))
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.5, 10.0)
        self.line_width_spin.setSingleStep(0.5)
        self.line_width_spin.setValue(0.5)
        self.line_width_spin.setDecimals(1)
        self.line_width_spin.setMaximumWidth(60)
        self.line_width_spin.valueChanged.connect(self.on_parameter_changed)
        line_width_layout.addWidget(self.line_width_spin)
        drawing_layout.addLayout(line_width_layout)

        # Number size
        number_size_layout = QHBoxLayout()
        number_size_layout.addWidget(QLabel("Cijfergrootte:"))
        self.number_size_spin = QSpinBox()
        self.number_size_spin.setRange(4, 32)
        self.number_size_spin.setValue(16)
        self.number_size_spin.setMaximumWidth(60)
        self.number_size_spin.valueChanged.connect(self.on_parameter_changed)
        number_size_layout.addWidget(self.number_size_spin)
        drawing_layout.addLayout(number_size_layout)

        # Min region size
        region_size_layout = QHBoxLayout()
        region_size_layout.addWidget(QLabel("Min. vlak:"))
        self.region_size_spin = QSpinBox()
        self.region_size_spin.setRange(10, 1000)
        self.region_size_spin.setSingleStep(10)
        self.region_size_spin.setValue(20)
        self.region_size_spin.setMaximumWidth(60)
        self.region_size_spin.valueChanged.connect(self.on_parameter_changed)
        self.region_size_spin.installEventFilter(self)
        region_size_layout.addWidget(self.region_size_spin)
        drawing_layout.addLayout(region_size_layout)

        # Grid size
        grid_size_layout = QHBoxLayout()
        grid_size_layout.addWidget(QLabel("Grid grootte:"))
        self.grid_size_spin = QSpinBox()
        self.grid_size_spin.setRange(2, 12)
        self.grid_size_spin.setValue(4)
        self.grid_size_spin.setMaximumWidth(60)
        self.grid_size_spin.setToolTip("Grid grootte voor export (2x2 tot 12x12)")
        self.grid_size_spin.valueChanged.connect(self.on_grid_settings_changed)
        grid_size_layout.addWidget(self.grid_size_spin)
        grid_size_layout.addWidget(QLabel("×"))
        grid_size_layout.addWidget(self.grid_size_spin)
        grid_size_layout.addStretch()
        drawing_layout.addLayout(grid_size_layout)

        # Grid color
        grid_color_layout = QHBoxLayout()
        grid_color_layout.addWidget(QLabel("Grid kleur:"))
        self.grid_color_combo = QComboBox()
        self.grid_color_combo.addItems(["Gifgroen", "Magenta", "Cyaan", "Geel", "Zwart", "Grijs"])
        self.grid_color_combo.setCurrentIndex(0)  # Default: Gifgroen
        self.grid_color_combo.setMaximumWidth(120)
        self.grid_color_combo.setToolTip("Kleur voor grid overlay en export")
        self.grid_color_combo.currentIndexChanged.connect(self.on_grid_settings_changed)
        grid_color_layout.addWidget(self.grid_color_combo)
        grid_color_layout.addStretch()
        drawing_layout.addLayout(grid_color_layout)

        drawing_group.setLayout(drawing_layout)
        layout.addWidget(drawing_group)

        # === TOOLS SECTION ===
        tools_group = QGroupBox("Tools")
        tools_layout = QVBoxLayout()
        tools_layout.setSpacing(10)

        # Presentation mode button
        self.presentation_btn = QPushButton("Presentatiemodus")
        self.presentation_btn.setToolTip("Open in fullscreen presentatiemodus")
        self.presentation_btn.clicked.connect(self.enter_presentation_mode)
        tools_layout.addWidget(self.presentation_btn)

        # Magnifier toggle button
        self.magnifier_toggle_btn = QPushButton("Vergrootglas (M)")
        self.magnifier_toggle_btn.setCheckable(True)
        self.magnifier_toggle_btn.setChecked(True)
        self.magnifier_toggle_btn.setToolTip("Toggle vergrootglas bij cursor (sneltoets: M)")
        self.magnifier_toggle_btn.clicked.connect(self.toggle_magnifier)
        tools_layout.addWidget(self.magnifier_toggle_btn)

        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # Selection Tools section
        selection_group = QGroupBox("Selectie Tools")
        selection_layout = QVBoxLayout()
        selection_layout.setSpacing(10)

        # Info label
        info_label = QLabel("Selecteer gebieden om kleur toe te passen")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10px; color: #666;")
        selection_layout.addWidget(info_label)

        # Tool buttons
        tools_layout = QHBoxLayout()

        self.magic_wand_btn = QPushButton("Wand")
        self.magic_wand_btn.setCheckable(True)
        self.magic_wand_btn.setToolTip("Magic Wand - Klik om vergelijkbare kleuren te selecteren\nShift+Klik: voeg toe aan selectie")
        self.magic_wand_btn.setMaximumWidth(60)
        self.magic_wand_btn.clicked.connect(lambda: self.set_selection_mode(SelectionMode.MAGIC_WAND))
        tools_layout.addWidget(self.magic_wand_btn)

        self.brush_btn = QPushButton("Brush")
        self.brush_btn.setCheckable(True)
        self.brush_btn.setToolTip("Brush - Verf over gebieden\nCtrl: wis selectie")
        self.brush_btn.setMaximumWidth(60)
        self.brush_btn.clicked.connect(lambda: self.set_selection_mode(SelectionMode.BRUSH))
        tools_layout.addWidget(self.brush_btn)

        self.polygon_btn = QPushButton("Polygon")
        self.polygon_btn.setCheckable(True)
        self.polygon_btn.setToolTip("Polygon - Klik punten om vorm te maken\nEnter: voltooi, Esc: annuleer")
        self.polygon_btn.setMaximumWidth(60)
        self.polygon_btn.clicked.connect(lambda: self.set_selection_mode(SelectionMode.POLYGON))
        tools_layout.addWidget(self.polygon_btn)

        selection_layout.addLayout(tools_layout)

        # Brush size (for brush tool)
        brush_size_layout = QHBoxLayout()
        brush_size_layout.addWidget(QLabel("Kwast:"))
        self.brush_size_spin = QSpinBox()
        self.brush_size_spin.setRange(5, 100)
        self.brush_size_spin.setValue(20)
        self.brush_size_spin.setMaximumWidth(60)
        self.brush_size_spin.valueChanged.connect(self.on_brush_size_changed)
        brush_size_layout.addWidget(self.brush_size_spin)
        selection_layout.addLayout(brush_size_layout)

        # Tolerance (for magic wand)
        tolerance_layout = QHBoxLayout()
        tolerance_layout.addWidget(QLabel("Tolerantie:"))
        self.tolerance_spin = QSpinBox()
        self.tolerance_spin.setRange(5, 100)
        self.tolerance_spin.setValue(30)
        self.tolerance_spin.setMaximumWidth(60)
        self.tolerance_spin.valueChanged.connect(self.on_tolerance_changed)
        tolerance_layout.addWidget(self.tolerance_spin)
        selection_layout.addLayout(tolerance_layout)

        # Selection stats
        self.selection_stats_label = QLabel("Geen selectie")
        self.selection_stats_label.setStyleSheet("font-size: 10px; color: #666;")
        selection_layout.addWidget(self.selection_stats_label)

        # Action buttons
        self.clear_selection_btn = QPushButton("Wis Selectie")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        self.clear_selection_btn.setEnabled(False)
        selection_layout.addWidget(self.clear_selection_btn)

        self.apply_selection_btn = QPushButton("Pas Selectie Toe")
        self.apply_selection_btn.clicked.connect(self.apply_selection)
        self.apply_selection_btn.setEnabled(False)
        self.apply_selection_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        selection_layout.addWidget(self.apply_selection_btn)

        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)

        # Hide selection tools for now
        selection_group.setVisible(False)

        # Stretch to push everything to top
        layout.addStretch()

        return panel

    def create_canvas_panel(self) -> QWidget:
        """Create center canvas panel"""
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Canvas controls
        controls_layout = QHBoxLayout()

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setMaximumWidth(40)
        zoom_in_btn.clicked.connect(lambda: self.zoom(0.1))
        controls_layout.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setMaximumWidth(40)
        zoom_out_btn.clicked.connect(lambda: self.zoom(-0.1))
        controls_layout.addWidget(zoom_out_btn)

        zoom_reset_btn = QPushButton("Reset")
        zoom_reset_btn.clicked.connect(self.reset_zoom)
        controls_layout.addWidget(zoom_reset_btn)

        presentation_btn = QPushButton("Presentatie Mode")
        presentation_btn.setToolTip("Open fullscreen beamer mode (F11)")
        presentation_btn.setStyleSheet("""
            background-color: #4A90E2;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        """)
        presentation_btn.clicked.connect(self.enter_presentation_mode)
        controls_layout.addWidget(presentation_btn)

        controls_layout.addStretch()

        self.zoom_label = QLabel("100%")
        controls_layout.addWidget(self.zoom_label)

        layout.addLayout(controls_layout)

        # Canvas (add with stretch to fill available space)
        self.canvas = CanvasWidget()
        self.canvas.color_picked.connect(self.on_color_picked)
        self.canvas.zoom_changed.connect(self.on_zoom_changed)
        self.canvas.quality_change_needed.connect(self.on_quality_change_needed)
        layout.addWidget(self.canvas, stretch=1)

        return panel

    def create_legend_panel(self) -> QWidget:
        """Create right legend panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QLabel("<h3>Kleuren</h3>")
        layout.addWidget(header)

        # Project statistics
        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("""
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 11px;
        """)
        layout.addWidget(self.stats_label)

        # Status Indicator
        self.status_indicator = StatusIndicator()
        layout.addWidget(self.status_indicator)

        # Sorting dropdown
        sort_layout = QHBoxLayout()
        sort_layout.setSpacing(10)

        sort_label = QLabel("Sorteer op:")
        sort_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Helderheid", "Tint", "Gebruik"])
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        sort_layout.addWidget(self.sort_combo, stretch=1)

        layout.addLayout(sort_layout)

        # Legend scroll area
        self.legend_widget = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_widget)
        self.legend_layout.setSpacing(4)
        self.legend_layout.setContentsMargins(0, 4, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.legend_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        layout.addWidget(scroll_area, stretch=1)

        return panel

    def on_sort_changed(self, index: int):
        """Handle sort dropdown selection"""
        sort_modes = ['brightness', 'hue', 'usage']
        if 0 <= index < len(sort_modes):
            self.sort_colors(sort_modes[index])

    def open_image(self):
        """Open image file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Afbeelding",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )

        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path: str):
        """Load image from file"""
        self.statusBar().showMessage(f"Laden: {os.path.basename(file_path)}...")

        # Switch to main UI if still on welcome screen
        self.switch_to_main_ui()

        success = self.image_processor.load_image(file_path)

        if success:
            self.current_file_path = file_path
            self.add_to_recent_files(file_path)

            # Update status indicator
            if self.status_indicator:
                self.status_indicator.set_status("image_loaded", True)

            # Update button states
            self.update_button_states()

            # Update preview
            img = self.image_processor.get_image_copy()
            self.update_preview(img)

            # Set original image for eyedropper
            self.canvas.set_original_image(img)

            # Track original image in memory manager (lazy loaded)
            self.get_memory_manager().add_image_version(
                key=f"original_{os.path.basename(file_path)}",
                image=img,
                metadata={'type': 'original', 'file_path': file_path}
            )

            # Initialize selection tools
            self.init_selection_tools()

            # Show color selection dialog
            logger.info("Showing ColorSelectionDialog...")
            dialog = ColorSelectionDialog(self)
            result = dialog.exec_()

            logger.info(f"Dialog result: {result}, selection_mode: {dialog.selection_mode}")

            if result == QDialog.Accepted:
                if dialog.selection_mode == 'automatic':
                    logger.info("Starting automatic color detection")
                    # Auto-detect colors
                    self.detect_colors_automatic()
                elif dialog.selection_mode == 'manual':
                    logger.info("Starting manual color picker")
                    # Show manual color picker
                    self.show_manual_color_picker(img)
                else:
                    logger.warning(f"Unknown selection mode: {dialog.selection_mode}")
            else:
                # Dialog was closed without selection
                logger.info("ColorSelectionDialog was cancelled")
                self.statusBar().showMessage(f"Geladen: {os.path.basename(file_path)} - Kies kleuren om verder te gaan")

            self.statusBar().showMessage(f"Geladen: {os.path.basename(file_path)}")
        else:
            QMessageBox.critical(self, "Fout", "Kan afbeelding niet laden")
            self.statusBar().showMessage("Fout bij laden")

    def show_manual_color_picker(self, image: np.ndarray):
        """Show manual color picker fullscreen interface"""
        logger.info("Creating ManualColorPicker window...")

        # Create manual color picker and store as instance variable
        self.manual_picker = ManualColorPicker(image, self)
        logger.info(f"ManualColorPicker created: {self.manual_picker}")

        # Connect signals
        self.manual_picker.colors_selected.connect(self.on_manual_colors_selected)
        self.manual_picker.cancelled.connect(self.on_manual_selection_cancelled)
        logger.info("Signals connected")

        # Show fullscreen and ensure it's on top
        logger.info("Calling show() first...")
        self.manual_picker.show()  # Show normally first

        logger.info("Now calling showFullScreen()...")
        self.manual_picker.showFullScreen()
        self.manual_picker.raise_()
        self.manual_picker.activateWindow()

        # Force update to trigger paintEvent
        self.manual_picker.update()
        logger.info("ManualColorPicker should now be visible")

        self.statusBar().showMessage("Handmatige kleur selectie - Klik op kleuren om toe te voegen")

    def on_manual_colors_selected(self, colors: List[Color]):
        """Handle colors selected from manual picker"""
        logger.info(f"Manual selection complete: {len(colors)} colors")

        # Update color manager with selected colors
        self.color_manager.colors = colors

        # Update color palette display
        self.update_color_palette()

        # Clear visualizer cache
        self.visualizer.clear_cache()

        # Render the image with the selected colors
        self.render()

        self.statusBar().showMessage(f"Handmatige selectie voltooid: {len(colors)} kleuren geselecteerd")

        # Cleanup picker reference
        self.manual_picker = None

    def on_manual_selection_cancelled(self):
        """Handle manual color selection cancelled"""
        logger.info("Manual color selection cancelled")
        self.statusBar().showMessage("Handmatige kleur selectie geannuleerd")

        # Cleanup picker reference
        self.manual_picker = None

    def update_preview(self, image: np.ndarray):
        """Update image preview thumbnail"""
        # Resize for preview
        height, width = image.shape[:2]
        scale = min(280 / width, 180 / height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        preview = cv2.resize(image, (new_width, new_height))

        # Convert to QPixmap
        bytes_per_line = 3 * new_width
        q_image = QImage(
            preview.data,
            new_width,
            new_height,
            bytes_per_line,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(q_image)
        self.image_preview.setPixmap(pixmap)

    def show_color_selection_dialog(self):
        """Show dialog to choose between automatic and manual color detection"""
        if self.image_processor.original_image is None:
            QMessageBox.warning(self, "Geen afbeelding", "Laad eerst een afbeelding")
            return

        # Show color selection dialog
        logger.info("Showing ColorSelectionDialog...")
        dialog = ColorSelectionDialog(self)
        result = dialog.exec_()

        logger.info(f"Dialog result: {result}, selection_mode: {dialog.selection_mode}")

        if result == QDialog.Accepted:
            if dialog.selection_mode == 'automatic':
                logger.info("Starting automatic color detection")
                # Auto-detect colors
                self.detect_colors_automatic()
            elif dialog.selection_mode == 'manual':
                logger.info("Starting manual color picker")
                # Show manual color picker
                img = self.image_processor.get_image_copy()
                self.show_manual_color_picker(img)
            else:
                logger.warning(f"Unknown selection mode: {dialog.selection_mode}")
        else:
            logger.info("ColorSelectionDialog was cancelled")

    def detect_colors_automatic(self):
        """Detect colors using K-means (automatic mode)"""
        if self.image_processor.original_image is None:
            return

        num_colors = self.color_count_spin.value()

        # Show progress dialog
        progress = QProgressDialog("Kleuren detecteren...", None, 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        def progress_callback(percent, message):
            progress.setValue(int(percent))
            progress.setLabelText(message)

        # Detect colors
        progress_callback(0, "K-means clustering...")
        colors = self.image_processor.detect_colors(num_colors)

        progress_callback(50, "Kleuren verwerken...")
        self.color_manager.set_colors(colors)

        # Update status indicator
        if self.status_indicator:
            self.status_indicator.set_status("colors_detected", True)

        # Update button states
        self.update_button_states()

        progress_callback(80, "Interface updaten...")
        self.update_color_palette()

        progress_callback(100, "Klaar!")
        progress.close()

        # Render
        self.render()

    def update_color_palette(self):
        """Update color legend display"""
        # Clear right legend (editable view)
        while self.legend_layout.count():
            child = self.legend_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add color items to legend
        colors = self.color_manager.get_colors()

        for color in colors:
            self.add_legend_item(color)

        self.legend_layout.addStretch()

    def add_legend_item(self, color: Color):
        """Add an editable color item to the legend"""
        # Use HoverWidget to detect mouse hover
        item_widget = HoverWidget(color.number - 1, self)  # color.number is 1-based, need 0-based index
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(6, 4, 6, 4)
        item_layout.setSpacing(8)

        # Number label
        num_label = QLabel(f"<b>{color.number}</b>")
        num_label.setFixedWidth(25)
        num_label.setAlignment(Qt.AlignCenter)
        item_layout.addWidget(num_label)

        # Color swatch
        swatch = QLabel()
        swatch.setFixedSize(32, 24)
        swatch.setStyleSheet(f"""
            background-color: {color.to_hex()};
            border: 1px solid #888;
            border-radius: 2px;
        """)
        item_layout.addWidget(swatch)

        # Editable color name
        name_edit = QLineEdit(color.name)
        name_edit.setStyleSheet("padding: 4px;")
        name_edit.editingFinished.connect(lambda: self.on_color_name_changed(color, name_edit.text()))
        item_layout.addWidget(name_edit, stretch=1)

        # Merge button
        merge_btn = QPushButton("↔")
        merge_btn.setFixedSize(22, 22)
        merge_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #4CAF50;
                color: white;
            }
        """)
        merge_btn.setToolTip("Samenvoegen met andere kleur")
        merge_btn.clicked.connect(lambda: self.merge_color(color))
        item_layout.addWidget(merge_btn)

        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(22, 22)
        delete_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #f44336;
                color: white;
            }
        """)
        delete_btn.setToolTip("Verwijder kleur")
        delete_btn.clicked.connect(lambda: self.delete_color(color))
        item_layout.addWidget(delete_btn)

        self.legend_layout.addWidget(item_widget)

    def on_color_name_changed(self, color: Color, new_name: str):
        """Handle color name change"""
        if new_name and new_name != color.name:
            old_name = color.name
            color.name = new_name
            logger.info(f"Color {color.number} renamed from '{old_name}' to '{new_name}'")

            # Update palette display
            self.update_color_palette()

            # Auto-recompute if image exists
            if self.image_processor.original_image is not None:
                self.render()

    def merge_color(self, initial_color: Color = None):
        """Merge multiple colors into a base color with similarity percentages"""
        colors = self.color_manager.get_colors()

        if len(colors) <= 2:
            QMessageBox.warning(
                self,
                "Kan niet samenvoegen",
                "Je moet minimaal 3 kleuren hebben om samen te voegen"
            )
            return

        # STEP 1: Select BASE COLOR (target)
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QScrollArea, QCheckBox

        base_dialog = QDialog(self)
        base_dialog.setWindowTitle("Selecteer Basiskleur")
        base_dialog.setModal(True)
        base_dialog.setMinimumWidth(450)
        base_dialog.setMinimumHeight(500)

        base_layout = QVBoxLayout()

        # Instructions
        instruction = QLabel("<h3>Stap 1: Selecteer de basiskleur</h3><p>Andere kleuren worden hiermee samengevoegd.</p>")
        instruction.setWordWrap(True)
        base_layout.addWidget(instruction)

        # Color selection area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        base_color = [initial_color if initial_color else None]

        for color in colors:
            color_widget = QWidget()
            color_layout = QHBoxLayout(color_widget)
            color_layout.setContentsMargins(8, 4, 8, 4)

            # Radio button
            radio = QRadioButton()
            if initial_color and color.id == initial_color.id:
                radio.setChecked(True)
            color_layout.addWidget(radio)

            # Color swatch
            swatch = QLabel()
            swatch.setFixedSize(50, 40)
            swatch.setStyleSheet(f"background-color: {color.to_hex()}; border: 2px solid #888; border-radius: 3px;")
            color_layout.addWidget(swatch)

            # Color info
            info = QLabel(f"<b>#{color.number}</b> - {color.name}")
            info.setMinimumWidth(200)
            color_layout.addWidget(info, stretch=1)

            # Store reference when selected
            radio.toggled.connect(lambda checked, c=color: base_color.__setitem__(0, c) if checked else None)

            scroll_layout.addWidget(color_widget)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        base_layout.addWidget(scroll_area)

        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annuleren")
        cancel_btn.clicked.connect(base_dialog.reject)
        button_layout.addWidget(cancel_btn)

        next_btn = QPushButton("Volgende →")
        next_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        next_btn.clicked.connect(base_dialog.accept)
        button_layout.addWidget(next_btn)

        base_layout.addLayout(button_layout)
        base_dialog.setLayout(base_layout)

        # Show dialog
        if base_dialog.exec_() != QDialog.Accepted or base_color[0] is None:
            return

        target_color = base_color[0]

        # STEP 2: Select MULTIPLE COLORS to merge with similarity percentages
        merge_dialog = QDialog(self)
        merge_dialog.setWindowTitle(f"Samenvoegen met: {target_color.name}")
        merge_dialog.setModal(True)
        merge_dialog.setMinimumWidth(500)
        merge_dialog.setMinimumHeight(600)

        merge_layout = QVBoxLayout()

        # Instructions
        instruction2 = QLabel(f"<h3>Stap 2: Selecteer kleuren om samen te voegen</h3><p>Deze kleuren worden samengevoegd met <b>{target_color.name}</b>.</p>")
        instruction2.setWordWrap(True)
        merge_layout.addWidget(instruction2)

        # Color selection area with checkboxes
        scroll_area2 = QScrollArea()
        scroll_widget2 = QWidget()
        scroll_layout2 = QVBoxLayout(scroll_widget2)

        selected_colors = []
        checkboxes = []

        # Calculate similarity for each color
        target_rgb = (target_color.r, target_color.g, target_color.b)

        for color in colors:
            if color.id == target_color.id:
                continue  # Skip the base color itself

            # Calculate color similarity (Euclidean distance in RGB space)
            color_rgb = (color.r, color.g, color.b)
            distance = ((target_rgb[0] - color_rgb[0])**2 +
                       (target_rgb[1] - color_rgb[1])**2 +
                       (target_rgb[2] - color_rgb[2])**2) ** 0.5

            # Convert to percentage (0 = identical, 441.67 = max distance)
            max_distance = (255**2 + 255**2 + 255**2) ** 0.5
            similarity_percentage = int((1 - distance / max_distance) * 100)

            color_widget = QWidget()
            color_layout = QHBoxLayout(color_widget)
            color_layout.setContentsMargins(8, 4, 8, 4)

            # Checkbox
            checkbox = QCheckBox()
            checkboxes.append((checkbox, color))
            color_layout.addWidget(checkbox)

            # Color swatch
            swatch = QLabel()
            swatch.setFixedSize(50, 40)
            swatch.setStyleSheet(f"background-color: {color.to_hex()}; border: 2px solid #888; border-radius: 3px;")
            color_layout.addWidget(swatch)

            # Color info with similarity
            info = QLabel(f"<b>#{color.number}</b> - {color.name}")
            info.setMinimumWidth(200)
            color_layout.addWidget(info, stretch=1)

            # Similarity percentage
            similarity_label = QLabel(f"<b>{similarity_percentage}%</b>")
            similarity_label.setMinimumWidth(50)
            similarity_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Color code similarity
            if similarity_percentage >= 80:
                similarity_label.setStyleSheet("color: #4CAF50; font-weight: bold;")  # Green
            elif similarity_percentage >= 60:
                similarity_label.setStyleSheet("color: #FFC107; font-weight: bold;")  # Orange
            else:
                similarity_label.setStyleSheet("color: #888; font-weight: bold;")  # Gray

            color_layout.addWidget(similarity_label)

            scroll_layout2.addWidget(color_widget)

        scroll_layout2.addStretch()
        scroll_area2.setWidget(scroll_widget2)
        scroll_area2.setWidgetResizable(True)
        merge_layout.addWidget(scroll_area2)

        # Helper text
        helper = QLabel("💡 Tip: Hogere percentages betekenen meer gelijkenis")
        helper.setStyleSheet("color: #888; font-style: italic; padding: 5px;")
        merge_layout.addWidget(helper)

        # Buttons
        button_layout2 = QHBoxLayout()

        back_btn = QPushButton("← Terug")
        back_btn.clicked.connect(merge_dialog.reject)
        button_layout2.addWidget(back_btn)

        button_layout2.addStretch()

        merge_btn = QPushButton("Samenvoegen")
        merge_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")

        def do_merge():
            # Collect selected colors
            selected = [color for checkbox, color in checkboxes if checkbox.isChecked()]
            if not selected:
                QMessageBox.warning(merge_dialog, "Geen selectie", "Selecteer minimaal 1 kleur om samen te voegen")
                return
            merge_dialog.accept()

            # Perform merges (efficient: only render once at the end)
            color_names = [c.name for c in selected]
            for i, source_color in enumerate(selected):
                is_last = (i == len(selected) - 1)
                self.perform_color_merge(source_color, target_color, render=is_last)

            # Show summary message
            if len(selected) == 1:
                self.statusBar().showMessage(f"'{color_names[0]}' samengevoegd met '{target_color.name}'")
            else:
                self.statusBar().showMessage(f"{len(selected)} kleuren samengevoegd met '{target_color.name}': {', '.join(color_names)}")

            logger.info(f"Batch merge complete. {len(selected)} colors merged into '{target_color.name}'")

        merge_btn.clicked.connect(do_merge)
        button_layout2.addWidget(merge_btn)

        merge_layout.addLayout(button_layout2)
        merge_dialog.setLayout(merge_layout)

        # Show dialog
        merge_dialog.exec_()

    def perform_color_merge(self, source_color: Color, target_color: Color, render: bool = True):
        """Perform the actual color merge operation"""
        logger.info(f"Merging '{source_color.name}' into '{target_color.name}'")

        # Get the image processor to remap colors
        if self.visualizer.color_map is None:
            QMessageBox.warning(
                self,
                "Geen data",
                "Render eerst de afbeelding voordat je kleuren kan samenvoegen"
            )
            return

        # Find which color index to replace
        source_index = source_color.number - 1
        target_index = target_color.number - 1

        # Remap all source_index pixels to target_index in color_map
        self.visualizer.color_map[self.visualizer.color_map == source_index] = target_index

        # Remove source color from color manager
        self.color_manager.remove_color(source_color.id)

        # Renumber remaining colors
        for i, c in enumerate(self.color_manager.get_colors()):
            c.number = i + 1

        # Update color map indices (shift down all colors after source)
        # This is needed because we removed a color and renumbered
        for old_num in range(source_color.number, len(self.color_manager.get_colors()) + 2):
            old_idx = old_num - 1
            new_idx = old_idx - 1
            if old_idx > source_index:
                self.visualizer.color_map[self.visualizer.color_map == old_idx] = new_idx

        # Update palette display (always needed)
        self.update_color_palette()

        # Only render if requested (for efficiency in batch merges)
        if render:
            self.visualizer.clear_cache()
            self.render()

        logger.info(f"Merge complete. Remaining colors: {len(self.color_manager.get_colors())}")

    def auto_merge_similar_colors(self):
        """Automatically detect and merge highly similar colors (>90% similarity)"""
        if not self.color_manager.get_colors():
            QMessageBox.warning(self, "Geen kleuren", "Er zijn geen kleuren om samen te voegen")
            return

        colors = self.color_manager.get_colors()
        if len(colors) <= 2:
            QMessageBox.information(self, "Geen kleuren", "Er zijn te weinig kleuren om samen te voegen")
            return

        # Calculate similarity for all color pairs
        similar_pairs = []
        max_distance = (255**2 + 255**2 + 255**2) ** 0.5

        for i, color1 in enumerate(colors):
            for j, color2 in enumerate(colors):
                if i >= j:
                    continue

                # Calculate similarity percentage
                color1_rgb = (color1.r, color1.g, color1.b)
                color2_rgb = (color2.r, color2.g, color2.b)
                distance = ((color1_rgb[0] - color2_rgb[0])**2 +
                           (color1_rgb[1] - color2_rgb[1])**2 +
                           (color1_rgb[2] - color2_rgb[2])**2) ** 0.5
                similarity = int((1 - distance / max_distance) * 100)

                # Only include pairs with >90% similarity
                if similarity >= 90:
                    similar_pairs.append({
                        'color1': color1,
                        'color2': color2,
                        'similarity': similarity
                    })

        if not similar_pairs:
            QMessageBox.information(
                self,
                "Geen vergelijkbare kleuren",
                "Er zijn geen kleuren gevonden met >90% overeenkomst.\n\n"
                "Tip: Gebruik 'Slimme Samenvoeg Suggesties' voor meer opties."
            )
            return

        # Sort by similarity (highest first)
        similar_pairs.sort(key=lambda x: x['similarity'], reverse=True)

        # Show dialog to confirm merges
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QCheckBox, QSpinBox

        dialog = QDialog(self)
        dialog.setWindowTitle("⚡ Auto-Merge Vergelijkbare Kleuren")
        dialog.setModal(True)
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Header with instructions
        header = QLabel(
            f"<h3>Gevonden: {len(similar_pairs)} zeer vergelijkbare kleurparen</h3>"
            f"<p>Selecteer welke paren je wilt samenvoegen. De tweede kleur wordt samengevoegd met de eerste.</p>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Threshold slider
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Minimale overeenkomst:"))
        threshold_spin = QSpinBox()
        threshold_spin.setRange(50, 99)
        threshold_spin.setValue(90)
        threshold_spin.setSuffix("%")
        threshold_layout.addWidget(threshold_spin)
        threshold_layout.addStretch()
        layout.addLayout(threshold_layout)

        # Scroll area for pairs
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        pair_checkboxes = []

        def update_pairs():
            # Clear existing
            for i in reversed(range(scroll_layout.count())):
                scroll_layout.itemAt(i).widget().deleteLater()

            pair_checkboxes.clear()
            threshold = threshold_spin.value()

            # Re-filter and display
            filtered_pairs = [p for p in similar_pairs if p['similarity'] >= threshold]

            if not filtered_pairs:
                no_pairs_label = QLabel(f"Geen kleurparen gevonden met ≥{threshold}% overeenkomst")
                no_pairs_label.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
                scroll_layout.addWidget(no_pairs_label)
            else:
                for pair in filtered_pairs:
                    pair_widget = QWidget()
                    pair_layout = QHBoxLayout(pair_widget)
                    pair_layout.setContentsMargins(4, 4, 4, 4)

                    # Checkbox
                    checkbox = QCheckBox()
                    checkbox.setChecked(True)
                    pair_checkboxes.append((checkbox, pair))
                    pair_layout.addWidget(checkbox)

                    # Color 1 swatch
                    swatch1 = QLabel()
                    swatch1.setFixedSize(40, 30)
                    swatch1.setStyleSheet(
                        f"background-color: {pair['color1'].to_hex()}; "
                        f"border: 2px solid #888; border-radius: 3px;"
                    )
                    pair_layout.addWidget(swatch1)

                    # Color 1 info
                    info1 = QLabel(f"#{pair['color1'].number} {pair['color1'].name}")
                    info1.setMinimumWidth(150)
                    pair_layout.addWidget(info1)

                    # Arrow
                    arrow = QLabel("→")
                    arrow.setStyleSheet("font-size: 16px; font-weight: bold;")
                    pair_layout.addWidget(arrow)

                    # Color 2 swatch
                    swatch2 = QLabel()
                    swatch2.setFixedSize(40, 30)
                    swatch2.setStyleSheet(
                        f"background-color: {pair['color2'].to_hex()}; "
                        f"border: 2px solid #888; border-radius: 3px;"
                    )
                    pair_layout.addWidget(swatch2)

                    # Color 2 info
                    info2 = QLabel(f"#{pair['color2'].number} {pair['color2'].name}")
                    info2.setMinimumWidth(150)
                    pair_layout.addWidget(info2)

                    # Similarity
                    similarity_label = QLabel(f"<b>{pair['similarity']}%</b>")
                    similarity_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                    similarity_label.setMinimumWidth(60)
                    pair_layout.addWidget(similarity_label)

                    scroll_layout.addWidget(pair_widget)

            scroll_layout.addStretch()

        threshold_spin.valueChanged.connect(lambda: update_pairs())
        update_pairs()

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()

        select_all_btn = QPushButton("Selecteer Alles")
        select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb, _ in pair_checkboxes])
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselecteer Alles")
        deselect_all_btn.clicked.connect(lambda: [cb.setChecked(False) for cb, _ in pair_checkboxes])
        button_layout.addWidget(deselect_all_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Annuleren")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        merge_btn = QPushButton("Samenvoegen")
        merge_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")

        def do_merge():
            selected = [(pair['color2'], pair['color1']) for cb, pair in pair_checkboxes if cb.isChecked()]
            if not selected:
                QMessageBox.warning(dialog, "Geen selectie", "Selecteer minimaal 1 paar om samen te voegen")
                return

            dialog.accept()

            # Perform merges (efficient: only render once at end)
            for i, (source, target) in enumerate(selected):
                is_last = (i == len(selected) - 1)
                self.perform_color_merge(source, target, render=is_last)

            # Show summary
            self.statusBar().showMessage(f"⚡ Auto-merge voltooid: {len(selected)} kleurparen samengevoegd")
            logger.info(f"Auto-merge complete: {len(selected)} pairs merged")

        merge_btn.clicked.connect(do_merge)
        button_layout.addWidget(merge_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        dialog.exec_()

    def suggest_smart_merges(self):
        """Analyze colors and suggest smart merges based on similarity and region fragmentation"""
        if self.visualizer.color_map is None or not self.color_manager.get_colors():
            QMessageBox.warning(
                self,
                "Geen data",
                "Render eerst de afbeelding om merge suggesties te krijgen"
            )
            return

        colors = self.color_manager.get_colors()
        if len(colors) <= 2:
            QMessageBox.information(
                self,
                "Geen suggesties",
                "Er zijn te weinig kleuren om samen te voegen"
            )
            return

        # Analyze color similarity and region fragmentation
        suggestions = []

        for i, color1 in enumerate(colors):
            for j, color2 in enumerate(colors):
                if i >= j:
                    continue

                # Calculate color distance (Euclidean distance in RGB space)
                dr = color1.r - color2.r
                dg = color1.g - color2.g
                db = color1.b - color2.b
                distance = (dr*dr + dg*dg + db*db) ** 0.5

                # Count regions for each color
                idx1 = color1.number - 1
                idx2 = color2.number - 1

                if self.visualizer.color_map is not None:
                    mask1 = self.visualizer.color_map == idx1
                    mask2 = self.visualizer.color_map == idx2

                    # Count pixels
                    pixels1 = np.sum(mask1)
                    pixels2 = np.sum(mask2)

                    # Calculate fragmentation (number of separate regions)
                    import cv2
                    num_regions1 = cv2.connectedComponents(mask1.astype(np.uint8).reshape(
                        self.image_processor.original_image.shape[:2]))[0] - 1
                    num_regions2 = cv2.connectedComponents(mask2.astype(np.uint8).reshape(
                        self.image_processor.original_image.shape[:2]))[0] - 1

                    # Calculate score (lower is better for merging)
                    # Factors: color similarity (low distance), high fragmentation, small pixel count
                    similarity_score = distance / 255.0  # Normalize to 0-1
                    fragmentation_score = (num_regions1 + num_regions2) / 100.0  # Higher fragmentation = better candidate
                    size_penalty = min(pixels1, pixels2) / (pixels1 + pixels2)  # Favor merging smaller colors

                    # Combined score: low distance + high fragmentation = good merge candidate
                    merge_score = similarity_score - fragmentation_score * 0.3 - size_penalty * 0.2

                    if distance < 80 or (num_regions1 > 20 or num_regions2 > 20):  # Similar colors or very fragmented
                        suggestions.append({
                            'color1': color1,
                            'color2': color2,
                            'distance': distance,
                            'regions1': num_regions1,
                            'regions2': num_regions2,
                            'score': merge_score,
                            'pixels1': pixels1,
                            'pixels2': pixels2
                        })

        if not suggestions:
            QMessageBox.information(
                self,
                "Geen suggesties",
                "Er zijn geen duidelijke merge kandidaten gevonden.\n\n" +
                "Alle kleuren zijn voldoende verschillend en hebben geen extreem veel kleine vlakken."
            )
            return

        # Sort by score (best suggestions first)
        suggestions.sort(key=lambda x: x['score'])

        # Show dialog with suggestions
        self.show_merge_suggestions_dialog(suggestions[:10])  # Top 10 suggestions

    def show_merge_suggestions_dialog(self, suggestions):
        """Show dialog with merge suggestions"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("🤖 Slimme Samenvoeg Suggesties")
        dialog.setModal(True)
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout(dialog)

        # Info label
        info = QLabel(
            f"Gevonden: {len(suggestions)} suggesties\n\n" +
            "Deze kleuren lijken op elkaar of hebben veel kleine vlakken:"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Scroll area for suggestions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for i, sug in enumerate(suggestions):
            # Create suggestion card
            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    padding: 12px;
                    margin: 4px;
                }
            """)
            card_layout = QHBoxLayout(card)

            # Color swatches
            swatch1 = QLabel()
            swatch1.setFixedSize(40, 40)
            swatch1.setStyleSheet(f"""
                background-color: rgb({sug['color1'].r}, {sug['color1'].g}, {sug['color1'].b});
                border: 2px solid white;
                border-radius: 4px;
            """)
            card_layout.addWidget(swatch1)

            arrow = QLabel("→")
            arrow.setStyleSheet("font-size: 20px; font-weight: bold;")
            card_layout.addWidget(arrow)

            swatch2 = QLabel()
            swatch2.setFixedSize(40, 40)
            swatch2.setStyleSheet(f"""
                background-color: rgb({sug['color2'].r}, {sug['color2'].g}, {sug['color2'].b});
                border: 2px solid white;
                border-radius: 4px;
            """)
            card_layout.addWidget(swatch2)

            # Info text
            info_text = QLabel(
                f"<b>{sug['color1'].name}</b> → <b>{sug['color2'].name}</b><br>" +
                f"<small>Kleurverschil: {sug['distance']:.1f} | " +
                f"Vlakken: {sug['regions1']}+{sug['regions2']} | " +
                f"Pixels: {sug['pixels1']:.0f}+{sug['pixels2']:.0f}</small>"
            )
            info_text.setWordWrap(True)
            card_layout.addWidget(info_text, 1)

            # Merge button
            merge_btn = QPushButton("✓ Samenvoegen")
            merge_btn.setMaximumWidth(120)
            merge_btn.clicked.connect(lambda checked, s=sug, d=dialog: self.apply_suggested_merge(s, d))
            card_layout.addWidget(merge_btn)

            scroll_layout.addWidget(card)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Close button
        close_btn = QPushButton("Sluiten")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def apply_suggested_merge(self, suggestion, dialog):
        """Apply a suggested merge"""
        self.perform_color_merge(suggestion['color1'], suggestion['color2'])
        dialog.accept()

        # Ask if user wants more suggestions
        result = QMessageBox.question(
            self,
            "Meer suggesties?",
            "Wil je nog meer samenvoeg suggesties zien?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.suggest_smart_merges()

    def delete_color(self, color: Color):
        """Delete a color from the palette"""
        colors = self.color_manager.get_colors()

        if len(colors) <= 2:
            QMessageBox.warning(
                self,
                "Kan niet verwijderen",
                "Je moet minimaal 2 kleuren behouden"
            )
            return

        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Kleur verwijderen",
            f"Weet je zeker dat je kleur '{color.name}' wilt verwijderen?\n\nDe afbeelding wordt automatisch opnieuw berekend.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            # Remove color
            self.color_manager.remove_color(color.id)
            logger.info(f"Deleted color {color.number}: {color.name}")

            # Renumber remaining colors
            for i, c in enumerate(self.color_manager.get_colors()):
                c.number = i + 1

            # Update palette
            self.update_color_palette()

            # Auto-recompute
            if self.image_processor.original_image is not None:
                # Need to re-detect/re-quantize with new color count
                self.render()

    def sort_colors(self, mode: str):
        """Sort colors by brightness, hue, or usage"""
        if not self.color_manager.get_colors():
            return

        if mode == 'brightness':
            self.color_manager.sort_by_brightness()
        elif mode == 'hue':
            self.color_manager.sort_by_hue()
        elif mode == 'usage':
            # Need color_map for usage sorting
            if self.visualizer.color_map is not None:
                self.color_manager.sort_by_usage(self.visualizer.color_map)
            else:
                QMessageBox.warning(
                    self,
                    "Geen data",
                    "Render eerst de afbeelding voordat je op gebruik kan sorteren"
                )
                return
        else:
            logger.warning(f"Unknown sort mode: {mode}")
            return

        # Update UI
        self.update_color_palette()

        # Clear cache and re-render
        self.visualizer.clear_cache()
        self.render()

        # Update statistics after sorting
        self.update_statistics()

        logger.info(f"Colors sorted by {mode}")

    def calculate_statistics(self) -> dict:
        """Calculate color usage statistics"""
        stats = {
            'total_pixels': 0,
            'color_stats': []
        }

        if self.visualizer.color_map is None:
            return stats

        try:
            color_map_flat = self.visualizer.color_map.flatten()
            stats['total_pixels'] = len(color_map_flat)

            # Calculate stats for each color
            for color in self.color_manager.get_colors():
                color_index = color.number - 1
                pixel_count = int(np.sum(color_map_flat == color_index))
                coverage = (pixel_count / stats['total_pixels'] * 100) if stats['total_pixels'] > 0 else 0

                # Count regions for this color
                if self.visualizer.color_map is not None:
                    # Ensure we have the right shape
                    if len(self.visualizer.color_map.shape) == 1:
                        # Need to reshape - get shape from original image
                        if self.image_processor.original_image is not None:
                            height, width = self.image_processor.original_image.shape[:2]
                            color_map_2d = self.visualizer.color_map.reshape(height, width)
                        else:
                            region_count = 0
                            stats['color_stats'].append({
                                'color': color,
                                'pixels': pixel_count,
                                'coverage': coverage,
                                'regions': region_count
                            })
                            continue
                    else:
                        color_map_2d = self.visualizer.color_map

                    mask = (color_map_2d == color_index).astype(np.uint8)

                    # Find contours to count regions
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    region_count = len(contours)
                else:
                    region_count = 0

                stats['color_stats'].append({
                    'color': color,
                    'pixels': pixel_count,
                    'coverage': coverage,
                    'regions': region_count
                })

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}", exc_info=True)

        return stats

    def update_statistics(self):
        """Update statistics label with color usage data"""
        # Safety check: ensure stats_label exists
        if not hasattr(self, 'stats_label') or self.stats_label is None:
            return

        if self.visualizer.color_map is None:
            self.stats_label.setText("")
            return

        try:
            stats = self.calculate_statistics()

            if not stats['color_stats']:
                self.stats_label.setText("")
                return

            # Calculate complexity score (1-10 scale)
            total_regions = sum(s['regions'] for s in stats['color_stats'])
            num_colors = len(stats['color_stats'])
            avg_regions_per_color = total_regions / num_colors if num_colors > 0 else 0

            # Calculate average region size (smaller = harder)
            total_pixels = sum(s['pixels'] for s in stats['color_stats'])
            avg_region_size = total_pixels / total_regions if total_regions > 0 else 0

            # Complexity factors (normalized 0-10):
            # 1. Color count (more colors = harder)
            color_score = min(num_colors / 3, 10)  # 30+ colors = max score

            # 2. Region fragmentation (more regions = harder)
            region_score = min(avg_regions_per_color / 10, 10)  # 100+ regions/color = max

            # 3. Small regions (smaller avg = harder)
            size_score = max(0, 10 - (avg_region_size / 100))  # <100px = high score

            # Weighted average: regions matter most, then colors, then size
            complexity_raw = (region_score * 0.5 + color_score * 0.3 + size_score * 0.2)
            complexity_score = max(1, min(10, round(complexity_raw)))

            # Determine difficulty label and emoji
            if complexity_score <= 3:
                difficulty = f"★☆☆ Makkelijk (Score: {complexity_score}/10)"
                emoji = "😊"
            elif complexity_score <= 6:
                difficulty = f"★★☆ Gemiddeld (Score: {complexity_score}/10)"
                emoji = "🙂"
            elif complexity_score <= 8:
                difficulty = f"★★★ Uitdagend (Score: {complexity_score}/10)"
                emoji = "😅"
            else:
                difficulty = f"★★★★ Expert (Score: {complexity_score}/10)"
                emoji = "🔥"

            # Format statistics text
            lines = [
                f"<b>📊 Project Statistieken</b>",
                f"",
                f"Kleuren: <b>{num_colors}</b>",
                f"Gebieden: <b>{total_regions}</b>",
                f"Gem. per kleur: <b>{avg_regions_per_color:.1f}</b>",
                f"Gem. grootte: <b>{avg_region_size:.0f}px</b>",
                f"",
                f"{emoji} <b>{difficulty}</b>",
            ]

            self.stats_label.setText("<br>".join(lines))
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            self.stats_label.setText("")

    def set_mode(self, mode: str):
        """Set visualization mode"""
        self.current_mode = mode
        self.visualizer.set_mode(mode)

        # Update button states
        self.mode_original_btn.setChecked(mode == 'original')
        self.mode_pbn_btn.setChecked(mode == 'paintByNumbers')
        self.mode_line_btn.setChecked(mode == 'lineDrawing')

        # Render
        self.render()

    def on_parameter_changed(self):
        """Handle parameter change - only update if real-time is enabled"""
        if self.realtime_checkbox.isChecked():
            self.update_parameters()

    def on_realtime_toggled(self):
        """Handle real-time checkbox toggle"""
        is_realtime = self.realtime_checkbox.isChecked()
        # Show/hide manual recalculate button
        self.recalc_btn.setVisible(not is_realtime)
        # If turning on real-time, trigger immediate update
        if is_realtime:
            self.update_parameters()

    def on_grid_settings_changed(self):
        """Handle grid settings change"""
        # Update canvas grid settings
        if hasattr(self, 'canvas'):
            self.canvas.grid_size = self.grid_size_spin.value() * 50  # Convert to pixels
            # Update grid color
            color_map = {
                0: (0, 255, 0),      # Gifgroen
                1: (255, 0, 255),    # Magenta
                2: (0, 255, 255),    # Cyaan
                3: (255, 255, 0),    # Geel
                4: (0, 0, 0),        # Zwart
                5: (128, 128, 128)   # Grijs
            }
            r, g, b = color_map.get(self.grid_color_combo.currentIndex(), (0, 255, 0))
            self.canvas.grid_color = QColor(r, g, b, 120)  # Semi-transparent
            if self.canvas.show_grid:
                self.canvas.update()

        # Update presentation mode if open
        if hasattr(self, 'presentation_window') and self.presentation_window:
            self.presentation_window.grid_size = self.grid_size_spin.value()
            self.presentation_window.grid_color_index = min(self.grid_color_combo.currentIndex(), 3)  # Limit to 4 colors

    def update_parameters(self):
        """Update visualization parameters"""
        self.visualizer.set_parameters(
            line_width=self.line_width_spin.value(),
            number_size=self.number_size_spin.value(),
            min_region_size=self.region_size_spin.value(),
            show_outlines=self.show_outlines_checkbox.isChecked(),
            hide_black_fill=self.hide_black_checkbox.isChecked()
        )

        # Clear cache to force re-render
        self.visualizer.clear_cache()

        # Re-render
        self.render()

    def render(self):
        """Render current visualization"""
        if self.image_processor.original_image is None:
            return

        self.statusBar().showMessage("Renderen...")

        # Render image
        result = self.visualizer.render()

        if result is not None:
            self.canvas.set_image(result)
            self.statusBar().showMessage("Klaar")

            # Track rendered image in memory manager (lazy loaded)
            import time
            self.get_memory_manager().add_image_version(
                key=f"rendered_{self.current_mode}_{int(time.time())}",
                image=result,
                metadata={'type': 'rendered', 'mode': self.current_mode}
            )

            # Update status indicator
            if self.status_indicator:
                self.status_indicator.set_status("rendered", True)

            # Update button states
            self.update_button_states()

            # Update statistics after successful render
            self.update_statistics()
        else:
            self.statusBar().showMessage("Fout bij renderen")

    def zoom(self, delta: float):
        """Zoom canvas"""
        current_zoom = self.canvas.zoom_level
        new_zoom = current_zoom + delta
        self.canvas.set_zoom(new_zoom)
        self.zoom_label.setText(f"{int(new_zoom * 100)}%")

    def reset_zoom(self):
        """Reset zoom to 100%"""
        self.canvas.set_zoom(1.0)
        self.zoom_label.setText("100%")

    def on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changed from canvas"""
        self.zoom_label.setText(f"{int(zoom_level * 100)}%")

    def on_quality_change_needed(self, zoom_level: float):
        """Handle quality threshold crossed - re-render at appropriate resolution"""
        logger.info(f"Re-rendering at zoom level {zoom_level} for better quality")

        # Scale parameters based on zoom level for better quality
        # At higher zoom, use larger font sizes and line widths
        zoom_scale = max(0.5, min(2.0, zoom_level))  # Clamp scaling between 0.5x and 2.0x

        self.visualizer.set_parameters(
            line_width=self.line_width_spin.value() * zoom_scale,
            number_size=self.number_size_spin.value() * zoom_scale,
            min_region_size=self.region_size_spin.value(),
            show_outlines=self.show_outlines_checkbox.isChecked(),
            hide_black_fill=self.hide_black_checkbox.isChecked()
        )

        # Clear cache and re-render
        self.visualizer.clear_cache()
        self.render()

        self.statusBar().showMessage(f"Kwaliteit aangepast voor zoom {int(zoom_level * 100)}%", 2000)

    def toggle_eyedropper(self):
        """Toggle eyedropper mode"""
        is_checked = self.eyedropper_btn.isChecked()
        self.canvas.set_eyedropper_mode(is_checked)

        if is_checked:
            self.statusBar().showMessage("Pipet modus: Klik op de afbeelding om een kleur te kiezen")
        else:
            self.statusBar().showMessage("Pipet modus uitgeschakeld")

    def on_color_picked(self, r: int, g: int, b: int):
        """Handle color picked from eyedropper"""
        # Show confirmation message with color preview
        msg = QMessageBox(self)
        msg.setWindowTitle("Kleur Gepickt")
        msg.setText(f"Kleur gepickt: RGB({r}, {g}, {b})")
        msg.setInformativeText("Wil je deze kleur toevoegen aan het palet?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)

        # Create color swatch label
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
        swatch_html = f'<div style="width: 100px; height: 50px; background-color: {color_hex}; border: 2px solid #ccc;"></div>'

        result = msg.exec_()

        if result == QMessageBox.Yes:
            # Add color to palette
            self.add_color_to_palette(r, g, b)

            # Turn off eyedropper mode
            self.eyedropper_btn.setChecked(False)
            self.canvas.set_eyedropper_mode(False)

            self.statusBar().showMessage(f"Kleur RGB({r}, {g}, {b}) toegevoegd aan palet")
        else:
            self.statusBar().showMessage("Kleur niet toegevoegd")

    def add_color_to_palette(self, r: int, g: int, b: int):
        """Add a new color to the palette"""
        # Get existing colors
        colors = self.color_manager.get_colors()

        # Check if color already exists (within threshold)
        threshold = 10
        for color in colors:
            if (abs(color.r - r) < threshold and
                abs(color.g - g) < threshold and
                abs(color.b - b) < threshold):
                QMessageBox.information(
                    self,
                    "Kleur bestaat al",
                    f"Deze kleur bestaat al in het palet als '{color.name}'"
                )
                return

        # Add new color
        self.color_manager.add_color(r, g, b)

        # Update UI
        self.update_color_palette()

        # Clear cache and re-render
        self.visualizer.clear_cache()
        self.render()

    def open_black_white_dialog(self):
        """Open dialog to select black/white colors"""
        if not self.color_manager.get_colors():
            QMessageBox.warning(
                self,
                "Geen kleuren",
                "Detecteer eerst kleuren voordat je zwart/wit kan selecteren"
            )
            return

        # Open dialog
        dialog = BlackWhiteSelectionDialog(self.color_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            # Get selections
            black_colors, white_colors = dialog.get_selections()

            # Reset all colors first
            for color in self.color_manager.get_colors():
                color.is_black = False
                color.is_white = False

            # Apply black selections
            for color in black_colors:
                color.is_black = True
                color.is_white = False  # Can't be both
                logger.info(f"Color {color.number} '{color.name}' marked as black")

            # Apply white selections
            for color in white_colors:
                color.is_white = True
                color.is_black = False  # Can't be both
                logger.info(f"Color {color.number} '{color.name}' marked as white")

            # Clear cache and re-render immediately
            self.visualizer.clear_cache()
            self.render()

            # Update presentation mode if open
            if self.presentation_window and self.canvas.image is not None:
                self.presentation_window.set_image(self.canvas.image)

            self.statusBar().showMessage(
                f"Zwart/wit selectie toegepast: {len(black_colors)} zwart, {len(white_colors)} wit"
            )

    def enter_presentation_mode(self):
        """Enter fullscreen presentation mode"""
        if self.canvas.image is None:
            QMessageBox.warning(
                self,
                "Geen afbeelding",
                "Render eerst een afbeelding voordat je naar presentatie mode gaat"
            )
            return

        # Create presentation window if it doesn't exist
        if self.presentation_window is None:
            self.presentation_window = PresentationMode()
            self.presentation_window.closed.connect(self.on_presentation_closed)
            self.presentation_window.toggle_numbers_requested.connect(self.on_toggle_numbers_presentation)
            self.presentation_window.cycle_mode_requested.connect(self.on_cycle_mode_presentation)
            self.presentation_window.toggle_outlines_requested.connect(self.on_toggle_outlines_presentation)
            self.presentation_window.quality_change_needed.connect(self.on_presentation_quality_change)

        # Set current image
        self.presentation_window.set_image(self.canvas.image)
        if self.image_processor.original_image is not None:
            self.presentation_window.set_original_image(
                self.image_processor.get_image_copy()
            )

        # Show in fullscreen
        self.presentation_window.showFullScreen()
        self.statusBar().showMessage("Presentatie mode gestart - Druk ESC om te sluiten")

    def on_presentation_closed(self):
        """Handle presentation mode closed"""
        # Bring main window to front and activate it
        self.show()
        self.raise_()
        self.activateWindow()
        self.statusBar().showMessage("Presentatie mode gesloten")

    def on_toggle_numbers_presentation(self):
        """Handle toggle numbers from presentation mode"""
        # Toggle in visualizer
        current_state = self.visualizer.show_numbers
        self.visualizer.set_show_numbers(not current_state)

        # Re-render
        result = self.visualizer.render_current_mode()
        if result is not None:
            self.canvas.set_image(result)
            # Update presentation window
            if self.presentation_window:
                self.presentation_window.set_image(result)

        logger.info(f"Numbers toggled: {self.visualizer.show_numbers}")

    def on_toggle_outlines_presentation(self):
        """Handle toggle outlines from presentation mode"""
        # Toggle checkbox state
        current_state = self.show_outlines_checkbox.isChecked()
        self.show_outlines_checkbox.setChecked(not current_state)

        # Update visualizer parameters
        self.visualizer.set_parameters(
            line_width=self.line_width_spin.value(),
            number_size=self.number_size_spin.value(),
            min_region_size=self.region_size_spin.value(),
            show_outlines=not current_state,
            hide_black_fill=self.hide_black_checkbox.isChecked()
        )

        # Clear cache and re-render
        self.visualizer.clear_cache()
        result = self.visualizer.render_current_mode()
        if result is not None:
            self.canvas.set_image(result)
            # Update presentation window
            if self.presentation_window:
                self.presentation_window.set_image(result)

        logger.info(f"Outlines toggled: {not current_state}")

    def on_cycle_mode_presentation(self):
        """Handle cycle mode from presentation mode"""
        # Cycle through modes
        modes = ['original', 'paintByNumbers', 'lineDrawing']
        current_idx = modes.index(self.current_mode)
        next_idx = (current_idx + 1) % len(modes)
        next_mode = modes[next_idx]

        # Set new mode
        self.set_mode(next_mode)

        # Update presentation window
        if self.presentation_window and self.canvas.image is not None:
            self.presentation_window.set_image(self.canvas.image)

        logger.info(f"Mode cycled to: {next_mode}")

    def on_presentation_quality_change(self, zoom_level: float):
        """Handle quality threshold crossed in presentation mode - re-render at appropriate resolution"""
        logger.info(f"Re-rendering for presentation mode at zoom level {zoom_level}")

        # Scale parameters based on zoom level for better quality
        # At higher zoom, use larger font sizes and line widths
        zoom_scale = max(0.5, min(2.0, zoom_level))  # Clamp scaling between 0.5x and 2.0x

        self.visualizer.set_parameters(
            line_width=self.line_width_spin.value() * zoom_scale,
            number_size=self.number_size_spin.value() * zoom_scale,
            min_region_size=self.region_size_spin.value(),
            show_outlines=self.show_outlines_checkbox.isChecked(),
            hide_black_fill=self.hide_black_checkbox.isChecked()
        )

        # Clear cache and re-render
        self.visualizer.clear_cache()
        result = self.visualizer.render()

        if result is not None:
            # Update both canvas and presentation window
            self.canvas.set_image(result)
            if self.presentation_window:
                self.presentation_window.set_image(result)

        logger.info(f"Presentation quality updated for zoom {int(zoom_level * 100)}%")

    def save_project(self):
        """Save current project as .jspr file"""
        if self.image_processor.original_image is None:
            QMessageBox.warning(self, "Geen project", "Laad eerst een afbeelding")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Project Opslaan",
            "",
            "JSPR Project (*.jspr);;All Files (*)"
        )

        if file_path:
            # Gather current parameters
            parameters = {
                'line_width': self.line_width_spin.value(),
                'number_size': self.number_size_spin.value(),
                'min_region_size': self.region_size_spin.value(),
                'show_outlines': self.show_outlines_checkbox.isChecked(),
                'hide_black_fill': self.hide_black_checkbox.isChecked()
            }

            # Save project
            success = ProjectManager.save_project(
                file_path,
                self.image_processor.get_image_copy(),
                self.color_manager,
                parameters,
                self.current_mode
            )

            if success:
                QMessageBox.information(
                    self,
                    "Project Opgeslagen",
                    f"Project opgeslagen als:\n{file_path}"
                )
                self.statusBar().showMessage(f"Project opgeslagen: {file_path}")
            else:
                QMessageBox.critical(
                    self,
                    "Fout",
                    "Kon project niet opslaan"
                )

    def load_project(self):
        """Load project from .jspr file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Project Openen",
            "",
            "JSPR Project (*.jspr);;All Files (*)"
        )

        if file_path:
            # Load project data
            project_data = ProjectManager.load_project(file_path)

            if project_data is None:
                QMessageBox.critical(
                    self,
                    "Fout",
                    "Kon project niet laden"
                )
                return

            # Restore image
            image = project_data['image']
            self.image_processor.set_image(image)
            self.update_preview(image)
            self.canvas.set_original_image(image)

            # Restore colors
            colors = project_data['colors']
            self.color_manager.colors = colors
            self.color_manager.next_number = len(colors) + 1
            self.update_color_palette()

            # Restore parameters
            params = project_data['parameters']
            self.line_width_spin.setValue(params.get('line_width', 0.5))
            self.number_size_spin.setValue(params.get('number_size', 16))
            self.region_size_spin.setValue(params.get('min_region_size', 50))
            self.show_outlines_checkbox.setChecked(params.get('show_outlines', True))
            self.hide_black_checkbox.setChecked(params.get('hide_black_fill', False))

            # Restore mode
            self.set_mode(project_data['current_mode'])

            # Render
            self.render()

            # Update current file path and recent files
            self.current_file_path = file_path
            self.add_to_recent_files(file_path)

            self.statusBar().showMessage(f"Project geladen: {file_path}")
            QMessageBox.information(
                self,
                "Project Geladen",
                f"Project succesvol geladen:\n{file_path}"
            )

    def batch_export(self):
        """Export all visualization modes at once"""
        if self.image_processor.original_image is None:
            QMessageBox.warning(self, "Geen afbeelding", "Laad eerst een afbeelding")
            return

        # Ask for base filename
        base_path, _ = QFileDialog.getSaveFileName(
            self,
            "Batch Export - Kies Basisnaam",
            "",
            "PNG Image (*.png)"
        )

        if not base_path:
            return

        # Remove .png extension if present
        if base_path.endswith('.png'):
            base_path = base_path[:-4]

        # Show progress dialog
        progress = QProgressDialog("Batch export...", "Annuleren", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        def progress_callback(percent, message):
            progress.setValue(int(percent))
            progress.setLabelText(message)
            if progress.wasCanceled():
                return False
            return True

        try:
            # Save current mode to restore later
            original_mode = self.current_mode

            # Export Original
            if not progress_callback(10, "Exporteren: Origineel..."):
                return
            self.visualizer.set_mode('original')
            original_img = self.visualizer.render()
            if original_img is not None:
                original_path = f"{base_path}_original.png"
                cv2.imwrite(original_path, cv2.cvtColor(original_img, cv2.COLOR_RGB2BGR))
                logger.info(f"Exported: {original_path}")

            # Export Paint-by-Numbers
            if not progress_callback(40, "Exporteren: Paint-by-Numbers..."):
                return
            self.visualizer.set_mode('paintByNumbers')
            pbn_img = self.visualizer.render()
            if pbn_img is not None:
                pbn_path = f"{base_path}_paintbynumbers.png"
                cv2.imwrite(pbn_path, cv2.cvtColor(pbn_img, cv2.COLOR_RGB2BGR))
                logger.info(f"Exported: {pbn_path}")

            # Export Line Drawing
            if not progress_callback(70, "Exporteren: Lijntekening..."):
                return
            self.visualizer.set_mode('lineDrawing')
            line_img = self.visualizer.render()
            if line_img is not None:
                line_path = f"{base_path}_linedrawing.png"
                cv2.imwrite(line_path, cv2.cvtColor(line_img, cv2.COLOR_RGB2BGR))
                logger.info(f"Exported: {line_path}")

            # Restore original mode and update canvas
            progress_callback(90, "Herstellen...")
            self.visualizer.set_mode(original_mode)
            self.current_mode = original_mode
            restored_img = self.visualizer.render()
            if restored_img is not None:
                self.canvas.set_image(restored_img)

            progress.setValue(100)
            progress.close()

            # Show success message
            QMessageBox.information(
                self,
                "Batch Export Voltooid",
                f"3 bestanden geëxporteerd:\n\n"
                f"• {base_path}_original.png\n"
                f"• {base_path}_paintbynumbers.png\n"
                f"• {base_path}_linedrawing.png"
            )
            self.statusBar().showMessage(f"Batch export voltooid: {base_path}_*.png")

        except Exception as e:
            progress.close()
            logger.error(f"Batch export failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Fout", f"Batch export mislukt:\n{str(e)}")

    def export_png(self):
        """Export as PNG"""
        if self.canvas.image is None:
            QMessageBox.warning(self, "Geen afbeelding", "Render eerst een afbeelding")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporteer PNG",
            "",
            "PNG Files (*.png)"
        )

        if file_path:
            # Convert RGB to BGR for OpenCV
            bgr = cv2.cvtColor(self.canvas.image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(file_path, bgr)
            self.statusBar().showMessage(f"Geëxporteerd: {os.path.basename(file_path)}")

            # Update status indicator
            if self.status_indicator:
                self.status_indicator.set_status("exported", True)

    def export_with_legend(self):
        """Export as PNG with color legend embedded - ALWAYS shows numbers"""
        if self.canvas.image is None:
            QMessageBox.warning(self, "Geen afbeelding", "Render eerst een afbeelding")
            return

        if not self.color_manager.get_colors():
            QMessageBox.warning(self, "Geen kleuren", "Er zijn geen kleuren om weer te geven")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporteer met Legenda",
            "",
            "PNG Files (*.png)"
        )

        if not file_path:
            return

        try:
            # Always render with numbers for legend export
            current_mode = self.visualizer.mode
            self.visualizer.set_show_numbers(True)
            main_image = self.visualizer.render()

            if main_image is None:
                QMessageBox.warning(self, "Render fout", "Kon afbeelding niet renderen")
                return
            img_height, img_width = main_image.shape[:2]

            # Create legend image
            colors = self.color_manager.get_colors()
            legend_width = 400
            row_height = 50
            legend_height = max(img_height, len(colors) * row_height + 100)

            # Create white background for legend
            legend_image = np.ones((legend_height, legend_width, 3), dtype=np.uint8) * 255

            # Add title
            title = "Kleuren Legenda"
            cv2.putText(
                legend_image, title,
                (20, 40),
                cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 0, 0), 2
            )

            # Draw each color in the legend
            y_offset = 80
            for color in colors:
                # Draw color swatch
                swatch_x = 20
                swatch_y = y_offset
                swatch_w = 60
                swatch_h = 40

                # Fill swatch with color (RGB format - will be converted to BGR later)
                cv2.rectangle(
                    legend_image,
                    (swatch_x, swatch_y),
                    (swatch_x + swatch_w, swatch_y + swatch_h),
                    (int(color.r), int(color.g), int(color.b)),  # RGB - converted to BGR at export
                    -1  # Filled
                )

                # Draw swatch border
                cv2.rectangle(
                    legend_image,
                    (swatch_x, swatch_y),
                    (swatch_x + swatch_w, swatch_y + swatch_h),
                    (100, 100, 100),  # Gray border
                    2
                )

                # Draw color number
                number_text = f"{color.number}"
                cv2.putText(
                    legend_image, number_text,
                    (swatch_x + swatch_w + 15, swatch_y + 28),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 0), 2
                )

                # Draw color name
                name_text = color.name
                if len(name_text) > 25:
                    name_text = name_text[:22] + "..."
                cv2.putText(
                    legend_image, name_text,
                    (swatch_x + swatch_w + 60, swatch_y + 28),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 0), 1
                )

                y_offset += row_height

            # Combine images side by side
            # Resize if heights don't match
            if img_height != legend_height:
                if img_height > legend_height:
                    # Expand legend
                    legend_image = cv2.resize(legend_image, (legend_width, img_height))
                else:
                    # Expand main image proportionally
                    scale = legend_height / img_height
                    new_width = int(img_width * scale)
                    main_image = cv2.resize(main_image, (new_width, legend_height))

            # Concatenate horizontally
            combined = np.hstack([main_image, legend_image])

            # Convert RGB to BGR for OpenCV
            bgr = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)
            cv2.imwrite(file_path, bgr)
            self.statusBar().showMessage(f"Geëxporteerd met legenda: {os.path.basename(file_path)}")

            # Update status indicator
            if self.status_indicator:
                self.status_indicator.set_status("exported", True)

        except Exception as e:
            logger.error(f"Error exporting with legend: {e}")
            QMessageBox.critical(
                self,
                "Export Fout",
                f"Kon niet exporteren met legenda:\n{str(e)}"
            )

    def advanced_export(self):
        """Advanced export with full control over mode, numbers, grid, and legend"""
        if self.canvas.image is None:
            QMessageBox.warning(self, "Geen afbeelding", "Render eerst een afbeelding")
            return

        if not self.color_manager.get_colors():
            QMessageBox.warning(self, "Geen kleuren", "Detecteer eerst kleuren")
            return

        from PyQt5.QtWidgets import (QDialog, QRadioButton, QCheckBox, QLineEdit,
                                     QPushButton, QButtonGroup, QFileDialog)

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Geavanceerde Export")
        dialog.setMinimumWidth(550)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)

        # Title
        title = QLabel("<h2>Geavanceerde Export</h2>")
        layout.addWidget(title)

        # Mode selection
        mode_group_box = QGroupBox("Selecteer Modus:")
        mode_layout = QVBoxLayout()

        mode_button_group = QButtonGroup(dialog)
        pbn_radio = QRadioButton("Paint-by-Numbers (gekleurde vakken)")
        line_radio = QRadioButton("Lijntekening (zwart/wit contour)")
        orig_radio = QRadioButton("Origineel (originele afbeelding)")

        # Check current mode to set default
        current_mode = self.visualizer.mode
        if current_mode == 'paintByNumbers':
            pbn_radio.setChecked(True)
        elif current_mode == 'lineDrawing':
            line_radio.setChecked(True)
        else:
            orig_radio.setChecked(True)

        mode_button_group.addButton(pbn_radio, 0)
        mode_button_group.addButton(line_radio, 1)
        mode_button_group.addButton(orig_radio, 2)

        mode_layout.addWidget(pbn_radio)
        mode_layout.addWidget(line_radio)
        mode_layout.addWidget(orig_radio)
        mode_group_box.setLayout(mode_layout)
        layout.addWidget(mode_group_box)

        # Options
        options_group_box = QGroupBox("Opties:")
        options_layout = QVBoxLayout()

        numbers_check = QCheckBox("Cijfers tonen")
        numbers_check.setChecked(self.visualizer.show_numbers)
        numbers_check.setToolTip("Toon kleurnummers in de vakken")

        grid_check = QCheckBox("Grid overlay")
        grid_check.setChecked(False)
        grid_check.setToolTip(f"Voeg {self.grid_size_spin.value()}x{self.grid_size_spin.value()} grid toe met labels")

        legend_check = QCheckBox("Legenda toevoegen")
        legend_check.setChecked(False)
        legend_check.setToolTip("Voeg kleuren legenda toe aan de rechterkant")

        options_layout.addWidget(numbers_check)
        options_layout.addWidget(grid_check)
        options_layout.addWidget(legend_check)
        options_group_box.setLayout(options_layout)
        layout.addWidget(options_group_box)

        # Function to update option availability based on mode
        def update_options_availability():
            """Disable incompatible options for Original mode"""
            is_original = orig_radio.isChecked()

            # Original mode doesn't support numbers, grid, or legend (no color regions)
            numbers_check.setEnabled(not is_original)
            grid_check.setEnabled(not is_original)
            legend_check.setEnabled(not is_original)

            if is_original:
                # Uncheck disabled options
                numbers_check.setChecked(False)
                grid_check.setChecked(False)
                legend_check.setChecked(False)
                # Update tooltips
                numbers_check.setToolTip("Niet beschikbaar voor originele afbeelding")
                grid_check.setToolTip("Niet beschikbaar voor originele afbeelding")
                legend_check.setToolTip("Niet beschikbaar voor originele afbeelding")
            else:
                # Restore normal tooltips
                numbers_check.setToolTip("Toon kleurnummers in de vakken")
                grid_check.setToolTip(f"Voeg {self.grid_size_spin.value()}x{self.grid_size_spin.value()} grid toe met labels")
                legend_check.setToolTip("Voeg kleuren legenda toe aan de rechterkant")

        # Connect mode changes to option availability
        pbn_radio.toggled.connect(update_options_availability)
        line_radio.toggled.connect(update_options_availability)
        orig_radio.toggled.connect(update_options_availability)

        # Initial state
        update_options_availability()

        # Format selection
        format_group_box = QGroupBox("Bestandsformaat:")
        format_layout = QHBoxLayout()

        format_button_group = QButtonGroup(dialog)
        png_radio = QRadioButton("PNG (lossless, grotere bestanden)")
        jpg_radio = QRadioButton("JPG (compressed, kleinere bestanden)")
        png_radio.setChecked(True)

        format_button_group.addButton(png_radio, 0)
        format_button_group.addButton(jpg_radio, 1)

        format_layout.addWidget(png_radio)
        format_layout.addWidget(jpg_radio)
        format_group_box.setLayout(format_layout)
        layout.addWidget(format_group_box)

        # Filename section
        filename_group_box = QGroupBox("Bestandsnaam:")
        filename_layout = QVBoxLayout()

        filename_preview_label = QLabel()
        filename_preview_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")

        filename_edit = QLineEdit()
        filename_edit.setPlaceholderText("Bestandsnaam wordt automatisch gegenereerd...")

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(filename_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.setMaximumWidth(100)
        browse_layout.addWidget(browse_btn)

        # Reset button to restore auto-generated name
        reset_filename_btn = QPushButton("↻")
        reset_filename_btn.setMaximumWidth(35)
        reset_filename_btn.setToolTip("Herstel automatische bestandsnaam")
        browse_layout.addWidget(reset_filename_btn)

        filename_layout.addWidget(QLabel("Automatische bestandsnaam preview:"))
        filename_layout.addWidget(filename_preview_label)
        filename_layout.addWidget(QLabel("Bewerk indien gewenst:"))
        filename_layout.addLayout(browse_layout)

        filename_group_box.setLayout(filename_layout)
        layout.addWidget(filename_group_box)

        # Track whether user has manually edited filename
        user_edited_filename = [False]  # Use list to allow modification in nested functions

        # Function to generate filename
        def generate_filename():
            # Get base name
            if hasattr(self, 'current_file_path') and self.current_file_path:
                base = os.path.splitext(os.path.basename(self.current_file_path))[0]
            else:
                base = "export"

            # Add mode
            if pbn_radio.isChecked():
                parts = [base, "pbn"]
            elif line_radio.isChecked():
                parts = [base, "line"]
            else:
                parts = [base, "orig"]

            # Add options
            if numbers_check.isChecked():
                parts.append("numbers")
            if grid_check.isChecked():
                parts.append("grid")
            if legend_check.isChecked():
                parts.append("legend")

            # Add extension
            ext = "png" if png_radio.isChecked() else "jpg"
            filename = "_".join(parts) + "." + ext

            return filename

        # Function to update filename preview
        def update_filename_preview():
            filename = generate_filename()
            filename_preview_label.setText(f"📄 {filename}")
            # Only auto-update if user hasn't manually edited
            if not user_edited_filename[0]:
                filename_edit.setText(filename)

        # Track manual edits to filename
        def on_filename_edited():
            # Mark as edited only if text differs from auto-generated
            user_edited_filename[0] = True

        # Reset to auto-generated filename
        def reset_filename():
            user_edited_filename[0] = False
            update_filename_preview()

        filename_edit.textEdited.connect(on_filename_edited)
        reset_filename_btn.clicked.connect(reset_filename)

        # Connect all controls to update preview
        pbn_radio.toggled.connect(update_filename_preview)
        line_radio.toggled.connect(update_filename_preview)
        orig_radio.toggled.connect(update_filename_preview)
        numbers_check.toggled.connect(update_filename_preview)
        grid_check.toggled.connect(update_filename_preview)
        legend_check.toggled.connect(update_filename_preview)
        png_radio.toggled.connect(update_filename_preview)
        jpg_radio.toggled.connect(update_filename_preview)

        # Initial preview
        update_filename_preview()

        # Browse button handler
        def browse_file():
            filename = generate_filename()
            ext = "PNG Files (*.png)" if png_radio.isChecked() else "JPG Files (*.jpg)"

            default_path = ""
            if hasattr(self, 'current_file_path') and self.current_file_path:
                default_dir = os.path.dirname(self.current_file_path)
                default_path = os.path.join(default_dir, filename)
            else:
                default_path = filename

            file_path, _ = QFileDialog.getSaveFileName(
                dialog,
                "Kies export locatie",
                default_path,
                ext
            )

            if file_path:
                filename_edit.setText(file_path)

        browse_btn.clicked.connect(browse_file)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Annuleren")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        export_btn = QPushButton("Exporteren")
        export_btn.setDefault(True)
        export_btn.clicked.connect(dialog.accept)
        export_btn.setStyleSheet("font-weight: bold;")
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

        # Show dialog
        if dialog.exec_() != QDialog.Accepted:
            return

        # Get export path
        export_path = filename_edit.text().strip()

        if not export_path:
            # If empty, use generated filename and ask for location
            filename = generate_filename()
            default_path = ""
            if hasattr(self, 'current_file_path') and self.current_file_path:
                default_dir = os.path.dirname(self.current_file_path)
                default_path = os.path.join(default_dir, filename)

            ext = "PNG Files (*.png)" if png_radio.isChecked() else "JPG Files (*.jpg)"
            export_path, _ = QFileDialog.getSaveFileName(
                self,
                "Kies export locatie",
                default_path,
                ext
            )

            if not export_path:
                return

        try:
            # Determine mode
            if pbn_radio.isChecked():
                mode = 'paintByNumbers'
            elif line_radio.isChecked():
                mode = 'lineDrawing'
            else:
                mode = 'original'

            # Get options
            show_numbers = numbers_check.isChecked()
            show_grid = grid_check.isChecked()
            show_legend = legend_check.isChecked()

            # Create progress dialog
            progress = QProgressDialog("Bezig met exporteren...", None, 0, 0, self)
            progress.setWindowTitle("Export")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setCancelButton(None)  # No cancel button for single export
            progress.show()

            # Render variant
            progress.setLabelText("Renderen van afbeelding...")
            result = self.render_variant(mode, show_numbers, show_grid)

            if result is None:
                progress.close()
                QMessageBox.warning(self, "Render fout", "Kon afbeelding niet renderen")
                return

            # Add legend if requested
            if show_legend:
                progress.setLabelText("Legenda toevoegen...")
                result = self.add_legend_to_image(result)

            # Save
            progress.setLabelText("Opslaan...")
            format_ext = 'png' if png_radio.isChecked() else 'jpg'
            self.save_image(result, export_path, format_ext)

            progress.close()

            # Show success message in statusbar only (no popup dialog)
            self.statusBar().showMessage(f"✓ Geëxporteerd: {os.path.basename(export_path)}", 5000)

            # Update status indicator
            if self.status_indicator:
                self.status_indicator.set_status("exported", True)

        except Exception as e:
            logger.error(f"Advanced export failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Export Fout",
                f"Kon niet exporteren:\n{str(e)}"
            )

    def export_svg(self):
        """Export as SVG"""
        if self.visualizer.color_map is None or self.visualizer.contours is None:
            QMessageBox.warning(
                self,
                "Geen data",
                "Render eerst een paint-by-numbers afbeelding"
            )
            return

        # Ask for mode
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QButtonGroup, QPushButton, QCheckBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("SVG Export Instellingen")
        dialog.setModal(True)
        dialog.setMinimumWidth(350)

        layout = QVBoxLayout()

        # Mode selection
        mode_label = QLabel("<b>Export modus:</b>")
        layout.addWidget(mode_label)

        mode_group = QButtonGroup()
        line_radio = QRadioButton("Lijntekening (zwart/wit met cijfers)")
        line_radio.setChecked(True)
        colored_radio = QRadioButton("Gekleurd (met vulkleuren)")

        mode_group.addButton(line_radio)
        mode_group.addButton(colored_radio)

        layout.addWidget(line_radio)
        layout.addWidget(colored_radio)

        layout.addSpacing(10)

        # Numbers checkbox
        numbers_checkbox = QCheckBox("Inclusief cijfers")
        numbers_checkbox.setChecked(True)
        layout.addWidget(numbers_checkbox)

        layout.addSpacing(20)

        # Buttons
        from PyQt5.QtWidgets import QHBoxLayout
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Exporteer")
        cancel_button = QPushButton("Annuleer")

        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        if dialog.exec_() != QDialog.Accepted:
            return

        # Get settings
        mode = 'lineDrawing' if line_radio.isChecked() else 'colored'
        include_numbers = numbers_checkbox.isChecked()

        # Ask for file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporteer SVG",
            "",
            "SVG Files (*.svg)"
        )

        if not file_path:
            return

        try:
            # Generate SVG
            svg_content = self.visualizer.export_svg(mode=mode, include_numbers=include_numbers)

            if svg_content:
                # Save to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)

                self.statusBar().showMessage(f"SVG geëxporteerd: {os.path.basename(file_path)}")

                # Update status indicator
                if self.status_indicator:
                    self.status_indicator.set_status("exported", True)

                QMessageBox.information(
                    self,
                    "SVG Export Succesvol",
                    f"SVG bestand opgeslagen:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Export Mislukt",
                    "Kon SVG niet genereren. Controleer de logs voor details."
                )

        except Exception as e:
            logger.error(f"SVG export error: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Export Fout",
                f"Fout bij SVG export:\n{str(e)}"
            )

    def export_pdf_with_grid(self):
        """Export as PDF with optional grid overlay"""
        if self.canvas.image is None:
            QMessageBox.warning(self, "Geen afbeelding", "Render eerst een afbeelding")
            return

        # Ask for settings
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QSpinBox, QLabel, QHBoxLayout, QPushButton, QComboBox

        dialog = QDialog(self)
        dialog.setWindowTitle("PDF Export Instellingen")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Grid checkbox
        grid_checkbox = QCheckBox("Voeg grid toe")
        grid_checkbox.setChecked(True)
        layout.addWidget(grid_checkbox)

        # Grid size
        grid_layout = QHBoxLayout()
        grid_label = QLabel("Grid grootte (cm):")
        grid_spin = QDoubleSpinBox()
        grid_spin.setRange(0.5, 10.0)
        grid_spin.setSingleStep(0.5)
        grid_spin.setValue(2.0)
        grid_spin.setDecimals(1)
        grid_layout.addWidget(grid_label)
        grid_layout.addWidget(grid_spin)
        layout.addLayout(grid_layout)

        # Page size
        page_layout = QHBoxLayout()
        page_label = QLabel("Papierformaat:")
        page_combo = QComboBox()
        page_combo.addItems(["A4", "A3", "A2", "Letter"])
        page_layout.addWidget(page_label)
        page_layout.addWidget(page_combo)
        layout.addLayout(page_layout)

        # Include legend checkbox
        legend_checkbox = QCheckBox("Inclusief legenda (aparte pagina)")
        legend_checkbox.setChecked(True)
        layout.addWidget(legend_checkbox)

        layout.addSpacing(20)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Exporteer")
        cancel_button = QPushButton("Annuleer")
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        if dialog.exec_() != QDialog.Accepted:
            return

        # Get settings
        include_grid = grid_checkbox.isChecked()
        grid_size_cm = grid_spin.value()
        page_size = page_combo.currentText()
        include_legend = legend_checkbox.isChecked()

        # Ask for file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporteer PDF",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        try:
            from reportlab.lib.pagesizes import A4, A3, A2, LETTER
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas as pdf_canvas
            from PIL import Image
            import io

            # Get page size
            page_sizes = {
                'A4': A4,
                'A3': A3,
                'A2': A2,
                'Letter': LETTER
            }
            page_size_tuple = page_sizes.get(page_size, A4)
            page_width, page_height = page_size_tuple

            # Create PDF
            c = pdf_canvas.Canvas(file_path, pagesize=page_size_tuple)

            # Prepare image
            image_rgb = self.canvas.image.copy()

            # Add grid overlay if requested
            if include_grid:
                img_height, img_width = image_rgb.shape[:2]

                # Calculate grid spacing in pixels
                # Assume we want to map image to fit on page with margins
                margin = 2 * cm
                usable_width = page_width - 2 * margin
                usable_height = page_height - 2 * margin

                # Scale factor to fit image on page
                scale_x = usable_width / img_width
                scale_y = usable_height / img_height
                scale = min(scale_x, scale_y)

                # Grid size in pixels on original image
                grid_size_pixels = int((grid_size_cm * cm) / scale)

                # Draw grid on image
                grid_color = (200, 200, 200)  # Light gray
                for x in range(0, img_width, grid_size_pixels):
                    cv2.line(image_rgb, (x, 0), (x, img_height), grid_color, 1)
                for y in range(0, img_height, grid_size_pixels):
                    cv2.line(image_rgb, (0, y), (img_width, y), grid_color, 1)

            # Convert to PIL Image
            pil_image = Image.fromarray(image_rgb)

            # Calculate dimensions to fit on page with margins
            margin = 2 * cm
            usable_width = page_width - 2 * margin
            usable_height = page_height - 2 * margin

            img_width, img_height = pil_image.size
            scale_x = usable_width / img_width
            scale_y = usable_height / img_height
            scale = min(scale_x, scale_y)

            new_width = img_width * scale
            new_height = img_height * scale

            # Center image on page
            x_offset = margin + (usable_width - new_width) / 2
            y_offset = margin + (usable_height - new_height) / 2

            # Draw image on PDF
            c.drawInlineImage(pil_image, x_offset, y_offset, width=new_width, height=new_height)

            # Add title
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin, page_height - margin / 2, "Paint by Numbers - JSPR Beamer Setup")

            # Add page with legend if requested
            if include_legend and self.color_manager.get_colors():
                c.showPage()  # New page

                # Title
                c.setFont("Helvetica-Bold", 16)
                c.drawString(margin, page_height - margin, "Kleuren Legenda")

                # Draw colors
                y = page_height - margin - 40
                colors = self.color_manager.get_colors()

                for color in colors:
                    if y < margin + 40:  # Check if we need a new page
                        c.showPage()
                        c.setFont("Helvetica-Bold", 16)
                        c.drawString(margin, page_height - margin, "Kleuren Legenda (vervolg)")
                        y = page_height - margin - 40

                    # Draw color swatch
                    c.setFillColorRGB(color.r / 255.0, color.g / 255.0, color.b / 255.0)
                    c.rect(margin, y, 1.5 * cm, 0.8 * cm, fill=1, stroke=1)

                    # Draw color number and name
                    c.setFillColorRGB(0, 0, 0)
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(margin + 2 * cm, y + 0.3 * cm, f"{color.number}.")

                    c.setFont("Helvetica", 11)
                    c.drawString(margin + 3 * cm, y + 0.3 * cm, color.name)

                    y -= 1.2 * cm

            # Save PDF
            c.save()

            self.statusBar().showMessage(f"PDF geëxporteerd: {os.path.basename(file_path)}")

            # Update status indicator
            if self.status_indicator:
                self.status_indicator.set_status("exported", True)

            QMessageBox.information(
                self,
                "PDF Export Succesvol",
                f"PDF bestand opgeslagen:\n{file_path}"
            )

        except Exception as e:
            logger.error(f"PDF export error: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Export Fout",
                f"Fout bij PDF export:\n{str(e)}"
            )

    def eventFilter(self, obj, event):
        """Event filter for shift+click on spinboxes"""
        if obj == self.region_size_spin and event.type() == QEvent.Wheel:
            # Check if shift is pressed
            if event.modifiers() & Qt.ShiftModifier:
                # Temporarily change step size to 100
                self.region_size_spin.setSingleStep(100)
                # Process the event
                result = super().eventFilter(obj, event)
                # Reset step size to 10
                self.region_size_spin.setSingleStep(10)
                return result
        return super().eventFilter(obj, event)

    def undo_color_change(self):
        """Undo last color operation"""
        if self.color_manager.can_undo():
            self.color_manager.undo()
            self.update_color_palette()
            self.visualizer.clear_cache()
            self.render()
            self.statusBar().showMessage("Ongedaan gemaakt")
        else:
            self.statusBar().showMessage("Niets om ongedaan te maken")

    def redo_color_change(self):
        """Redo last undone operation"""
        # TODO: Implement redo functionality in color_manager
        self.statusBar().showMessage("Opnieuw functie komt binnenkort")

    def load_config(self):
        """Load configuration from file"""
        try:
            if self.CONFIG_PATH.exists():
                with open(self.CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    self.recent_files = config.get('recent_files', [])
                    # Validate that files still exist
                    self.recent_files = [f for f in self.recent_files if Path(f).exists()]
                    logger.info(f"Loaded {len(self.recent_files)} recent files")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.recent_files = []

    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                'recent_files': self.recent_files
            }
            with open(self.CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Config saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get_recent_files_with_time(self):
        """Get recent files with time ago information"""
        from datetime import datetime
        result = []
        for file_path in self.recent_files[:5]:  # Max 5 for welcome screen
            if Path(file_path).exists():
                modified_time = Path(file_path).stat().st_mtime
                time_diff = time.time() - modified_time
                if time_diff < 3600:
                    time_ago = f"{int(time_diff / 60)} minuten geleden"
                elif time_diff < 86400:
                    time_ago = f"{int(time_diff / 3600)} uur geleden"
                else:
                    time_ago = f"{int(time_diff / 86400)} dagen geleden"
                result.append((file_path, time_ago))
        return result

    def add_to_recent_files(self, file_path: str):
        """Add file to recent files list"""
        # Convert to absolute path
        file_path = str(Path(file_path).resolve())

        # Remove if already in list
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)

        # Add to beginning
        self.recent_files.insert(0, file_path)

        # Limit to MAX_RECENT_FILES
        self.recent_files = self.recent_files[:self.MAX_RECENT_FILES]

        # Save and update menu
        self.save_config()
        self.update_recent_files_menu()
        logger.info(f"Added to recent files: {file_path}")

    def update_recent_files_menu(self):
        """Update the recent files menu"""
        if self.recent_files_menu is None:
            return

        # Clear existing actions
        self.recent_files_menu.clear()

        if not self.recent_files:
            # Show "No recent files" if empty
            no_files_action = self.recent_files_menu.addAction("Geen recente projecten")
            no_files_action.setEnabled(False)
        else:
            # Add action for each recent file
            for file_path in self.recent_files:
                # Show just the filename, not the full path
                filename = Path(file_path).name
                action = self.recent_files_menu.addAction(filename)
                action.setToolTip(file_path)  # Show full path in tooltip
                # Use lambda with default argument to capture file_path
                action.triggered.connect(lambda checked=False, fp=file_path: self.open_recent_file(fp))

    def clear_recent_files(self):
        """Clear recent files list"""
        self.recent_files = []
        self.save_config()
        self.update_recent_files_menu()
        self.statusBar().showMessage("Recente projecten gewist")
        logger.info("Recent files cleared")

    def open_recent_file(self, file_path: str):
        """Open a file from recent files list"""
        if not Path(file_path).exists():
            QMessageBox.warning(
                self,
                "Bestand niet gevonden",
                f"Het bestand bestaat niet meer:\n{file_path}"
            )
            # Remove from recent files
            self.recent_files.remove(file_path)
            self.save_config()
            self.update_recent_files_menu()
            return

        # Load the file based on extension
        if file_path.lower().endswith('.jspr'):
            project_data = ProjectManager.load_project(file_path)
            if project_data:
                self.apply_loaded_project(project_data)
                self.current_file_path = file_path
                self.statusBar().showMessage(f"Project geladen: {Path(file_path).name}")
        elif file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            self.load_image(file_path)

    def on_color_hover_enter(self, color_index: int):
        """Handle mouse hover over a color in the legend"""
        if self.visualizer.color_map is None:
            return

        # Set preview color in color manager
        self.color_manager.set_preview_color(color_index)

        # Re-render with preview
        self.render()

    def on_color_hover_leave(self):
        """Handle mouse leaving a color in the legend"""
        if self.visualizer.color_map is None:
            return

        # Clear preview
        self.color_manager.clear_preview()

        # Re-render without preview
        self.render()

    def toggle_magnifier(self):
        """Toggle magnifier on/off"""
        self.canvas.show_magnifier = not self.canvas.show_magnifier
        self.magnifier_toggle_btn.setChecked(self.canvas.show_magnifier)
        status = "aan" if self.canvas.show_magnifier else "uit"
        self.statusBar().showMessage(f"Vergrootglas: {status}")
        logger.info(f"Magnifier toggled: {self.canvas.show_magnifier}")
        self.canvas.update()

    def toggle_grid_overlay(self):
        """Toggle grid overlay on/off"""
        self.canvas.show_grid = not self.canvas.show_grid
        self.grid_toggle_action.setChecked(self.canvas.show_grid)
        status = "aan" if self.canvas.show_grid else "uit"
        self.statusBar().showMessage(f"Grid overlay: {status}")
        logger.info(f"Grid overlay toggled: {self.canvas.show_grid}")
        self.canvas.update()

    def open_documentation(self):
        """Open online documentation"""
        import webbrowser
        webbrowser.open("https://github.com/Jasperdeveer/Jasperdeveer")
        self.statusBar().showMessage("Documentatie geopend in browser")

    def show_tips(self):
        """Show tips and tricks dialog"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("💡 Tips & Tricks")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout(dialog)

        # Title
        title = QLabel("<h2>💡 Handige Tips & Tricks</h2>")
        layout.addWidget(title)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Tips list
        tips = [
            ("🎨 Kleurdetectie", [
                "• Gebruik <b>Automatic mode</b> voor snelle kleurdetectie",
                "• Gebruik <b>Manual mode</b> voor volledige controle over je kleuren",
                "• Zwart/wit vlakken krijgen altijd cijfers, andere kleuren alleen bij grote vlakken"
            ]),
            ("🔍 Vergrootglas", [
                "• Druk <b>M</b> om het vergrootglas aan/uit te zetten",
                "• Het vergrootglas toont een 5x5 pixel grid voor detail work",
                "• Werkt in alle modes en tools"
            ]),
            ("📐 Grid Overlay", [
                "• Druk <b>Ctrl+G</b> voor een hulp-grid over je afbeelding",
                "• Perfect voor het meten van afstanden en proporties",
                "• Grid past zich aan bij zoomen"
            ]),
            ("🤖 Smart Merge", [
                "• <b>Ctrl+M</b> voor intelligente samenvoeg-suggesties",
                "• Systeem detecteert vergelijkbare kleuren automatisch",
                "• Ook handig voor gefragmenteerde kleuren met veel kleine vlakken"
            ]),
            ("⚡ Performance", [
                "• Auto-save werkt elke 2 minuten op de achtergrond",
                "• Grote afbeeldingen? Verlaag eerst het aantal kleuren",
                "• Live voorvertoning kan uitgezet worden voor snellere parameter tuning"
            ]),
            ("🖱 Sneltoetsen", [
                "• Druk <b>F1</b> voor een compleet overzicht van alle sneltoetsen",
                "• <b>F11</b> voor presentatiemodus",
                "• <b>Ctrl+Z/Y</b> voor undo/redo"
            ]),
            ("💾 Export", [
                "• <b>Ctrl+L</b> exporteert met legenda erbij",
                "• <b>Ctrl+Shift+E</b> voor batch export (alle modes tegelijk)",
                "• PDF export heeft opties voor grid en page size"
            ])
        ]

        for category, tip_list in tips:
            # Category header
            cat_label = QLabel(f"<h3>{category}</h3>")
            cat_label.setStyleSheet("margin-top: 15px;")
            scroll_layout.addWidget(cat_label)

            # Tips
            for tip in tip_list:
                tip_label = QLabel(tip)
                tip_label.setWordWrap(True)
                tip_label.setStyleSheet("margin-left: 20px; padding: 2px;")
                scroll_layout.addWidget(tip_label)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Close button
        close_btn = QPushButton("Sluiten")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle drop event"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            # Check if it's an image file
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.load_image(file_path)
            elif file_path.lower().endswith('.jspr'):
                # Load project file
                project_data = ProjectManager.load_project(file_path)
                if project_data:
                    self.apply_loaded_project(project_data)
                    self.current_file_path = file_path
                    self.add_to_recent_files(file_path)
                    self.statusBar().showMessage(f"Project geladen: {file_path}")

    def show_shortcuts(self):
        """Show keyboard shortcuts dialog"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("⌨️ Sneltoetsen")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout(dialog)

        # Title
        title = QLabel("<h2>⌨️ Sneltoetsen Overzicht</h2>")
        layout.addWidget(title)

        # Scroll area for shortcuts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Define shortcuts by category
        shortcuts = [
            ("📁 Bestand", [
                ("Ctrl+O", "Open afbeelding"),
                ("Ctrl+S", "Opslaan project"),
                ("Ctrl+Shift+O", "Open project"),
                ("Ctrl+E", "Exporteer PNG"),
                ("Ctrl+L", "Exporteer met legenda"),
                ("Ctrl+Shift+E", "Batch export (alle modi)"),
                ("Ctrl+Q", "Afsluiten"),
            ]),
            ("✏️ Bewerken", [
                ("Ctrl+Z", "Ongedaan maken"),
                ("Ctrl+Y", "Opnieuw"),
                ("Ctrl+M", "Slimme samenvoeg suggesties"),
                ("Ctrl+R", "Herbereken (als live preview uit staat)"),
            ]),
            ("👁 Weergave", [
                ("F11", "Presentatiemodus"),
                ("M", "Toggle vergrootglas"),
                ("Esc", "Sluit presentatiemodus / Annuleer polygon"),
            ]),
            ("🎨 Kleuren", [
                ("Klik op kleur", "Selecteer kleur"),
                ("Shift+Klik", "Samenvoegen naar andere kleur"),
                ("Ctrl+Klik", "Verwijder kleur"),
                ("Alt+Klik", "Wijzig kleurnaam"),
                ("Scroll in legenda", "Scroll door kleuren"),
            ]),
            ("🔧 Tools & Selectie", [
                ("Shift+Klik", "Magic Wand: voeg toe aan selectie"),
                ("Ctrl+Sleep", "Brush: wis selectie"),
                ("Klik punten", "Polygon: plaats punten"),
                ("Enter", "Polygon: voltooi selectie"),
                ("Esc", "Polygon: annuleer"),
            ]),
            ("🖱 Algemeen", [
                ("Scroll", "Zoom in/uit (in canvas)"),
                ("Sleep afbeelding", "Sleep bestand om te openen"),
                ("F1", "Toon dit venster"),
            ]),
        ]

        # Add each category
        for category, items in shortcuts:
            # Category header
            category_label = QLabel(f"<h3>{category}</h3>")
            category_label.setStyleSheet("margin-top: 15px; margin-bottom: 5px;")
            scroll_layout.addWidget(category_label)

            # Add shortcuts in this category
            for shortcut, description in items:
                shortcut_row = QWidget()
                shortcut_layout = QHBoxLayout(shortcut_row)
                shortcut_layout.setContentsMargins(20, 4, 10, 4)

                # Shortcut key(s)
                key_label = QLabel(f"<b>{shortcut}</b>")
                key_label.setMinimumWidth(150)
                key_label.setStyleSheet("""
                    background: rgba(102, 126, 234, 100);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-family: monospace;
                """)
                shortcut_layout.addWidget(key_label)

                # Description
                desc_label = QLabel(description)
                desc_label.setWordWrap(True)
                shortcut_layout.addWidget(desc_label, 1)

                scroll_layout.addWidget(shortcut_row)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Close button
        close_btn = QPushButton("Sluiten")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "Over JSPR Beamer Setup",
            "<h2>JSPR Beamer Setup v1.0</h2>"
            "<p>Voor street art en spuitbus projecten met beamer projectie</p>"
            "<p>High-performance Python + OpenCV + PyQt5 desktop applicatie</p>"
            "<p>© 2026 JSPR</p>"
        )

    # Selection Tools Methods

    def init_selection_tools(self):
        """Initialize selection tools when image is loaded"""
        if self.canvas.image is not None:
            height, width = self.canvas.image.shape[:2]
            self.canvas.selection_tools = SelectionTools((height, width))
            logger.info(f"Selection tools initialized for {width}x{height} image")

    def set_selection_mode(self, mode: SelectionMode):
        """Set the active selection tool mode"""
        if not self.canvas.selection_tools:
            QMessageBox.warning(
                self,
                "Geen afbeelding",
                "Laad eerst een afbeelding voordat je selectie tools gebruikt"
            )
            # Uncheck all buttons
            self.magic_wand_btn.setChecked(False)
            self.brush_btn.setChecked(False)
            self.polygon_btn.setChecked(False)
            return

        # Update button states
        self.magic_wand_btn.setChecked(mode == SelectionMode.MAGIC_WAND)
        self.brush_btn.setChecked(mode == SelectionMode.BRUSH)
        self.polygon_btn.setChecked(mode == SelectionMode.POLYGON)

        # Set mode
        self.canvas.selection_tools.mode = mode
        self.canvas.selection_active = True

        logger.info(f"Selection mode set to: {mode.value}")

    def on_brush_size_changed(self, value: int):
        """Handle brush size change"""
        if self.canvas.selection_tools:
            self.canvas.selection_tools.brush_size = value

    def on_tolerance_changed(self, value: int):
        """Handle tolerance change"""
        if self.canvas.selection_tools:
            self.canvas.selection_tools.tolerance = value

    def update_selection_stats(self):
        """Update selection statistics label"""
        if not self.canvas.selection_tools:
            self.selection_stats_label.setText("Geen selectie")
            self.clear_selection_btn.setEnabled(False)
            self.apply_selection_btn.setEnabled(False)
            return

        count = self.canvas.selection_tools.get_selection_count()
        if count > 0:
            self.selection_stats_label.setText(f"{count:,} pixels geselecteerd")
            self.clear_selection_btn.setEnabled(True)
            self.apply_selection_btn.setEnabled(True)
        else:
            self.selection_stats_label.setText("Geen selectie")
            self.clear_selection_btn.setEnabled(False)
            self.apply_selection_btn.setEnabled(False)

    def clear_selection(self):
        """Clear the current selection"""
        if self.canvas.selection_tools:
            self.canvas.selection_tools.clear_selection()
            self.canvas.selection_tools.cancel_polygon()
            self.update_selection_stats()
            self.canvas.update()
            logger.info("Selection cleared")

    def apply_selection(self):
        """Apply the selection to the color map"""
        if not self.canvas.selection_tools or not self.canvas.selection_tools.is_selection_active():
            QMessageBox.warning(
                self,
                "Geen selectie",
                "Maak eerst een selectie voordat je deze toepast"
            )
            return

        if not self.color_manager.get_colors():
            QMessageBox.warning(
                self,
                "Geen kleuren",
                "Detecteer eerst kleuren voordat je een selectie toepast"
            )
            return

        # Show dialog to select target color
        colors = self.color_manager.get_colors()

        dialog = QDialog(self)
        dialog.setWindowTitle("Selecteer Doelkleur")
        dialog.setModal(True)
        dialog.setMinimumWidth(350)

        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel(
            f"Selecteer de kleur om toe te passen op {self.canvas.selection_tools.get_selection_count():,} pixels:"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Color selection
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        color_group = QButtonGroup()
        for color in colors:
            radio = QRadioButton(f"{color.number}. {color.name}")
            color_group.addButton(radio)
            scroll_layout.addWidget(radio)

            # Select first by default
            if color == colors[0]:
                radio.setChecked(True)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Toepassen")
        cancel_btn = QPushButton("Annuleren")

        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        if dialog.exec_() != QDialog.Accepted:
            return

        # Get selected color
        selected_radio = color_group.checkedButton()
        if not selected_radio:
            return

        selected_index = None
        for i, color in enumerate(colors):
            if color_group.button(i) == selected_radio:
                selected_index = color.number - 1  # Convert to 0-based
                break

        if selected_index is None:
            return

        # Apply selection to color map
        if self.visualizer.color_map is not None:
            self.visualizer.color_map = self.canvas.selection_tools.apply_selection_to_color_map(
                self.visualizer.color_map,
                selected_index
            )

            # Clear cache and re-render
            self.visualizer.clear_cache()
            self.render()

            # Clear selection after applying
            self.canvas.selection_tools.clear_selection()
            self.update_selection_stats()

            self.statusBar().showMessage(f"Selectie toegepast op kleur {colors[selected_index].name}")
            logger.info(f"Selection applied to color index {selected_index}")

    def export_all_variants(self):
        """Export all variants with dialog for selection"""
        if self.canvas.image is None:
            QMessageBox.warning(self, "Geen afbeelding", "Render eerst een afbeelding")
            return

        if not self.color_manager.get_colors():
            QMessageBox.warning(self, "Geen kleuren", "Detecteer eerst kleuren")
            return

        # Create export dialog
        from PyQt5.QtWidgets import QDialog, QCheckBox, QRadioButton, QButtonGroup

        dialog = QDialog(self)
        dialog.setWindowTitle("Export All Varianten")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(600)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("<h2>Export All Varianten</h2>")
        layout.addWidget(title_label)

        # Modi selection
        modi_group = QGroupBox("Modi om te exporteren:")
        modi_layout = QVBoxLayout()
        self.export_pbn_check = QCheckBox("Paint-by-Numbers")
        self.export_pbn_check.setChecked(True)
        modi_layout.addWidget(self.export_pbn_check)

        self.export_line_check = QCheckBox("Lijntekening")
        self.export_line_check.setChecked(True)
        modi_layout.addWidget(self.export_line_check)

        self.export_original_check = QCheckBox("Origineel")
        self.export_original_check.setChecked(True)
        modi_layout.addWidget(self.export_original_check)
        modi_group.setLayout(modi_layout)
        layout.addWidget(modi_group)

        # Variants selection
        variants_group = QGroupBox("Varianten per modus:")
        variants_layout = QVBoxLayout()

        self.export_basis_check = QCheckBox("Basis")
        self.export_basis_check.setChecked(True)
        variants_layout.addWidget(self.export_basis_check)

        self.export_numbers_check = QCheckBox("+ Cijfers")
        self.export_numbers_check.setChecked(True)
        variants_layout.addWidget(self.export_numbers_check)

        self.export_numbers_grid_check = QCheckBox("+ Cijfers + Grid")
        self.export_numbers_grid_check.setChecked(True)
        variants_layout.addWidget(self.export_numbers_grid_check)

        self.export_legend_check = QCheckBox("+ Legenda")
        self.export_legend_check.setChecked(True)
        variants_layout.addWidget(self.export_legend_check)

        self.export_numbers_legend_check = QCheckBox("+ Cijfers + Legenda")
        self.export_numbers_legend_check.setChecked(True)
        variants_layout.addWidget(self.export_numbers_legend_check)

        self.export_complete_check = QCheckBox("+ Complete (alles)")
        self.export_complete_check.setChecked(True)
        variants_layout.addWidget(self.export_complete_check)

        variants_group.setLayout(variants_layout)
        layout.addWidget(variants_group)

        # Settings info
        settings_info = QLabel(f"""
        <b>Huidige instellingen:</b><br>
        • Grid: {self.grid_size_spin.value()}x{self.grid_size_spin.value()},
          {self.grid_color_combo.currentText()}, met labels<br>
        • Cijfers: {self.number_size_spin.value()}pt<br>
        • Lijnen: {self.line_width_spin.value()}px
        """)
        settings_info.setWordWrap(True)
        layout.addWidget(settings_info)

        # Format selection
        format_group = QGroupBox("Formaat:")
        format_layout = QHBoxLayout()
        self.export_format_png = QRadioButton("PNG")
        self.export_format_png.setChecked(True)
        self.export_format_jpg = QRadioButton("JPG")
        format_layout.addWidget(self.export_format_png)
        format_layout.addWidget(self.export_format_jpg)
        format_layout.addStretch()
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Buttons
        button_layout = QHBoxLayout()

        select_all_btn = QPushButton("Alles Aan")
        select_all_btn.clicked.connect(lambda: self.toggle_all_export_checks(True))
        button_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton("Alles Uit")
        select_none_btn.clicked.connect(lambda: self.toggle_all_export_checks(False))
        button_layout.addWidget(select_none_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Annuleren")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        export_btn = QPushButton("Exporteer...")
        export_btn.setDefault(True)
        export_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

        # Show dialog
        if dialog.exec_() != QDialog.Accepted:
            return

        # Get selections
        selected_modi = []
        if self.export_pbn_check.isChecked():
            selected_modi.append('paintByNumbers')
        if self.export_line_check.isChecked():
            selected_modi.append('lineDrawing')
        if self.export_original_check.isChecked():
            selected_modi.append('original')

        selected_variants = []
        if self.export_basis_check.isChecked():
            selected_variants.append('basis')
        if self.export_numbers_check.isChecked():
            selected_variants.append('numbers')
        if self.export_numbers_grid_check.isChecked():
            selected_variants.append('numbers_grid')
        if self.export_legend_check.isChecked():
            selected_variants.append('legend')
        if self.export_numbers_legend_check.isChecked():
            selected_variants.append('numbers_legend')
        if self.export_complete_check.isChecked():
            selected_variants.append('complete')

        if not selected_modi or not selected_variants:
            QMessageBox.warning(self, "Geen selectie", "Selecteer minimaal 1 modus en 1 variant")
            return

        # Ask for export folder
        default_path = os.path.dirname(self.current_file_path) if hasattr(self, 'current_file_path') and self.current_file_path else os.path.expanduser("~")
        export_folder = QFileDialog.getExistingDirectory(
            self,
            "Kies exportmap",
            default_path,
            QFileDialog.ShowDirsOnly
        )

        if not export_folder:
            return

        # Perform export
        self.perform_export_all(export_folder, selected_modi, selected_variants, 'png' if self.export_format_png.isChecked() else 'jpg')

    def toggle_all_export_checks(self, checked: bool):
        """Toggle all export checkboxes"""
        self.export_pbn_check.setChecked(checked)
        self.export_line_check.setChecked(checked)
        self.export_original_check.setChecked(checked)
        self.export_basis_check.setChecked(checked)
        self.export_numbers_check.setChecked(checked)
        self.export_numbers_grid_check.setChecked(checked)
        self.export_legend_check.setChecked(checked)
        self.export_numbers_legend_check.setChecked(checked)
        self.export_complete_check.setChecked(checked)

    def perform_export_all(self, base_folder: str, modi: list, variants: list, format: str):
        """Perform the actual export of all selected variants"""
        # Get base filename
        if hasattr(self, 'current_file_path') and self.current_file_path:
            base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
        else:
            base_name = "export"

        # Create export folder
        export_folder = os.path.join(base_folder, f"{base_name}_project_exports")
        os.makedirs(export_folder, exist_ok=True)

        # Calculate total exports
        total_exports = 0
        for mode in modi:
            if mode == 'original':
                total_exports += 1  # Only basis for original
            else:
                total_exports += len(variants)

        # Progress dialog
        progress = QProgressDialog("Exporteren...", "Annuleren", 0, total_exports, self)
        progress.setWindowTitle("Export All")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        current = 0
        extension = f".{format}"

        try:
            for mode in modi:
                # Set mode
                self.visualizer.set_mode(mode)

                # For original, only export basis
                if mode == 'original':
                    progress.setLabelText(f"Exporteren: origineel...")
                    if progress.wasCanceled():
                        break

                    filename = f"{base_name}_original{extension}"
                    filepath = os.path.join(export_folder, filename)

                    result = self.visualizer.render()
                    if result is not None:
                        self.save_image(result, filepath, format)

                    current += 1
                    progress.setValue(current)
                    continue

                # For PBN and Line modes, export selected variants
                mode_prefix = "pbn" if mode == 'paintByNumbers' else "line"

                for variant in variants:
                    if progress.wasCanceled():
                        break

                    progress.setLabelText(f"Exporteren: {mode_prefix}_{variant}...")

                    # Determine settings for this variant
                    show_numbers = 'numbers' in variant
                    show_grid = 'grid' in variant
                    show_legend = 'legend' in variant

                    # Render with appropriate settings
                    result = self.render_variant(mode, show_numbers, show_grid)

                    if result is not None:
                        # Add legend if requested
                        if show_legend:
                            result = self.add_legend_to_image(result)

                        # Save
                        filename = f"{base_name}_{mode_prefix}_{variant}{extension}"
                        filepath = os.path.join(export_folder, filename)
                        self.save_image(result, filepath, format)

                    current += 1
                    progress.setValue(current)

            progress.close()

            if current == total_exports:
                QMessageBox.information(
                    self,
                    "Export Voltooid",
                    f"✅ {total_exports} bestanden geëxporteerd naar:\n{export_folder}"
                )
                # Open folder
                import subprocess
                subprocess.Popen(['open' if os.name == 'darwin' else 'xdg-open', export_folder])

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Export Fout", f"Fout bij exporteren:\n{str(e)}")
            logger.error(f"Export all failed: {e}", exc_info=True)

    def render_variant(self, mode: str, show_numbers: bool, show_grid: bool) -> Optional[np.ndarray]:
        """Render a specific variant"""
        # Set visualizer mode
        self.visualizer.set_mode(mode)
        self.visualizer.set_show_numbers(show_numbers)

        # Render
        result = self.visualizer.render()

        if result is not None and show_grid:
            # Add grid overlay
            result = self.add_grid_to_image(result)

        return result

    def add_grid_to_image(self, image: np.ndarray) -> np.ndarray:
        """Add presentation-style grid to image"""
        height, width = image.shape[:2]
        result = image.copy()

        # Get grid settings
        grid_size = self.grid_size_spin.value()
        color_index = self.grid_color_combo.currentIndex()

        # Defensive checks
        if grid_size < 1:
            logger.warning(f"Invalid grid_size: {grid_size}, returning original image")
            return result

        if grid_size > 26:
            logger.warning(f"Grid size {grid_size} exceeds alphabet limit (26), clamping to 26")
            grid_size = 26

        # Color map
        color_map = {
            0: (0, 255, 0),      # Gifgroen
            1: (255, 0, 255),    # Magenta
            2: (0, 255, 255),    # Cyaan
            3: (255, 255, 0),    # Geel
            4: (0, 0, 0),        # Zwart
            5: (128, 128, 128)   # Grijs
        }
        r, g, b = color_map.get(color_index, (0, 255, 0))

        # Draw grid lines
        cell_width = width / grid_size
        cell_height = height / grid_size

        # Vertical lines
        for i in range(1, grid_size):
            x = int(i * cell_width)
            cv2.line(result, (x, 0), (x, height), (r, g, b), 3)

        # Horizontal lines
        for i in range(1, grid_size):
            y = int(i * cell_height)
            cv2.line(result, (0, y), (width, y), (r, g, b), 3)

        # Add grid labels (A1, A2, B1, B2, etc.)
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = min(cell_width, cell_height) / 100
        thickness = max(1, int(font_scale * 2))

        for row in range(grid_size):
            for col in range(grid_size):
                label = f"{letters[row]}{col + 1}"
                label_x = int(col * cell_width + 10)
                label_y = int(row * cell_height + 30)

                # Draw with white outline for visibility
                cv2.putText(result, label, (label_x, label_y), font, font_scale, (255, 255, 255), thickness + 2, cv2.LINE_AA)
                cv2.putText(result, label, (label_x, label_y), font, font_scale, (r, g, b), thickness, cv2.LINE_AA)

        return result

    def add_legend_to_image(self, image: np.ndarray) -> np.ndarray:
        """Add legend to right side of image"""
        colors = self.color_manager.get_colors()
        img_height, img_width = image.shape[:2]

        # Create legend
        legend_width = 400
        row_height = 50
        legend_height = max(img_height, len(colors) * row_height + 100)

        legend_image = np.ones((legend_height, legend_width, 3), dtype=np.uint8) * 255

        # Title
        cv2.putText(legend_image, "Kleuren Legenda", (20, 40), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 0, 0), 2)

        # Draw colors
        y_offset = 80
        for color in colors:
            swatch_x, swatch_y = 20, y_offset
            swatch_w, swatch_h = 60, 40

            # Swatch (RGB format)
            cv2.rectangle(legend_image, (swatch_x, swatch_y), (swatch_x + swatch_w, swatch_y + swatch_h),
                         (int(color.r), int(color.g), int(color.b)), -1)
            cv2.rectangle(legend_image, (swatch_x, swatch_y), (swatch_x + swatch_w, swatch_y + swatch_h),
                         (100, 100, 100), 2)

            # Number and name
            cv2.putText(legend_image, f"{color.number}", (swatch_x + swatch_w + 15, swatch_y + 28),
                       cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 0), 2)

            name_text = color.name[:25] + "..." if len(color.name) > 25 else color.name
            cv2.putText(legend_image, name_text, (swatch_x + swatch_w + 60, swatch_y + 28),
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 0), 1)

            y_offset += row_height

        # Resize if needed
        if img_height != legend_height:
            if img_height > legend_height:
                legend_image = cv2.resize(legend_image, (legend_width, img_height))
            else:
                scale = legend_height / img_height
                new_width = int(img_width * scale)
                image = cv2.resize(image, (new_width, legend_height))

        # Combine
        combined = np.hstack([image, legend_image])
        return combined

    def save_image(self, image: np.ndarray, filepath: str, format: str):
        """Save image in specified format"""
        # Convert RGB to BGR for OpenCV
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if format == 'jpg':
            cv2.imwrite(filepath, bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            cv2.imwrite(filepath, bgr)

        logger.info(f"Exported: {filepath}")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for selection tools and magnifier"""
        # Toggle magnifier with M key
        if event.key() == Qt.Key_M:
            self.toggle_magnifier()
            return

        # Handle polygon completion/cancellation
        if self.canvas.selection_active and self.canvas.selection_tools:
            if self.canvas.selection_tools.mode == SelectionMode.POLYGON:
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    # Complete polygon
                    add_to_selection = event.modifiers() & Qt.ShiftModifier
                    self.canvas.selection_tools.complete_polygon_selection(add_to_selection)
                    self.update_selection_stats()
                    self.canvas.update()
                    logger.info("Polygon selection completed")
                    return
                elif event.key() == Qt.Key_Escape:
                    # Cancel polygon
                    self.canvas.selection_tools.cancel_polygon()
                    self.canvas.update()
                    logger.info("Polygon cancelled")
                    return

        super().keyPressEvent(event)
