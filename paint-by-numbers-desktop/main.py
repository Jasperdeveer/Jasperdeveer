#!/usr/bin/env python3
"""
JSPR Beamer Setup - Main Entry Point
High-performance desktop app for paint-by-numbers generation
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor

# Add src to path
sys.path.insert(0, 'src')

from main_window import JSPRBeamerSetup
from stylesheet import get_glassmorphism_stylesheet


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('jspr_beamer.log'),
            logging.StreamHandler()
        ]
    )


def setup_dark_theme(app):
    """Setup custom dark theme with glassmorphism"""
    # Set Fusion style as base
    app.setStyle("Fusion")

    # Create dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(15, 15, 15))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(30, 30, 30))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(40, 40, 40))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(102, 126, 234))
    palette.setColor(QPalette.Highlight, QColor(102, 126, 234))
    palette.setColor(QPalette.HighlightedText, Qt.black)

    app.setPalette(palette)

    # Apply glassmorphism stylesheet
    app.setStyleSheet(get_glassmorphism_stylesheet())


def main():
    """Main application entry point - optimized for fast startup"""
    # Minimal logging setup (no file handler for speed)
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger(__name__)

    try:
        # Enable High DPI scaling BEFORE creating QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # Create application (fast)
        app = QApplication(sys.argv)
        app.setApplicationName("JSPR Beamer Setup")
        app.setOrganizationName("JSPR")

        # Minimal theme
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(15, 15, 15))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(40, 40, 40))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.Highlight, QColor(102, 126, 234))
        app.setPalette(palette)

        # Show splash screen immediately for instant feedback
        from PyQt5.QtWidgets import QSplashScreen
        from PyQt5.QtGui import QPixmap, QFont
        from PyQt5.QtCore import Qt as QtCore

        # Create simple splash screen
        splash_pix = QPixmap(400, 200)
        splash_pix.fill(QColor(25, 25, 25))
        splash = QSplashScreen(splash_pix, QtCore.WindowStaysOnTopHint)

        # Add text
        font = QFont("Arial", 16, QFont.Bold)
        splash.setFont(font)
        splash.showMessage("JSPR Beamer Setup wordt geladen...", QtCore.AlignCenter, Qt.white)
        splash.show()
        app.processEvents()  # Force immediate display

        # Create main window (this takes time due to imports)
        window = JSPRBeamerSetup()

        # Close splash and show window
        splash.finish(window)
        window.show()
        window.raise_()
        window.activateWindow()

        # Apply full theme after window is visible (delayed)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: app.setStyleSheet(get_glassmorphism_stylesheet()))
        QTimer.singleShot(150, lambda: window.raise_())
        QTimer.singleShot(150, lambda: window.activateWindow())

        # Run application
        sys.exit(app.exec_())

    except Exception as e:
        logger.error(f"Failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
