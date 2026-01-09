"""
Setup script for building macOS .app bundle
Usage: python setup.py py2app
"""

import os
from setuptools import setup

APP = ['main.py']
DATA_FILES = [
    ('src', [
        'src/image_processor.py',
        'src/color_manager.py',
        'src/contour_tracer.py',
        'src/visualizer.py',
        'src/main_window.py',
        'src/presentation_mode.py',
        'src/stylesheet.py'
    ])
]
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'cv2',
        'numpy',
        'sklearn',
        'PyQt5',
        'scipy',
        'skimage',
        'joblib',
        'threadpoolctl'
    ],
    'includes': [
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'src.image_processor',
        'src.color_manager',
        'src.contour_tracer',
        'src.visualizer',
        'src.main_window',
        'src.presentation_mode',
        'src.stylesheet'
    ],
    'excludes': [
        'matplotlib',
        'tkinter',
        'IPython',
        'jupyter',
        'notebook',
        'pandas',
        'test',
        'tests'
    ],
    'iconfile': 'icon.icns' if os.path.exists('icon.icns') else None,
    'plist': {
        'CFBundleName': 'JSPR Beamer Setup',
        'CFBundleDisplayName': 'JSPR Beamer Setup',
        'CFBundleIdentifier': 'com.jspr.beamersetup',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14.0',
        'NSRequiresAquaSystemAppearance': False,
        'LSApplicationCategoryType': 'public.app-category.graphics-design',
        'NSHumanReadableCopyright': '© 2026 JSPR',
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Image',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': [
                    'public.image',
                    'public.png',
                    'public.jpeg',
                    'com.compuserve.gif'
                ],
                'LSHandlerRank': 'Alternate'
            }
        ]
    },
    'semi_standalone': False,
    'site_packages': True,
    'strip': False,
    'optimize': 2
}

setup(
    name='JSPR Beamer Setup',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
