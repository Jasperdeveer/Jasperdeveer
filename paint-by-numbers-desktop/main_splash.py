#!/usr/bin/env python3
"""
Splash Screen voor JSPR Beamer Setup
Toont een loading screen tijdens het laden van modules
"""

import sys
from PyQt5.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont

def create_splash():
    """Create and show splash screen"""
    # Create splash screen
    splash_pix = QPixmap(600, 400)
    splash_pix.fill(QColor(26, 26, 26))

    painter = QPainter(splash_pix)
    painter.setRenderHint(QPainter.Antialiasing)

    # Title
    painter.setPen(QColor(255, 255, 255))
    title_font = QFont("Arial", 32, QFont.Bold)
    painter.setFont(title_font)
    painter.drawText(splash_pix.rect(), Qt.AlignCenter | Qt.AlignTop, "\n\nJSPR Beamer Setup")

    # Version
    version_font = QFont("Arial", 14)
    painter.setFont(version_font)
    painter.setPen(QColor(180, 180, 180))
    painter.drawText(splash_pix.rect(), Qt.AlignCenter, "\nv1.0\n\n")

    # Loading text
    painter.setPen(QColor(100, 200, 255))
    loading_font = QFont("Arial", 12)
    painter.setFont(loading_font)
    painter.drawText(splash_pix.rect(), Qt.AlignCenter | Qt.AlignBottom, "Modules laden...\n\n\n")

    painter.end()

    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.show()

    return splash

if __name__ == '__main__':
    app = QApplication(sys.argv)
    splash = create_splash()
    app.processEvents()

    # Import main window (heavy operation)
    splash.showMessage("Laden GUI componenten...", Qt.AlignBottom | Qt.AlignHCenter, QColor(100, 200, 255))
    app.processEvents()

    from src.main_window import JSPRBeamerSetup

    splash.showMessage("Initialiseren...", Qt.AlignBottom | Qt.AlignHCenter, QColor(100, 200, 255))
    app.processEvents()

    # Create main window
    window = JSPRBeamerSetup()

    # Show window and close splash
    window.show()
    splash.finish(window)

    sys.exit(app.exec_())
