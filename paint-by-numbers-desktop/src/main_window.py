"""
Main Window - PyQt5 GUI for JSPR Beamer Setup
Native desktop interface for paint-by-numbers generation
"""

import sys
import os
from typing import List, Optional
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox, QFileDialog, QScrollArea,
    QGroupBox, QSplitter, QMessageBox, QProgressDialog, QCheckBox, QDialog,
    QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QFont, QCursor
import cv2
import numpy as np
import logging

from image_processor import ImageProcessor
from color_manager import ColorManager, Color
from visualizer import Visualizer
from presentation_mode import PresentationMode
from manual_color_picker import ColorSelectionDialog, ManualColorPicker
from project_manager import ProjectManager

logger = logging.getLogger(__name__)


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image: Optional[np.ndarray] = None
        self.original_image: Optional[np.ndarray] = None  # For eyedropper
        self.zoom_level = 1.0
        self.eyedropper_mode = False
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)  # Track mouse for cursor changes

    def set_image(self, image: np.ndarray):
        """Set image to display (RGB numpy array)"""
        self.image = image
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

    def resizeEvent(self, event):
        """Handle widget resize - refit image"""
        super().resizeEvent(event)
        # Re-fit image when canvas is resized
        if self.image is not None:
            self.fit_to_canvas()

    def paintEvent(self, event):
        """Paint the canvas"""
        painter = QPainter(self)

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

            # Center image in widget
            x = (self.width() - scaled_width) // 2
            y = (self.height() - scaled_height) // 2

            # Draw scaled image using target rectangle
            from PyQt5.QtCore import QRect
            target_rect = QRect(x, y, scaled_width, scaled_height)
            painter.drawImage(target_rect, q_image)
        else:
            # Draw placeholder
            painter.fillRect(self.rect(), QColor(50, 50, 50))
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Sleep een afbeelding hierheen of gebruik Bestand > Open"
            )

    def set_zoom(self, zoom: float):
        """Set zoom level"""
        self.zoom_level = max(0.1, min(5.0, zoom))
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

        # Update display
        self.update()

        # Update parent's zoom label if it exists
        parent = self.parent()
        if parent and hasattr(parent, 'zoom_label'):
            parent.zoom_label.setText(f"{int(self.zoom_level * 100)}%")

    def mousePressEvent(self, event):
        """Handle mouse clicks for eyedropper"""
        if self.eyedropper_mode and self.original_image is not None and event.button() == Qt.LeftButton:
            # Get click position
            click_pos = event.pos()

            # Convert widget coordinates to image coordinates
            if self.image is not None:
                height, width = self.image.shape[:2]
                scaled_width = int(width * self.zoom_level)
                scaled_height = int(height * self.zoom_level)

                # Calculate image position in widget
                x_offset = (self.width() - scaled_width) // 2
                y_offset = (self.height() - scaled_height) // 2

                # Convert to image coordinates
                img_x = int((click_pos.x() - x_offset) / self.zoom_level)
                img_y = int((click_pos.y() - y_offset) / self.zoom_level)

                # Check bounds
                if 0 <= img_x < width and 0 <= img_y < height:
                    # Sample color from original image
                    color = self.original_image[img_y, img_x]
                    r, g, b = int(color[0]), int(color[1]), int(color[2])

                    # Emit signal
                    self.color_picked.emit(r, g, b)
        else:
            super().mousePressEvent(event)


