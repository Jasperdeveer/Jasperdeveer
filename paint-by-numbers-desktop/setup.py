"""
Setup script for building macOS .app bundle
Usage: python setup.py py2app
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'cv2',
        'numpy',
        'sklearn',
        'PyQt5',
        'scipy',
        'skimage'
    ],
    'includes': [
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    'excludes': [
        'matplotlib',
        'tkinter',
        'IPython'
    ],
    'iconfile': None,  # TODO: Add app icon
    'plist': {
        'CFBundleName': 'JSPR Beamer Setup',
        'CFBundleDisplayName': 'JSPR Beamer Setup',
        'CFBundleIdentifier': 'com.jspr.beamersetup',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14.0',
    }
}

setup(
    name='JSPR Beamer Setup',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
