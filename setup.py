"""
Build a standalone .app with:
    pip install py2app
    python setup.py py2app
The output is in dist/Topbins.app
"""
from setuptools import setup

APP     = ["app.py"]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon.icns",
    "plist": {
        "LSUIElement": True,
        "CFBundleName": "Topbins",
        "CFBundleDisplayName": "Topbins",
        "CFBundleIdentifier": "com.topbins.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "NSHumanReadableCopyright": "MIT",
    },
    "packages": ["rumps"],
}

setup(
    app=APP,
    name="Topbins",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
