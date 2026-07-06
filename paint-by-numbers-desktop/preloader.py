#!/usr/bin/env python3
"""
JSPR Pre-Loader - Shows loading indicator before heavy imports
Uses tkinter (built-in, no dependencies) for instant startup
"""

import sys
import os
import time
import tkinter as tk
from tkinter import ttk
import threading

class PreLoader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JSPR Beamer Setup")

        # Center window
        window_width = 400
        window_height = 150
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Remove window decorations
        self.root.overrideredirect(True)
        self.root.configure(bg='#1a1a1a')

        # Title
        title_label = tk.Label(
            self.root,
            text="JSPR Beamer Setup",
            font=("Arial", 20, "bold"),
            bg='#1a1a1a',
            fg='#64C8FA'
        )
        title_label.pack(pady=20)

        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Laden...",
            font=("Arial", 12),
            bg='#1a1a1a',
            fg='white'
        )
        self.status_label.pack(pady=10)

        # Progress bar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("blue.Horizontal.TProgressbar",
                       troughcolor='#333333',
                       background='#64C8FA',
                       bordercolor='#1a1a1a',
                       lightcolor='#64C8FA',
                       darkcolor='#64C8FA')

        self.progress = ttk.Progressbar(
            self.root,
            style="blue.Horizontal.TProgressbar",
            length=350,
            mode='indeterminate'
        )
        self.progress.pack(pady=10)
        self.progress.start(10)

        # Keep on top
        self.root.attributes('-topmost', True)

    def update_status(self, text):
        """Update status text"""
        self.status_label.config(text=text)
        self.root.update()

    def close(self):
        """Close the pre-loader"""
        self.root.quit()
        self.root.destroy()

def load_app(preloader):
    """Load the actual application"""
    try:
        preloader.update_status("PyQt5 laden...")
        time.sleep(0.1)

        # Now import the heavy stuff
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt

        preloader.update_status("Modules laden...")
        time.sleep(0.1)

        # Add src to path
        sys.path.insert(0, 'src')
        from main_window import JSPRBeamerSetup

        preloader.update_status("Interface voorbereiden...")
        time.sleep(0.1)

        # Create Qt application
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        app = QApplication(sys.argv)
        app.setApplicationName("JSPR Beamer Setup")

        preloader.update_status("Venster maken...")
        time.sleep(0.1)

        # Create main window
        window = JSPRBeamerSetup()

        # Close pre-loader
        preloader.close()

        # Show main window
        window.show()
        window.raise_()
        window.activateWindow()

        # Run
        sys.exit(app.exec_())

    except Exception as e:
        preloader.close()
        import tkinter.messagebox as mb
        mb.showerror("Error", f"Failed to start JSPR:\n{str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    # Create and show pre-loader
    preloader = PreLoader()

    # Load app in background
    threading.Thread(target=load_app, args=(preloader,), daemon=True).start()

    # Run pre-loader (blocks until closed)
    preloader.root.mainloop()
