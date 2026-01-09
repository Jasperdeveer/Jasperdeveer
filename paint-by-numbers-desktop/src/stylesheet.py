"""
Glassmorphism Stylesheet for JSPR Beamer Setup
Replicates the liquid glass / glassmorphism effect from the web version
"""

# Main glassmorphism dark theme stylesheet
GLASSMORPHISM_STYLE = """
/* Global styles */
* {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

QMainWindow {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #0f0f0f,
        stop:0.5 #1a1a1a,
        stop:1 #0f0f0f
    );
}

/* Panel sections with glassmorphism */
QGroupBox {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255, 255, 255, 25),
        stop:1 rgba(255, 255, 255, 10)
    );
    border: 1px solid rgba(255, 255, 255, 40);
    border-radius: 16px;
    padding: 15px;
    margin-top: 10px;
    color: white;
    font-weight: 600;
    font-size: 13px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 5px 10px;
    color: white;
    font-size: 14px;
    font-weight: 600;
}

/* Buttons with glassmorphism */
QPushButton {
    background: rgba(255, 255, 255, 30);
    border: 1px solid rgba(255, 255, 255, 50);
    border-radius: 8px;
    color: white;
    padding: 10px 15px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background: rgba(255, 255, 255, 40);
    border: 1px solid rgba(255, 255, 255, 100);
}

QPushButton:pressed {
    background: rgba(255, 255, 255, 50);
}

QPushButton:disabled {
    background: rgba(255, 255, 255, 10);
    color: rgba(255, 255, 255, 80);
    border: 1px solid rgba(255, 255, 255, 20);
}

/* Primary buttons */
QPushButton#primaryButton {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(102, 126, 234, 200),
        stop:1 rgba(118, 75, 162, 200)
    );
    border: 1px solid rgba(255, 255, 255, 60);
}

QPushButton#primaryButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(102, 126, 234, 255),
        stop:1 rgba(118, 75, 162, 255)
    );
}

/* Mode buttons */
QPushButton[checkable="true"] {
    background: rgba(255, 255, 255, 20);
    border: 1px solid rgba(255, 255, 255, 40);
}

QPushButton[checkable="true"]:checked {
    background: rgba(255, 255, 255, 60);
    border: 1px solid rgba(255, 255, 255, 100);
}

/* Spin boxes and input fields */
QSpinBox {
    background: rgba(255, 255, 255, 20);
    border: 1px solid rgba(255, 255, 255, 40);
    border-radius: 6px;
    color: white;
    padding: 5px 10px;
    font-size: 13px;
}

QSpinBox:focus {
    border: 1px solid rgba(255, 255, 255, 100);
    background: rgba(255, 255, 255, 30);
}

QSpinBox::up-button, QSpinBox::down-button {
    background: rgba(255, 255, 255, 20);
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: rgba(255, 255, 255, 40);
}

/* Sliders */
QSlider::groove:horizontal {
    background: rgba(255, 255, 255, 30);
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: white;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    border: 2px solid rgba(255, 255, 255, 80);
}

QSlider::handle:horizontal:hover {
    background: rgba(255, 255, 255, 255);
    border: 2px solid rgba(255, 255, 255, 150);
}

/* Scroll areas */
QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: rgba(255, 255, 255, 20);
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 80);
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 120);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Labels */
QLabel {
    color: white;
    font-size: 13px;
}

/* Canvas panel */
#canvasPanel {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255, 255, 255, 25),
        stop:1 rgba(255, 255, 255, 10)
    );
    border: 1px solid rgba(255, 255, 255, 40);
    border-radius: 16px;
}

/* Canvas wrapper */
#canvasWrapper {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(0, 0, 0, 100),
        stop:1 rgba(0, 0, 0, 80)
    );
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 40);
}

/* Color palette items */
#colorItem {
    background: rgba(255, 255, 255, 20);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 8px;
    padding: 10px;
}

#colorItem:hover {
    background: rgba(255, 255, 255, 30);
    border: 1px solid rgba(255, 255, 255, 60);
}

/* Progress bar */
QProgressBar {
    background: rgba(255, 255, 255, 30);
    border: none;
    border-radius: 10px;
    text-align: center;
    color: white;
    font-weight: 600;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(102, 126, 234, 255),
        stop:1 rgba(118, 75, 162, 255)
    );
    border-radius: 10px;
}

/* Menu bar */
QMenuBar {
    background: rgba(255, 255, 255, 20);
    color: white;
    border-bottom: 1px solid rgba(255, 255, 255, 40);
    spacing: 5px;
    padding: 5px;
}

QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background: rgba(255, 255, 255, 40);
}

QMenu {
    background: rgba(20, 20, 20, 250);
    border: 1px solid rgba(255, 255, 255, 40);
    border-radius: 8px;
    color: white;
    padding: 5px;
}

QMenu::item {
    padding: 8px 30px 8px 20px;
    border-radius: 4px;
}

QMenu::item:selected {
    background: rgba(255, 255, 255, 40);
}

/* Status bar */
QStatusBar {
    background: rgba(255, 255, 255, 20);
    color: white;
    border-top: 1px solid rgba(255, 255, 255, 40);
}

/* Splitter */
QSplitter::handle {
    background: rgba(255, 255, 255, 20);
    width: 2px;
}

QSplitter::handle:hover {
    background: rgba(255, 255, 255, 60);
}

/* Message boxes */
QMessageBox {
    background: rgba(20, 20, 20, 250);
    color: white;
}

QMessageBox QLabel {
    color: white;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""

def get_glassmorphism_stylesheet():
    """Get the complete glassmorphism stylesheet"""
    return GLASSMORPHISM_STYLE
