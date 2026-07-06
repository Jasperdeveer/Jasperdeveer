"""
Worker Thread System for Background Processing
Handles heavy operations without blocking the UI
"""

from PyQt5.QtCore import QThread, pyqtSignal
import logging

logger = logging.getLogger(__name__)


class WorkerThread(QThread):
    """Generic worker thread for background operations"""

    # Signals
    finished = pyqtSignal(object)  # Emits result when done
    error = pyqtSignal(str)  # Emits error message
    progress = pyqtSignal(int)  # Emits progress percentage (0-100)

    def __init__(self, func, *args, **kwargs):
        """
        Initialize worker thread

        Args:
            func: Function to execute in background
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        """
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = None

    def run(self):
        """Execute the function in background thread"""
        try:
            logger.info(f"Worker thread starting: {self.func.__name__}")
            self.result = self.func(*self.args, **self.kwargs)
            logger.info(f"Worker thread completed: {self.func.__name__}")
            self.finished.emit(self.result)
        except Exception as e:
            logger.error(f"Worker thread error in {self.func.__name__}: {e}", exc_info=True)
            self.error.emit(str(e))


class ColorDetectionWorker(QThread):
    """Specialized worker for color detection"""

    finished = pyqtSignal(list)  # Emits detected colors
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, image_processor, num_colors, mode='automatic'):
        super().__init__()
        self.image_processor = image_processor
        self.num_colors = num_colors
        self.mode = mode

    def run(self):
        """Detect colors in background"""
        try:
            logger.info(f"Detecting {self.num_colors} colors in {self.mode} mode")
            self.progress.emit(10)

            if self.mode == 'automatic':
                colors = self.image_processor.detect_colors(self.num_colors)
            else:
                colors = self.image_processor.detect_colors_kmeans(self.num_colors)

            self.progress.emit(100)
            logger.info(f"Color detection complete: {len(colors)} colors found")
            self.finished.emit(colors)
        except Exception as e:
            logger.error(f"Color detection error: {e}", exc_info=True)
            self.error.emit(str(e))


class RenderWorker(QThread):
    """Specialized worker for rendering operations"""

    finished = pyqtSignal(object)  # Emits rendered image
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # Progress percentage and status message

    def __init__(self, visualizer, mode, parameters=None):
        super().__init__()
        self.visualizer = visualizer
        self.mode = mode
        self.parameters = parameters or {}

    def run(self):
        """Render in background"""
        try:
            logger.info(f"Rendering in {self.mode} mode")

            def progress_callback(percent, message=''):
                self.progress.emit(percent, message)

            result = self.visualizer.render(progress_callback)

            logger.info(f"Rendering complete")
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Rendering error: {e}", exc_info=True)
            self.error.emit(str(e))


class ExportWorker(QThread):
    """Specialized worker for export operations"""

    finished = pyqtSignal(bool, str)  # Success flag and file path
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, export_func, file_path, *args, **kwargs):
        super().__init__()
        self.export_func = export_func
        self.file_path = file_path
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Export in background"""
        try:
            logger.info(f"Exporting to {self.file_path}")
            self.progress.emit(50, "Bezig met exporteren...")

            success = self.export_func(self.file_path, *self.args, **self.kwargs)

            self.progress.emit(100, "Export voltooid")
            logger.info(f"Export complete: {success}")
            self.finished.emit(success, self.file_path)
        except Exception as e:
            logger.error(f"Export error: {e}", exc_info=True)
            self.error.emit(str(e))
