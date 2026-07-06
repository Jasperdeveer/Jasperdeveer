#!/usr/bin/env python3
"""
Paint-by-Numbers Generator - GUI Application
Modern PyQt5 interface with live preview
"""

import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QProgressBar,
    QGroupBox, QGridLayout, QComboBox, QSpinBox, QListWidget,
    QListWidgetItem, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap, QPalette, QColor

from paint_by_numbers import PaintByNumbersGenerator, Color


class ProcessingThread(QThread):
    """Background thread for image processing"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, image_path, n_colors, min_region_size):
        super().__init__()
        self.image_path = image_path
        self.n_colors = n_colors
        self.min_region_size = min_region_size

    def run(self):
        try:
            self.progress.emit("Initializing...")
            generator = PaintByNumbersGenerator(
                self.image_path,
                n_colors=self.n_colors,
                min_region_size=self.min_region_size
            )

            self.progress.emit("Detecting colors...")
            generator.detect_colors()

            self.progress.emit("Quantizing image...")
            generator.quantize_image()

            self.progress.emit("Segmenting regions...")
            generator.segment_regions()

            self.progress.emit("Merging small regions...")
            generator.merge_small_regions()

            self.progress.emit("Finding region centers...")
            generator.find_region_centers()

            self.progress.emit("Complete!")
            self.finished.emit(generator)

        except Exception as e:
            self.error.emit(str(e))


class PaintByNumbersGUI(QMainWindow):
    """Main GUI application"""

    def __init__(self):
        super().__init__()
        self.generator = None
        self.current_image = None
        self.current_mode = 'original'

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('Paint-by-Numbers Generator - Professional Edition')
        self.setGeometry(100, 100, 1400, 900)

        # Apply dark theme
        self.apply_dark_theme()

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - Controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Center panel - Image display
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)

        # Right panel - Legend
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # Set initial splitter sizes
        splitter.setSizes([350, 700, 350])

        self.statusBar().showMessage('Ready - Load an image to start')

    def apply_dark_theme(self):
        """Apply a modern dark theme"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(25, 25, 25))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)

        self.setPalette(palette)

        # Set stylesheet for additional styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #777;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #3a3a3a;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2a82da;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)

    def create_left_panel(self):
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Image section
        image_group = QGroupBox("Image")
        image_layout = QVBoxLayout()

        self.load_btn = QPushButton("📁 Load Image")
        self.load_btn.clicked.connect(self.load_image)
        image_layout.addWidget(self.load_btn)

        image_group.setLayout(image_layout)
        layout.addWidget(image_group)

        # Parameters section
        params_group = QGroupBox("Parameters")
        params_layout = QGridLayout()

        # Number of colors
        params_layout.addWidget(QLabel("Colors:"), 0, 0)
        self.colors_spin = QSpinBox()
        self.colors_spin.setRange(2, 32)
        self.colors_spin.setValue(12)
        self.colors_spin.valueChanged.connect(self.on_params_changed)
        params_layout.addWidget(self.colors_spin, 0, 1)

        # Min region size
        params_layout.addWidget(QLabel("Min Region:"), 1, 0)
        self.region_spin = QSpinBox()
        self.region_spin.setRange(10, 1000)
        self.region_spin.setSingleStep(10)
        self.region_spin.setValue(200)
        self.region_spin.setSuffix(" px")
        self.region_spin.valueChanged.connect(self.on_params_changed)
        params_layout.addWidget(self.region_spin, 1, 1)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Process button
        self.process_btn = QPushButton("🎨 Generate Paint-by-Numbers")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.process_image)
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                padding: 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #666;
            }
        """)
        layout.addWidget(self.process_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        layout.addStretch()
        return panel

    def create_center_panel(self):
        """Create center image display panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # View mode buttons
        mode_layout = QHBoxLayout()

        self.original_btn = QPushButton("Original")
        self.original_btn.clicked.connect(lambda: self.set_view_mode('original'))
        mode_layout.addWidget(self.original_btn)

        self.colored_btn = QPushButton("Paint-by-Numbers")
        self.colored_btn.clicked.connect(lambda: self.set_view_mode('colored'))
        self.colored_btn.setEnabled(False)
        mode_layout.addWidget(self.colored_btn)

        self.line_btn = QPushButton("Line Drawing")
        self.line_btn.clicked.connect(lambda: self.set_view_mode('line'))
        self.line_btn.setEnabled(False)
        mode_layout.addWidget(self.line_btn)

        layout.addLayout(mode_layout)

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #2a2a2a; border: 2px solid #555; border-radius: 8px;")
        self.image_label.setMinimumSize(600, 600)
        self.image_label.setScaledContents(False)
        layout.addWidget(self.image_label)

        # Export buttons
        export_layout = QHBoxLayout()

        self.export_svg_btn = QPushButton("📄 Export SVG")
        self.export_svg_btn.setEnabled(False)
        self.export_svg_btn.clicked.connect(self.export_svg)
        export_layout.addWidget(self.export_svg_btn)

        self.export_png_btn = QPushButton("🖼️ Export PNG")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.clicked.connect(self.export_png)
        export_layout.addWidget(self.export_png_btn)

        layout.addLayout(export_layout)

        return panel

    def create_right_panel(self):
        """Create right legend panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        legend_group = QGroupBox("Color Legend")
        legend_layout = QVBoxLayout()

        self.legend_list = QListWidget()
        legend_layout.addWidget(self.legend_list)

        legend_group.setLayout(legend_layout)
        layout.addWidget(legend_group)

        # Spray calculations
        spray_group = QGroupBox("Spray Paint Calculations")
        spray_layout = QVBoxLayout()

        self.spray_info = QLabel("Montana Black: ~2-2.5 m² per can\n\nLoad an image to calculate.")
        self.spray_info.setWordWrap(True)
        spray_layout.addWidget(self.spray_info)

        spray_group.setLayout(spray_layout)
        layout.addWidget(spray_group)

        return panel

    def load_image(self):
        """Load an image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )

        if file_path:
            try:
                # Load and display original image
                img = cv2.imread(file_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self.current_image = img
                self.image_path = file_path

                self.display_image(img)
                self.process_btn.setEnabled(True)
                self.statusBar().showMessage(f'Loaded: {file_path}')

                # Reset generator
                self.generator = None
                self.colored_btn.setEnabled(False)
                self.line_btn.setEnabled(False)
                self.export_svg_btn.setEnabled(False)
                self.export_png_btn.setEnabled(False)
                self.legend_list.clear()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load image: {e}")

    def display_image(self, img_array):
        """Display numpy array as QPixmap"""
        height, width, channel = img_array.shape
        bytes_per_line = 3 * width

        q_image = QImage(
            img_array.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(q_image)

        # Scale to fit label
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(scaled_pixmap)

    def process_image(self):
        """Process image in background thread"""
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_label.setVisible(True)

        # Create and start processing thread
        self.thread = ProcessingThread(
            self.image_path,
            self.colors_spin.value(),
            self.region_spin.value()
        )
        self.thread.progress.connect(self.on_progress)
        self.thread.finished.connect(self.on_processing_finished)
        self.thread.error.connect(self.on_processing_error)
        self.thread.start()

    def on_progress(self, message):
        """Update progress display"""
        self.progress_label.setText(message)
        self.statusBar().showMessage(message)

    def on_processing_finished(self, generator):
        """Handle processing completion"""
        self.generator = generator

        # Hide progress
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.process_btn.setEnabled(True)

        # Enable view modes
        self.colored_btn.setEnabled(True)
        self.line_btn.setEnabled(True)
        self.export_svg_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)

        # Update legend
        self.update_legend()

        # Show colored view by default
        self.set_view_mode('colored')

        self.statusBar().showMessage('Processing complete!')

    def on_processing_error(self, error_msg):
        """Handle processing error"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.process_btn.setEnabled(True)

        QMessageBox.critical(self, "Processing Error", error_msg)
        self.statusBar().showMessage('Processing failed')

    def set_view_mode(self, mode):
        """Switch between view modes"""
        if mode == 'original':
            self.display_image(self.current_image)
            self.current_mode = 'original'

        elif mode == 'colored' and self.generator:
            # Show colored paint-by-numbers view
            img = np.zeros_like(self.current_image)
            for i, color in enumerate(self.generator.colors):
                mask = self.generator.labels == i
                img[mask] = color.rgb

            self.display_image(img)
            self.current_mode = 'colored'

        elif mode == 'line' and self.generator:
            # Show line drawing
            img = np.ones_like(self.current_image) * 255

            # Draw contours
            from skimage import measure
            regions = measure.regionprops(self.generator.segmented)
            contours_img = np.zeros((self.generator.height, self.generator.width), dtype=np.uint8)

            for region in regions:
                if region.area < self.generator.min_region_size:
                    continue

                mask = (self.generator.segmented == region.label).astype(np.uint8)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(contours_img, contours, -1, 255, 2)

            img[contours_img > 0] = [0, 0, 0]
            self.display_image(img)
            self.current_mode = 'line'

    def update_legend(self):
        """Update color legend"""
        self.legend_list.clear()

        if not self.generator:
            return

        # Calculate areas
        total_cans = 0
        coverage_per_can = 2.25  # m²

        for i, color in enumerate(self.generator.colors):
            mask = self.generator.labels == i
            area_px = np.sum(mask)
            area_m2 = area_px / 10000  # rough estimate
            cans_needed = int(np.ceil(area_m2 / coverage_per_can))
            total_cans += cans_needed

            # Create list item
            item = QListWidgetItem(f"  {color.number}. {color.hex}  |  {cans_needed} cans")

            # Set background color
            item.setBackground(QColor(*color.rgb))

            # Set text color for contrast
            brightness = (color.rgb[0] * 299 + color.rgb[1] * 587 + color.rgb[2] * 114) / 1000
            text_color = Qt.black if brightness > 128 else Qt.white
            item.setForeground(text_color)

            self.legend_list.addItem(item)

        # Update spray calculations
        self.spray_info.setText(
            f"Montana Black: ~2-2.5 m² per can\n\n"
            f"Total cans needed: {total_cans}\n\n"
            f"Based on rough pixel-to-area estimation.\n"
            f"Adjust for actual wall dimensions."
        )

    def export_svg(self):
        """Export SVG file"""
        if not self.generator:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export SVG",
            "",
            "SVG Files (*.svg)"
        )

        if file_path:
            try:
                self.generator.export_svg(file_path, show_numbers=True)
                QMessageBox.information(self, "Success", "SVG exported successfully!")
                self.statusBar().showMessage(f'Exported: {file_path}')
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not export SVG: {e}")

    def export_png(self):
        """Export PNG file"""
        if not self.generator:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PNG",
            "",
            "PNG Files (*.png)"
        )

        if file_path:
            try:
                # Export based on current mode
                mode = 'line' if self.current_mode == 'line' else 'colored'
                self.generator.export_png(file_path, mode=mode)
                QMessageBox.information(self, "Success", f"PNG ({mode} mode) exported successfully!")
                self.statusBar().showMessage(f'Exported: {file_path}')
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not export PNG: {e}")

    def on_params_changed(self):
        """Handle parameter changes"""
        if self.generator:
            # Suggest reprocessing
            self.statusBar().showMessage('Parameters changed - click Generate to reprocess')


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = PaintByNumbersGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
