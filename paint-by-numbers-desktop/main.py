#!/usr/bin/env python3
"""
JSPR Beamer Setup - Main Entry Point
High-performance desktop app for paint-by-numbers generation
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Add src to path
sys.path.insert(0, 'src')

from main_window import JSPRBeamerSetup


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


def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting JSPR Beamer Setup")

    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("JSPR Beamer Setup")
    app.setOrganizationName("JSPR")

    # Set dark theme
    app.setStyle("Fusion")

    # Create and show main window
    window = JSPRBeamerSetup()
    window.show()

    # Run application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
