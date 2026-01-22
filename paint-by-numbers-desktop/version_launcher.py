#!/usr/bin/env python3
"""
Version Launcher - GUI popup to choose between Stable and Development version
"""
import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon


class VersionSelectorDialog(QDialog):
    """Modern dialog to select which version to launch"""

    def __init__(self):
        super().__init__()
        self.selected_version = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("JSPR Beamer Setup - Versie Selecteren")
        self.setFixedSize(500, 280)
        self.setModal(True)

        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("Welke versie wil je starten?")
        title.setFont(QFont("Sans", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Kies tussen de stabiele versie of de ontwikkelversie met nieuwe features")
        subtitle.setFont(QFont("Sans", 9))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Stable button
        stable_btn = QPushButton("✓ Stable Versie")
        stable_btn.setFont(QFont("Sans", 12, QFont.Bold))
        stable_btn.setMinimumHeight(60)
        stable_btn.setCursor(Qt.PointingHandCursor)
        stable_btn.clicked.connect(lambda: self.launch_version("stable"))
        stable_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        layout.addWidget(stable_btn)

        # Stable description
        stable_desc = QLabel("Aanbevolen • Geteste en betrouwbare versie")
        stable_desc.setFont(QFont("Sans", 8))
        stable_desc.setAlignment(Qt.AlignCenter)
        stable_desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); margin-top: -10px;")
        layout.addWidget(stable_desc)

        layout.addSpacing(5)

        # Development button
        dev_btn = QPushButton("⚡ Development Versie")
        dev_btn.setFont(QFont("Sans", 12, QFont.Bold))
        dev_btn.setMinimumHeight(60)
        dev_btn.setCursor(Qt.PointingHandCursor)
        dev_btn.clicked.connect(lambda: self.launch_version("dev"))
        dev_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:pressed {
                background-color: #ba4a00;
            }
        """)
        layout.addWidget(dev_btn)

        # Dev description
        dev_desc = QLabel("Experimenteel • Nieuwe features in ontwikkeling")
        dev_desc.setFont(QFont("Sans", 8))
        dev_desc.setAlignment(Qt.AlignCenter)
        dev_desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); margin-top: -10px;")
        layout.addWidget(dev_desc)

        layout.addStretch()

        self.setLayout(layout)

        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: white;
            }
        """)

    def launch_version(self, version):
        """Launch the selected version"""
        self.selected_version = version
        self.accept()


def main():
    """Main entry point"""
    # Get the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    # Show version selector
    dialog = VersionSelectorDialog()
    result = dialog.exec_()

    if result == QDialog.Accepted and dialog.selected_version:
        # Switch to selected branch
        if dialog.selected_version == "stable":
            print("🚀 Starting Stable version...")
            branch = "stable"
        else:
            print("⚡ Starting Development version...")
            print("⚠️  Warning: This is the development version with untested features!")
            branch = "dev"

        # Close the dialog first
        app.quit()
        del dialog
        del app

        # Switch git branch (silent, ignore errors)
        try:
            subprocess.run(["git", "checkout", branch],
                         capture_output=True,
                         cwd=project_dir,
                         timeout=5)
        except Exception:
            pass  # Continue even if git checkout fails

        # Launch main.py directly
        try:
            print(f"📌 Branch: {branch}")
            print("🚀 Launching application...")
            print("")

            # Execute main.py in the same process
            sys.argv = ["main.py"]  # Reset argv

            # Import and run main.py
            import importlib.util
            spec = importlib.util.spec_from_file_location("main", os.path.join(project_dir, "main.py"))
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)

        except Exception as e:
            print(f"Error launching application: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("Launch cancelled")
        sys.exit(0)


if __name__ == "__main__":
    main()