class JSPRBeamerSetup(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Initialize components
        self.image_processor = ImageProcessor()
        self.color_manager = ColorManager()
        self.visualizer = Visualizer()

        # Connect components
        self.visualizer.set_image_processor(self.image_processor)
        self.visualizer.set_color_manager(self.color_manager)

        # State
        self.current_mode = 'original'
        self.current_file_path = None
        self.presentation_window = None
        self.manual_picker = None

        # Setup UI
        self.init_ui()

        logger.info("JSPR Beamer Setup initialized")

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle('JSPR Beamer Setup v1.0')
        self.setGeometry(100, 100, 1600, 900)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)  # Prevent panels from collapsing

        # Left panel: Controls
        left_panel = self.create_control_panel()
        left_panel.setMinimumWidth(280)
        left_panel.setMaximumWidth(450)
        splitter.addWidget(left_panel)

        # Center panel: Canvas
        center_panel = self.create_canvas_panel()
        center_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(center_panel)

        # Right panel: Legend
        right_panel = self.create_legend_panel()
        right_panel.setMinimumWidth(250)
        right_panel.setMaximumWidth(400)
        splitter.addWidget(right_panel)

        # Set splitter sizes (proportions)
        # Use proportional sizing: left 20%, center 60%, right 20%
        total_width = self.width()
        splitter.setSizes([int(total_width * 0.20), int(total_width * 0.60), int(total_width * 0.20)])

        main_layout.addWidget(splitter)

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.statusBar().showMessage('Klaar')

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()

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

        export_png_action = file_menu.addAction('Exporteer PNG...')
        export_png_action.setShortcut('Ctrl+E')
        export_png_action.triggered.connect(self.export_png)

        batch_export_action = file_menu.addAction('Batch Export (Alle Modi)...')
        batch_export_action.setShortcut('Ctrl+Shift+E')
        batch_export_action.triggered.connect(self.batch_export)

        export_svg_action = file_menu.addAction('Exporteer SVG...')
        export_svg_action.triggered.connect(self.export_svg)

        file_menu.addSeparator()

        quit_action = file_menu.addAction('Afsluiten')
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(self.close)

        # View menu
        view_menu = menubar.addMenu('Weergave')

        presentation_action = view_menu.addAction('Presentatie Mode')
        presentation_action.setShortcut('F11')
        presentation_action.triggered.connect(self.enter_presentation_mode)

        # Help menu
        help_menu = menubar.addMenu('Help')

        about_action = help_menu.addAction('Over JSPR Beamer Setup')
        about_action.triggered.connect(self.show_about)

    def create_control_panel(self) -> QWidget:
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Image section
        image_group = QGroupBox("Afbeelding")
        image_layout = QVBoxLayout()
        image_layout.setSpacing(5)
        image_layout.setContentsMargins(5, 5, 5, 5)

        self.open_btn = QPushButton("Open Afbeelding...")
        self.open_btn.clicked.connect(self.open_image)
        image_layout.addWidget(self.open_btn)

        # Image preview - smaller for compact UI
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(280, 180)
        self.image_preview.setStyleSheet("border: 1px solid #ccc; background: #2a2a2a;")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setText("Geen afbeelding")
        image_layout.addWidget(self.image_preview)

        image_group.setLayout(image_layout)
        layout.addWidget(image_group)

        # Mode selection
        mode_group = QGroupBox("Visualisatie")
        mode_layout = QVBoxLayout()
        mode_layout.setSpacing(3)
        mode_layout.setContentsMargins(5, 5, 5, 5)

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

        # Parameters
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout()
        params_layout.setSpacing(3)  # Compacter
        params_layout.setContentsMargins(5, 5, 5, 5)

        # Color count
        color_count_layout = QHBoxLayout()
        color_count_layout.addWidget(QLabel("Kleuren:"))
        self.color_count_spin = QSpinBox()
        self.color_count_spin.setRange(2, 32)
        self.color_count_spin.setValue(8)
        self.color_count_spin.setMaximumWidth(60)
        color_count_layout.addWidget(self.color_count_spin)
        params_layout.addLayout(color_count_layout)

        # Detect colors button
        self.detect_colors_btn = QPushButton("Detecteer Kleuren")
        self.detect_colors_btn.clicked.connect(self.show_color_selection_dialog)
        params_layout.addWidget(self.detect_colors_btn)

        # Black/White selection button
        self.black_white_btn = QPushButton("⚫⚪ Zwart/Wit")
        self.black_white_btn.clicked.connect(self.open_black_white_dialog)
        params_layout.addWidget(self.black_white_btn)

        # Real-time updates checkbox
        self.realtime_checkbox = QCheckBox("Real-time updates")
        self.realtime_checkbox.setChecked(False)
        params_layout.addWidget(self.realtime_checkbox)

        # Show outlines checkbox
        self.show_outlines_checkbox = QCheckBox("Toon outlines")
        self.show_outlines_checkbox.setChecked(True)  # Default: outlines visible
        self.show_outlines_checkbox.stateChanged.connect(self.on_parameter_changed)
        params_layout.addWidget(self.show_outlines_checkbox)

        # Herbereken button
        self.recalc_btn = QPushButton("↻ Herbereken")
        self.recalc_btn.clicked.connect(self.update_parameters)
        params_layout.addWidget(self.recalc_btn)

        # Line width (with decimals)
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
        params_layout.addLayout(line_width_layout)

        # Number size
        number_size_layout = QHBoxLayout()
        number_size_layout.addWidget(QLabel("Cijfergrootte:"))
        self.number_size_spin = QSpinBox()
        self.number_size_spin.setRange(6, 32)
        self.number_size_spin.setValue(16)
        self.number_size_spin.setMaximumWidth(60)
        self.number_size_spin.valueChanged.connect(self.on_parameter_changed)
        number_size_layout.addWidget(self.number_size_spin)
        params_layout.addLayout(number_size_layout)

        # Min region size
        region_size_layout = QHBoxLayout()
        region_size_layout.addWidget(QLabel("Min. vlak:"))
        self.region_size_spin = QSpinBox()
        self.region_size_spin.setRange(10, 500)
        self.region_size_spin.setValue(20)
        self.region_size_spin.setMaximumWidth(60)
        self.region_size_spin.valueChanged.connect(self.on_parameter_changed)
        region_size_layout.addWidget(self.region_size_spin)
        params_layout.addLayout(region_size_layout)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Color palette (scrollable)
        palette_group = QGroupBox("Kleuren")
        palette_layout = QVBoxLayout()
        palette_layout.setSpacing(3)
        palette_layout.setContentsMargins(5, 5, 5, 5)

        self.color_palette_widget = QWidget()
        self.color_palette_layout = QVBoxLayout(self.color_palette_widget)
        self.color_palette_layout.setSpacing(2)  # Compact color items

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.color_palette_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(250)  # Smaller for compact UI

        palette_layout.addWidget(scroll_area)
        palette_group.setLayout(palette_layout)
        layout.addWidget(palette_group)

        # Stretch to push everything to top
        layout.addStretch()

        return panel

    def create_canvas_panel(self) -> QWidget:
        """Create center canvas panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

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

        presentation_btn = QPushButton("🖥️ Presentatie Mode")
        presentation_btn.clicked.connect(self.enter_presentation_mode)
        controls_layout.addWidget(presentation_btn)

        controls_layout.addStretch()

        self.zoom_label = QLabel("100%")
        controls_layout.addWidget(self.zoom_label)

        layout.addLayout(controls_layout)

        # Canvas
        self.canvas = CanvasWidget()
        self.canvas.color_picked.connect(self.on_color_picked)
        layout.addWidget(self.canvas)

        return panel

    def create_legend_panel(self) -> QWidget:
        """Create right legend panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("<h2>Legenda</h2>"))

        # Sorting buttons
        sort_layout = QHBoxLayout()
        sort_label = QLabel("Sorteer:")
        sort_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        sort_layout.addWidget(sort_label)

        sort_brightness_btn = QPushButton("🔆 Helderheid")
        sort_brightness_btn.setMaximumHeight(25)
        sort_brightness_btn.clicked.connect(lambda: self.sort_colors('brightness'))
        sort_layout.addWidget(sort_brightness_btn)

        sort_hue_btn = QPushButton("🌈 Tint")
        sort_hue_btn.setMaximumHeight(25)
        sort_hue_btn.clicked.connect(lambda: self.sort_colors('hue'))
        sort_layout.addWidget(sort_hue_btn)

        sort_usage_btn = QPushButton("📊 Gebruik")
        sort_usage_btn.setMaximumHeight(25)
        sort_usage_btn.clicked.connect(lambda: self.sort_colors('usage'))
        sort_layout.addWidget(sort_usage_btn)

        layout.addLayout(sort_layout)

        # Project statistics
        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("""
            background-color: #f0f0f0;
            padding: 8px;
            border-radius: 4px;
            font-size: 11px;
        """)
        layout.addWidget(self.stats_label)

        # Legend scroll area
        self.legend_widget = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.legend_widget)
        scroll_area.setWidgetResizable(True)

        layout.addWidget(scroll_area)

        return panel

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

        success = self.image_processor.load_image(file_path)

        if success:
            self.current_file_path = file_path

            # Update preview
            img = self.image_processor.get_image_copy()
            self.update_preview(img)

            # Set original image for eyedropper
            self.canvas.set_original_image(img)

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

        progress_callback(80, "Interface updaten...")
        self.update_color_palette()

        progress_callback(100, "Klaar!")
        progress.close()

        # Render
        self.render()

    def update_color_palette(self):
        """Update color palette display (both left palette and right legend)"""
        # Update left palette (compact view)
        while self.color_palette_layout.count():
            child = self.color_palette_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Update right legend (editable view)
        while self.legend_layout.count():
            child = self.legend_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add color items
        colors = self.color_manager.get_colors()

        for color in colors:
            # Left palette - compact view
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(2, 2, 2, 2)
            item_layout.setSpacing(5)

            # Number label
            num_label = QLabel(f"<b>{color.number}</b>")
            num_label.setFixedWidth(25)
            item_layout.addWidget(num_label)

            # Color swatch - smaller
            swatch = QLabel()
            swatch.setFixedSize(30, 30)
            swatch.setStyleSheet(f"background-color: {color.to_hex()}; border: 1px solid #ccc;")
            item_layout.addWidget(swatch)

            # Color name
            name_label = QLabel(color.name)
            name_label.setStyleSheet("font-size: 11px;")  # Smaller font
            item_layout.addWidget(name_label)

            item_layout.addStretch()

            self.color_palette_layout.addWidget(item_widget)

            # Right legend - editable view
            self.add_legend_item(color)

        self.color_palette_layout.addStretch()
        self.legend_layout.addStretch()

    def add_legend_item(self, color: Color):
        """Add an editable color item to the legend"""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 3, 5, 3)
        item_layout.setSpacing(8)

        # Number label
        num_label = QLabel(f"<b>{color.number}</b>")
        num_label.setFixedWidth(30)
        num_label.setStyleSheet("font-size: 13px;")
        item_layout.addWidget(num_label)

        # Color swatch
        swatch = QLabel()
        swatch.setFixedSize(40, 30)
        swatch.setStyleSheet(f"background-color: {color.to_hex()}; border: 2px solid #999; border-radius: 3px;")
        item_layout.addWidget(swatch)

        # Editable color name
        name_edit = QLineEdit(color.name)
        name_edit.setStyleSheet("font-size: 12px; padding: 4px;")
        name_edit.editingFinished.connect(lambda: self.on_color_name_changed(color, name_edit.text()))
        item_layout.addWidget(name_edit, stretch=1)

        # Delete button
        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(30, 30)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
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

    def update_parameters(self):
        """Update visualization parameters"""
        self.visualizer.set_parameters(
            line_width=self.line_width_spin.value(),
            number_size=self.number_size_spin.value(),
            min_region_size=self.region_size_spin.value(),
            show_outlines=self.show_outlines_checkbox.isChecked()
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
            show_outlines=not current_state
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
                'show_outlines': self.show_outlines_checkbox.isChecked()
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

            # Restore mode
            self.set_mode(project_data['current_mode'])

            # Render
            self.render()

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

    def export_svg(self):
        """Export as SVG"""
        QMessageBox.information(
            self,
            "SVG Export",
            "SVG export komt binnenkort beschikbaar!"
        )

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
