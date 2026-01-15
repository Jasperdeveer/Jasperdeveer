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
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting JSPR Beamer Setup")

    try:
        import time
        start_time = time.time()

        # Enable High DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        logger.info(f"Qt attributes set ({time.time() - start_time:.2f}s)")

        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("JSPR Beamer Setup")
        app.setOrganizationName("JSPR")
        logger.info(f"QApplication created ({time.time() - start_time:.2f}s)")

        # Setup glassmorphism dark theme
        setup_dark_theme(app)
        logger.info(f"Theme applied ({time.time() - start_time:.2f}s)")

        # Create and show main window
        logger.info("Creating main window...")
        window = JSPRBeamerSetup()
        logger.info(f"Main window created ({time.time() - start_time:.2f}s)")

        # Force window to front (especially important on macOS)
        window.show()
        window.raise_()  # Bring window to front
        window.activateWindow()  # Activate window

        # On macOS, sometimes need to force focus after a short delay
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, lambda: window.raise_())
        QTimer.singleShot(50, lambda: window.activateWindow())

        logger.info(f"Window shown ({time.time() - start_time:.2f}s)")

        # Run application
        sys.exit(app.exec_())

    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
