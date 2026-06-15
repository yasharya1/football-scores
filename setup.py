"""
Build a standalone .app with:
    pip install py2app
    python setup.py py2app
The output is in dist/Football Scores.app
"""
from setuptools import setup

APP     = ["app.py"]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "LSUIElement": True,         # menubar-only app, no Dock icon
        "CFBundleName": "Football Scores",
        "CFBundleDisplayName": "Football Scores",
        "CFBundleIdentifier": "com.footballscores.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "NSHumanReadableCopyright": "MIT",
    },
    "packages": ["rumps"],
}

setup(
    app=APP,
    name="Football Scores",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
